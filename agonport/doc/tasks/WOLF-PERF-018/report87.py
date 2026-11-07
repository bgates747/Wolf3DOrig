"""Offline actual87 join; uses the independently replay-qualified report body."""
from pathlib import Path
import importlib.util,json
T=Path(__file__).resolve().parent
G=T.parent/'WOLF-GOAL-001'
def main():
    spec=importlib.util.spec_from_file_location('wolf_report87',G/'report_h02.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    B=T/'build/hardware01'
    result=module.report(T,B,B/'release87.json',
        [('original','room'),('candidate','room'),('candidate','room'),('original','room')])
    result['comparisons']['candidate']['scope']='Two uncapped runs per arm in one A/B/B/A cohort; pooled controls and their drift bound attribution. Ordinary room only.'
    result['qualification']+=' This selected arrangement is A/B/B/A, not the six-case H02 shared-control design.'
    (B/'RESULT87.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['comparisons'],indent=2))
if __name__=='__main__':main()
