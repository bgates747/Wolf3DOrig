"""File-only exact-process handshake. No target transport or process signalling."""
from pathlib import Path
import hashlib
import json
import os
import secrets
import time


class ObserverUnavailable(RuntimeError):
    pass


def identity(pid):
    root = Path('/proc') / str(pid)
    # comm may contain spaces/parentheses; fields after the final ')' start at 3.
    fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] in ('Z', 'X'):
        raise ObserverUnavailable('Process is terminal')
    return dict(pid=int(pid), start=int(fields[19]), ppid=int(fields[1]),
                pgid=int(fields[2]), uid=root.stat().st_uid,
                boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def tracer(pid):
    lines = (Path('/proc') / str(pid) / 'status').read_text().splitlines()
    return int(next(line.split()[1] for line in lines if line.startswith('TracerPid:')))


def write_once(path, value):
    # Publish a complete record atomically, without replacing any earlier record.
    path = Path(path)
    temporary = path.with_name(path.name + '.new-' + secrets.token_hex(8))
    try:
        with temporary.open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def create(folder, lease, kit_sha):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    record = dict(schema='wolf-observer-session-v1', controller=identity(os.getpid()),
                  lease=lease, kit_sha256=kit_sha, nonce=secrets.token_hex(32),
                  epoch=time.time())
    write_once(folder / 'session.json', record)
    return record


def load(path):
    return json.loads(Path(path).read_text())


def check(folder, expected):
    """No successor is admitted on stale ACK, dead actors or missing attachment."""
    try:
        folder = Path(folder)
        if load(folder / 'session.json') != expected:
            raise ObserverUnavailable('Session changed')
        if identity(expected['controller']['pid']) != expected['controller']:
            raise ObserverUnavailable('Controller identity changed')
        ack = load(folder / 'attached.json')
        digest = hashlib.sha256((folder / 'session.json').read_bytes()).hexdigest()
        if ack['session_sha256'] != digest or ack['nonce'] != expected['nonce']:
            raise ObserverUnavailable('Wrong handshake')
        for role in ('observer', 'tracer'):
            if identity(ack[role]['pid']) != ack[role]:
                raise ObserverUnavailable(role + ' identity changed')
        if ack['tracer']['ppid'] != ack['observer']['pid']:
            raise ObserverUnavailable('Tracer has wrong owner')
        if ack['tracer']['pgid'] != ack['tracer']['pid']:
            raise ObserverUnavailable('Tracer group is not isolated')
        if tracer(expected['controller']['pid']) != ack['tracer']['pid']:
            raise ObserverUnavailable('Observer detached')
        return ack
    except (OSError, ValueError, KeyError, StopIteration) as error:
        raise ObserverUnavailable(str(error)) from error


def wait(folder, expected, seconds=45):
    deadline = time.monotonic() + seconds
    while True:
        try:
            return check(folder, expected)
        except ObserverUnavailable:
            if time.monotonic() >= deadline:
                raise
            time.sleep(.025)
