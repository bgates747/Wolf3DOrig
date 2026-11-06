"""Scope adapter: one unchanged paced case, original49file admission preserved."""
from pathlib import Path
import argparse,importlib.util,hashlib,json
HERE=Path(__file__).resolve().parent
DONOR=HERE.parent/'WOLF-PERF-001/hardware/physical.py'
spec=importlib.util.spec_from_file_location('wolf_physical_original',DONOR)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class VisibleBench(m.Bench):
 def __init__(self,context):
  super().__init__(context)
  self.inventory=dict(self.inventory,order=['paced'])
  self.remote='/test/wolf/perf002-visible01'
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('context');p.add_argument('action',choices=('entry','stage','run','retrieve','handback'));a=p.parse_args()
 b=VisibleBench(a.context)
 if a.action in ('run','retrieve'):getattr(b,a.action)('paced')
 else:getattr(b,a.action)()
