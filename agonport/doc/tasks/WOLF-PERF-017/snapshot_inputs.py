"""Preserve exact selected bytes before any post-release checklist disposition."""
from pathlib import Path
import hashlib, json
T=Path(__file__).resolve().parent
B=T/'build/hardware01'
def main():
    kit=json.loads((B/'kit.json').read_text())
    root=B/'frozen-inputs';root.mkdir(exist_ok=False)
    index={}
    for name,digest in kit['inputs'].items():
        data=Path(name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        p=root/digest
        if not p.exists():p.write_bytes(data)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
        index[name]=dict(sha256=digest,bytes=len(data),snapshot=str(p))
    (root/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps(dict(files=len(index),unique=len(list(root.iterdir()))-1)))
if __name__=='__main__':main()
