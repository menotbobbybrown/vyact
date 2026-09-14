"""Opt-in startup timing available before application logging is initialized."""
import os
import sys
import time

_ENABLED = os.environ.get('VYACT_STARTUP_TRACE') == '1'
_STARTED_AT = time.perf_counter()
_STAGES = {}


def trace_startup(stage: str, event: str = 'checkpoint') -> None:
    if not _ENABLED:
        return
    now = time.perf_counter()
    duration = ''
    if event == 'begin':
        _STAGES[stage] = now
    elif event == 'end':
        beginning = _STAGES.pop(stage, None)
        if beginning is not None:
            duration = f' duration_ms={(now - beginning) * 1000:.1f}'
    try:
        print(f'[startup-timing] pid={os.getpid()} stage={stage} event={event}'
              f' elapsed_ms={(now - _STARTED_AT) * 1000:.1f}{duration}', file=sys.stderr, flush=True)
    except OSError:
        pass  # Diagnostics must not prevent startup when the desktop pipe closes.
