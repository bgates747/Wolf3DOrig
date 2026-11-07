"""Join original terminal tool results to exact native host process identities.

Offline/proc-only release preparation. Never signal, attach or contact a device.
Tool JSON files must contain the actual original-handle tool returns, not a
substituted process poll; wrapper metadata supplies each original session id.
"""
from pathlib import Path
import argparse
import json
import sys
import time
import host_observer as session

T = Path(__file__).resolve().parent
B = T / 'build/hardware02'


def main(controller_tool, observer_tool):
    assert sys.executable == '/usr/bin/python3'
    record = session.load(B / 'observer/session.json')
    ack = session.load(B / 'observer/attached.json')
    actual = dict(controller=record['controller'], observer=ack['observer'], tracer=ack['tracer'])
    handles = {}
    for role, source in (('controller', controller_tool), ('observer', observer_tool)):
        result = session.load(source)
        assert result['original_session_id'] and result['tool_result']['exit_code'] == 0
        assert not result['tool_result'].get('session_id'), 'Original tool still running'
        handles[role] = dict(original_session_id=result['original_session_id'],
                             original_tool_receipt=str(Path(source).resolve()))
    observations = {}
    for role, original in actual.items():
        try:
            current = session.identity(original['pid'])
        except FileNotFoundError:
            observations[role] = dict(original_pid_absent=True)
        except session.ObserverUnavailable:
            observations[role] = dict(original_process_terminal=True)
        else:
            assert current != original, role + ' is still live; do not release'
            # PID reuse is never attributed to the old process or signalled.
            observations[role] = dict(original_identity_absent=True, current_identity=current)
    session.write_once(B / 'host-actors-terminal.json', dict(**actual, handles=handles,
        epoch=time.time(), controller_returncode=0, observer_returncode=0,
        all_original_handles_terminal=True, exact_processes_terminal=True,
        native_proc_observations=observations, no_target_io=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--controller-tool', type=Path, required=True)
    parser.add_argument('--observer-tool', type=Path, required=True)
    a = parser.parse_args()
    main(a.controller_tool, a.observer_tool)
