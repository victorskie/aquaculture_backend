"""Recompute the rule verdict and delta fields for every stored SensorReading.

One-off backfill for rows written before the rule/forecast split. Old rows hold
the v2 model's safe/unsafe answer in is_safe; this replaces it with the verdict
of telemetry.rules at the moment of the reading.

Note on will_fail_60min: it means the same thing in every row but is not arrived
at the same way. Live ingestion has no future to look at, so it stores the V3
model's *prediction*. This backfill does have the future, so it stores the
*derived outcome* - what actually happened in the following hour. Both land in
the same field, so anything that trains on it is learning from a mixture of
observed history and model output on the live tail.
"""

from collections import Counter
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from telemetry import rules
from telemetry.models import SensorReading
from telemetry.views import MIN_GAP_MINUTES, MAX_GAP_MINUTES

BATCH_SIZE = 500

UPDATED_FIELDS = [
    'temp_delta', 'ph_delta', 'turb_delta', 'after_gap',
    'is_safe', 'failure_type', 'will_fail_60min',
]

MIN_GAP = timedelta(minutes=MIN_GAP_MINUTES)
MAX_GAP = timedelta(minutes=MAX_GAP_MINUTES)
HORIZON = timedelta(minutes=rules.HORIZON_MINUTES)


class Command(BaseCommand):
    help = "Recompute deltas, rule verdicts and derived forecasts for all readings."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        node_names = sorted(
            SensorReading.objects.values_list('node_name', flat=True).distinct()
        )
        if not node_names:
            self.stdout.write("No readings found; nothing to do.")
            return

        totals = Counter()
        changed_rows = []

        for node_name in node_names:
            readings = list(
                SensorReading.objects.filter(node_name=node_name).order_by('timestamp')
            )
            before = [self._snapshot(r) for r in readings]

            self._apply_deltas_and_verdicts(readings)
            self._apply_derived_forecast(readings)

            node_changed = [
                r for r, old in zip(readings, before) if self._snapshot(r) != old
            ]
            changed_rows.extend(node_changed)

            self._report_node(node_name, readings, before, node_changed)
            self._accumulate(totals, readings, before, node_changed)

        self._report_totals(totals, len(changed_rows))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\nDry run: nothing was written."
            ))
            return

        with transaction.atomic():
            SensorReading.objects.bulk_update(
                changed_rows, UPDATED_FIELDS, batch_size=BATCH_SIZE
            )
        self.stdout.write(self.style.SUCCESS(
            f"\nWrote {len(changed_rows)} rows in batches of {BATCH_SIZE}."
        ))

    @staticmethod
    def _snapshot(reading):
        return tuple(getattr(reading, f) for f in UPDATED_FIELDS)

    @staticmethod
    def _apply_deltas_and_verdicts(readings):
        """Pass 1: deltas against the previous reading, then the rule verdict."""
        previous = None
        for reading in readings:
            reading.temp_delta = reading.ph_delta = reading.turb_delta = None
            reading.after_gap = True

            if previous is not None:
                gap = reading.timestamp - previous.timestamp
                if MIN_GAP <= gap <= MAX_GAP:
                    reading.temp_delta = round(reading.temperature - previous.temperature, 2)
                    reading.ph_delta = round(reading.ph_level - previous.ph_level, 2)
                    reading.turb_delta = round(reading.turbidity - previous.turbidity, 2)
                    reading.after_gap = False

            reading.is_safe, reading.failure_type = rules.classify(
                reading.temperature, reading.ph_level, reading.turbidity,
                reading.temp_delta, reading.ph_delta, reading.turb_delta,
            )
            previous = reading

    @staticmethod
    def _apply_derived_forecast(readings):
        """Pass 2: look ahead at the verdicts pass 1 just computed.

        Must run after every verdict in the node is settled - a reading's
        forecast depends on the recomputed is_safe of the rows that follow it.
        """
        if not readings:
            return
        last_timestamp = readings[-1].timestamp

        for i, reading in enumerate(readings):
            if not reading.is_safe or reading.after_gap:
                reading.will_fail_60min = None
                continue

            failed_ahead = False
            for later in readings[i + 1:]:
                if later.timestamp > reading.timestamp + HORIZON:
                    break
                if not later.is_safe:
                    failed_ahead = True
                    break

            if failed_ahead:
                reading.will_fail_60min = True
            elif last_timestamp - reading.timestamp < HORIZON:
                # The record runs out before the horizon closes, so a quiet
                # window here is unobserved rather than clear.
                reading.will_fail_60min = None
            else:
                reading.will_fail_60min = False

    def _report_node(self, node_name, readings, before, node_changed):
        verdicts = Counter(r.is_safe for r in readings)
        failures = Counter(r.failure_type for r in readings if r.failure_type)
        forecasts = Counter(r.will_fail_60min for r in readings)
        gaps = sum(1 for r in readings if r.after_gap)
        flipped = sum(
            1 for r, old in zip(readings, before)
            if old[UPDATED_FIELDS.index('is_safe')] != r.is_safe
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{node_name}"))
        self.stdout.write(f"  readings              {len(readings)}")
        self.stdout.write(f"  rows changed          {len(node_changed)}")
        self.stdout.write(f"  is_safe flipped       {flipped}")
        self.stdout.write(
            f"  verdict               safe {verdicts[True]}  unsafe {verdicts[False]}"
        )
        self.stdout.write(
            "  failure_type          "
            f"parameter {failures['parameter']}  rate {failures['rate']}"
        )
        self.stdout.write(f"  after_gap             {gaps}")
        self.stdout.write(
            "  will_fail_60min       "
            f"True {forecasts[True]}  False {forecasts[False]}  None {forecasts[None]}"
        )

    @staticmethod
    def _accumulate(totals, readings, before, node_changed):
        totals['readings'] += len(readings)
        totals['changed'] += len(node_changed)
        totals['flipped'] += sum(
            1 for r, old in zip(readings, before)
            if old[UPDATED_FIELDS.index('is_safe')] != r.is_safe
        )
        totals['safe'] += sum(1 for r in readings if r.is_safe)
        totals['unsafe'] += sum(1 for r in readings if not r.is_safe)
        totals['parameter'] += sum(1 for r in readings if r.failure_type == 'parameter')
        totals['rate'] += sum(1 for r in readings if r.failure_type == 'rate')
        totals['after_gap'] += sum(1 for r in readings if r.after_gap)
        totals['fc_true'] += sum(1 for r in readings if r.will_fail_60min is True)
        totals['fc_false'] += sum(1 for r in readings if r.will_fail_60min is False)
        totals['fc_none'] += sum(1 for r in readings if r.will_fail_60min is None)

    def _report_totals(self, totals, changed):
        self.stdout.write(self.style.MIGRATE_HEADING("\nAll nodes"))
        self.stdout.write(f"  readings              {totals['readings']}")
        self.stdout.write(f"  rows changed          {changed}")
        self.stdout.write(f"  is_safe flipped       {totals['flipped']}")
        self.stdout.write(
            f"  verdict               safe {totals['safe']}  unsafe {totals['unsafe']}"
        )
        self.stdout.write(
            "  failure_type          "
            f"parameter {totals['parameter']}  rate {totals['rate']}"
        )
        self.stdout.write(f"  after_gap             {totals['after_gap']}")
        self.stdout.write(
            "  will_fail_60min       "
            f"True {totals['fc_true']}  False {totals['fc_false']}  None {totals['fc_none']}"
        )
