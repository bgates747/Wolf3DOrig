"""Default-disposition disposable child for the separate-group attach check."""
from pathlib import Path
import argparse, json, os, time

parser = argparse.ArgumentParser()
parser.add_argument('--ready', required=True, type=Path)
parser.add_argument('--case', choices=('normal', 'direct', 'group', 'observer'), required=True)
args = parser.parse_args()
with args.ready.open('x') as stream:
    json.dump(dict(pid=os.getpid(), ppid=os.getppid(), pgid=os.getpgrp(),
                   uid=os.getuid(), case=args.case, epoch=time.time()), stream)
    stream.flush()
    os.fsync(stream.fileno())
time.sleep(1 if args.case == 'normal' else 15)

