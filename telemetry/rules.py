"""Deterministic water-safety rules.

Pure functions and constants only - no Django imports, so this module can be
used by the backend, the trainer and any offline analysis alike.
"""

TEMP_MIN, TEMP_MAX = 25.0, 32.0
PH_MIN, PH_MAX = 6.5, 8.5
TURB_MAX = 25.0

D_TEMP_MAX, D_PH_MAX, D_TURB_MAX = 1.0, 0.5, 5.0

CYCLE_MINUTES = 15
HORIZON_MINUTES = 60


def classify(temperature, ph_level, turbidity,
             temp_delta=None, ph_delta=None, turb_delta=None):
    """Return (is_safe, failure_type).

    failure_type is 'parameter' if any measured value is outside its
    range, else 'rate' if any delta magnitude exceeds its limit, else
    None. Parameter failure takes precedence.

    Deltas that are None are skipped, so a reading whose deltas are
    undefined is still checked against the parameter ranges.
    """
    if not (TEMP_MIN <= temperature <= TEMP_MAX):
        return False, 'parameter'
    if not (PH_MIN <= ph_level <= PH_MAX):
        return False, 'parameter'
    if turbidity > TURB_MAX:
        return False, 'parameter'

    if temp_delta is not None and abs(temp_delta) > D_TEMP_MAX:
        return False, 'rate'
    if ph_delta is not None and abs(ph_delta) > D_PH_MAX:
        return False, 'rate'
    if turb_delta is not None and abs(turb_delta) > D_TURB_MAX:
        return False, 'rate'

    return True, None
