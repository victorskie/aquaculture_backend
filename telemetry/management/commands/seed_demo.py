"""Replay a window of real readings so the dashboard lands in a chosen state.

For producing dashboard screenshots that look like the pond, rather than like
synthetic test data. Each state names a window of aquaculture_dataset_v3.csv
that ends in that state. The window is shifted forward by one constant offset so
it ends at now, and every reading is then put through views.ingest_reading() -
the same function a live upload calls.

That means the verdicts are derived here, not copied: classify() decides safety
and the V3 pickle makes the forecast, from the replayed values. The CSV's own
is_safe / will_fail_60min columns are never read. They are used only to check
the outcome afterwards, and a mismatch is reported rather than papered over.

Spacing is preserved exactly, gaps included, so a reading that followed a missed
cycle in the pond follows one here too and keeps its undefined deltas.

Nothing is deleted unless --reset is passed. --reset is refused outside DEBUG,
and refused again if the database is not local: this project reads DATABASE_URL
and normally points at hosted Postgres, where DEBUG is still True on a developer
machine. DEBUG describes the environment, not which database is wired up, so on
its own it does not stop a reset from deleting a real pond's history.
"""

import os
from urllib.parse import urlparse

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from telemetry.models import SensorReading
from telemetry.views import NODE_NAMES, ingest_reading, ml_model

DATASET = "aquaculture_dataset_v3.csv"

# Readings considered per node before the lead-in is trimmed. The graphs cap at
# views.GRAPH_POINTS, which is this same number, so a full window fills them.
WINDOW = 96

# The last reading of each window. These windows were chosen because they end in
# the state they are named for; the verdicts are still recomputed, not assumed.
ANCHORS = {
    'optimal': "2026-08-05 05:38",   # both nodes steady and well within limits
    'early':   "2026-08-03 00:53",   # Node B within limits, turbidity climbing
    'warning': "2026-08-02 07:08",   # Node B turbidity above the limit
}

# Hours trimmed off the START of each window, so the graphs open on calm water
# instead of part-way through an episode. The end point is untouched, and so is
# the final verdict: trimming the lead-in only changes where the graph opens.
#
# 'early' needs a longer trim than the others. Its Node B episode runs 05:08 to
# 07:08 at turbidity 25.7-29.2, so a 6-hour trim would open the graph at 27.6,
# above the limit and in the middle of the very spike being trimmed. The water
# is back under the limit by 07:23 and flat around 16 from 10 hours in.
LEAD_IN_HOURS = {
    'optimal': 6,
    'early': 10,
    'warning': 6,
}

# Columns the replay is allowed to touch. The verdict and delta columns are
# deliberately absent: reading them would defeat the point of the replay.
REPLAYED = ['timestamp', 'node_name', 'temperature', 'ph_level', 'turbidity']

# Hosts whose data is disposable. Anything else is treated as real.
LOCAL_HOSTS = {'', 'localhost', '127.0.0.1', '::1', 'host.docker.internal'}


def _reset_target_objection(conn):
    """Return why --reset must not run here, or None if the target is disposable.

    Checked in addition to DEBUG, which only says how the code is configured and
    stays True on a developer machine that is pointed at the production database.
    """
    db = conn.settings_dict
    if db['ENGINE'].endswith('sqlite3'):
        return None

    host = (db.get('HOST') or '').strip()
    if not host:
        # dj_database_url may leave HOST empty; fall back to the raw URL.
        host = urlparse(os.environ.get('DATABASE_URL', '')).hostname or ''
    host = host.lower()

    if host in LOCAL_HOSTS:
        return None

    return (
        f"the database is {db['ENGINE'].rsplit('.', 1)[-1]} on host {host!r} "
        f"(NAME {db.get('NAME')!r}), which is not local"
    )


class Command(BaseCommand):
    help = ("Replay a window of real readings from the V3 dataset so the "
            "dashboard ends in the optimal, early-warning or failure state.")

    def add_arguments(self, parser):
        parser.add_argument(
            '--state', choices=sorted(ANCHORS), default='optimal',
            help="Banner state the replayed window should end in. Default: optimal.",
        )
        parser.add_argument(
            '--reset', action='store_true',
            help=("Delete every SensorReading first. Refused unless DEBUG is True "
                  "and the database is local."),
        )
        parser.add_argument(
            '--i-know-this-is-not-local', action='store_true',
            help=("Allow --reset against a non-local database. This deletes real "
                  "logged history and cannot be undone from here."),
        )
        parser.add_argument(
            '--dataset', default=None,
            help=f"Path to the source CSV. Default: {DATASET} beside manage.py.",
        )

    def handle(self, *args, **options):
        state = options['state']

        self._guard_reset(options)

        if ml_model is None:
            self.stdout.write(self.style.WARNING(
                "The V3 model did not load, so will_fail_60min will be None on "
                "every row and the 'early' state cannot appear."
            ))

        window = self._load_window(options['dataset'], state)

        if options['reset']:
            self._reset()

        # One offset for every row of every node, so the two nodes stay aligned
        # with each other and the spacing inside each node is untouched.
        anchor = window['timestamp'].max()
        offset = timezone.now() - anchor
        window = window.assign(timestamp=window['timestamp'] + offset)

        written = self._replay(window)
        self._report(state, anchor, offset, written)

    def _guard_reset(self, options):
        if not options['reset']:
            return

        if not settings.DEBUG:
            raise CommandError(
                "--reset deletes every SensorReading and is only allowed when "
                "DEBUG is True. DEBUG is False here, which usually means this "
                "is a real deployment. Refusing."
            )

        # DEBUG alone is not enough. This project reads DATABASE_URL, so a
        # developer machine with DEBUG=True is usually still pointed at the
        # hosted database holding the only copy of the logged history.
        objection = _reset_target_objection(connection)
        if objection and not options['i_know_this_is_not_local']:
            raise CommandError(
                f"--reset would delete every SensorReading, but {objection}.\n"
                f"DEBUG is True, which only says how this checkout is "
                f"configured, not which database it is pointed at.\n"
                f"Refusing. Point DATABASE_URL at a local database, or pass "
                f"--i-know-this-is-not-local to delete the real history anyway."
            )

    def _reset(self):
        # Say what is being destroyed, and say it before destroying it, so a
        # reset aimed at the wrong database leaves a record of what was lost.
        doomed = SensorReading.objects.all()
        count = doomed.count()
        if count:
            oldest = doomed.order_by('timestamp').values_list('timestamp', flat=True).first()
            newest = doomed.order_by('-timestamp').values_list('timestamp', flat=True).first()
            self.stdout.write(self.style.WARNING(
                f"--reset: deleting {count} existing reading(s), "
                f"{oldest:%Y-%m-%d %H:%M} .. {newest:%Y-%m-%d %H:%M}."
            ))
        SensorReading.objects.all().delete()

    def _load_window(self, dataset, state):
        """Return the last WINDOW rows per node ending at this state's anchor."""
        path = dataset or os.path.join(settings.BASE_DIR, DATASET)
        if not os.path.exists(path):
            raise CommandError(
                f"{path} not found. The replay needs the V3 dataset; pass "
                f"--dataset to point at it."
            )

        df = pd.read_csv(path, parse_dates=['timestamp'], usecols=REPLAYED)
        anchor = pd.Timestamp(ANCHORS[state])

        frames = []
        for node_name in NODE_NAMES:
            rows = df[(df.node_name == node_name) & (df.timestamp <= anchor)]
            rows = rows.sort_values('timestamp').tail(WINDOW)
            if len(rows) < WINDOW:
                raise CommandError(
                    f"{node_name} has only {len(rows)} reading(s) at or before "
                    f"{anchor} in {os.path.basename(path)}; need {WINDOW}."
                )
            frames.append(rows)

        window = pd.concat(frames)

        # Trim the lead-in. Cut from the combined window so both nodes keep the
        # same time range and stay aligned on the graphs.
        lead_in = LEAD_IN_HOURS[state]
        if lead_in:
            cut = window['timestamp'].min() + pd.Timedelta(hours=lead_in)
            window = window[window['timestamp'] >= cut]
            if window.empty:
                raise CommandError(
                    f"Trimming {lead_in}h off the {state!r} window left nothing."
                )

        if window['timestamp'].max() != anchor:
            raise CommandError(
                f"The {state!r} window should end at {anchor}, but the latest "
                f"reading in it is {window['timestamp'].max()}."
            )

        # Naive in the CSV. Interpret in the project's timezone; the shift that
        # follows is a timedelta, so the spacing survives either way.
        tz = timezone.get_current_timezone()
        return window.assign(
            timestamp=window['timestamp'].dt.tz_localize(tz)
        ).sort_values(['timestamp', 'node_name']).reset_index(drop=True)

    def _replay(self, window):
        """Ingest every row in time order, through the live ingest path."""
        written = {node_name: [] for node_name in NODE_NAMES}
        with transaction.atomic():
            for row in window.itertuples(index=False):
                reading = ingest_reading(
                    node_name=row.node_name,
                    temperature=float(row.temperature),
                    ph_level=float(row.ph_level),
                    turbidity=float(row.turbidity),
                    timestamp=row.timestamp.to_pydatetime(),
                )
                written[reading.node_name].append(reading)
        return written

    @staticmethod
    def _verdict(reading):
        if reading.is_safe is False:
            return f"FAIL ({reading.failure_type})"
        if reading.will_fail_60min is True:
            return "safe, failure forecast"
        if reading.will_fail_60min is False:
            return "safe, no failure forecast"
        return "safe, forecast skipped"

    @staticmethod
    def _fmt(value):
        return "  -  " if value is None else f"{value:+.2f}"

    def _report(self, state, anchor, offset, written):
        total = sum(len(rows) for rows in written.values())
        per_node = max((len(rows) for rows in written.values()), default=0)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nReplayed --state {state}: {total} readings, "
            f"{per_node} per node, from {DATASET}"
        ))
        self.stdout.write(
            f"  source window ended {anchor:%Y-%m-%d %H:%M}, "
            f"shifted forward {offset.days}d {offset.seconds // 3600}h to end now"
        )
        self.stdout.write(
            f"  lead-in trimmed: {LEAD_IN_HOURS[state]}h off the start "
            f"(from {WINDOW} readings per node), so the graphs open on calm water"
        )

        for node_name, rows in written.items():
            gaps = sum(1 for r in rows if r.after_gap)
            span = rows[-1].timestamp - rows[0].timestamp
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{node_name}"))
            self.stdout.write(
                f"  {len(rows)} readings spanning {span}, "
                f"{gaps} after a gap (deltas undefined)"
            )
            self.stdout.write(
                "  last five:  time          temp     pH    turb  |"
                "   dtemp   dpH   dturb  |  verdict"
            )
            for r in rows[-5:]:
                self.stdout.write(
                    f"              {r.timestamp:%d %b %H:%M}  "
                    f"{r.temperature:5.2f}  {r.ph_level:4.2f}  {r.turbidity:5.2f}  |  "
                    f"{self._fmt(r.temp_delta)}  {self._fmt(r.ph_delta)}  "
                    f"{self._fmt(r.turb_delta)}  |  {self._verdict(r)}"
                )

        self.stdout.write(self.style.MIGRATE_HEADING("\nFinal reading per node"))
        finals = {n: rows[-1] for n, rows in written.items() if rows}
        for node_name, reading in finals.items():
            self.stdout.write(f"  {node_name:8} {self._verdict(reading)}")

        # Same three-way ladder the dashboard applies to these same rows.
        if any(r.is_safe is False for r in finals.values()):
            banner, style = 'warning', self.style.ERROR
        elif any(r.will_fail_60min for r in finals.values()):
            banner, style = 'early', self.style.WARNING
        else:
            banner, style = 'optimal', self.style.SUCCESS

        self.stdout.write(style(f"\nDashboard banner: {banner}"))
        if banner != state:
            self.stdout.write(self.style.ERROR(
                f"WARNING: you asked for {state!r} but the replayed readings "
                f"produce {banner!r}. The rule thresholds or the model have "
                f"changed since this window was chosen, so the screenshot will "
                f"not show what you expect."
            ))
