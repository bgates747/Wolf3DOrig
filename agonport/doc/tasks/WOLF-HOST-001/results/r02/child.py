"""Disposable native observer target; retain default SIGTERM termination."""
from pathlib import Path
import argparse, json, os, time

parser = argparse.ArgumentParser()
parser.add_argument('--ready', required=True, type=Path)
parser.add_argument('--case', choices=('normal', 'direct', 'group'), required=True)
args = parser.parse_args()
record = dict(pid=os.getpid(), ppid=os.getppid(), pgid=os.getpgrp(),
              uid=os.getuid(), case=args.case, epoch=time.time(),
              default_signal_disposition=True)
with args.ready.open('x') as stream:
    json.dump(record, stream)
    stream.flush()
    os.fsync(stream.fileno())
if args.case != 'normal':
    time.sleep(15)

