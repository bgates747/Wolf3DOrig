from pathlib import Path
from PIL import Image,ImageDraw
import json,hashlib
T=Path('/Agon/mystuff/Wolf3dOrig/agonport/doc/tasks/WOLF-PERF-007');B=T/'build/visual02';results={};canvas=Image.new('RGB',(1280,520));draw=ImageDraw.Draw(canvas)
binding=json.loads((B/'binding-result.json').read_text())['arms']
for row,a in enumerate(('original','candidate')):
 p=B/'profiles'/a;b=(p/'run/timing.bin').read_bytes();assert len(b)==16233 and b[:8]==b'WPF3\1\3\1\1' and b[29:33]==bytes([34,36,0,2]);count=int.from_bytes(b[8:11],'little');assert count==600
 poses=[]
 for i in range(600):
  raw=b[33+27*i:60+27*i];v=[int.from_bytes(raw[3*j:3*j+3],'little') for j in range(9)]
  assert v[0]==i+1 and v[1]==(720*(i+1)//600)%360 and v[8]==28
  poses.append(v[:2])
 assert (p/'sdcard/wolf3d/stack.bin').stat().st_size==256
 after=(p/'sdcard/wolf3d/after.bin').read_bytes();sp={n:int.from_bytes(after[address-0x40000:address-0x40000+3],'little') for n,address in binding[a]['stack_labels'].items()};assert sp['wp_entry_sp']==sp['wp_exit_sp']
 frames=sorted((p/'run').glob('frame-*.ppm'));distinct=len({hashlib.sha256(f.read_bytes()).hexdigest() for f in frames})
 results[a]=dict(actual_poses=count,distinct_headings=len({x[1] for x in poses}),distinct_captures=distinct,captured_frames=len(frames),bridge=json.loads((p/'run/bridge.json').read_text()),run=json.loads((p/'run/result.json').read_text()),build=json.loads((B/a/'bridge/build-result.json').read_text()),guest_sp=sp)
 for col,n in enumerate((35,40,45,50)):
  image=Image.open(p/f'run/frame-{n:03d}.ppm');canvas.paste(image,(col*320,row*260+20));draw.text((col*320+5,row*260+4),a+' host capture '+str(n)+'s',fill='white')
canvas.save(T/'VISUAL-CAPTURES.png')
(T/'VISUAL-RESULT.json').write_text(json.dumps(dict(passed=True,scope='Native production-source bridge, not Xtensa/runtime/PIC/cache/performance',inputs_manifest_sha256=hashlib.sha256((B/'dispatch-inputs.json').read_bytes()).hexdigest(),retrieval_files=len(json.loads((B/'retrieval-remote.json').read_text())),retrieval_manifest_sha256=hashlib.sha256((B/'retrieval-remote.json').read_bytes()).hexdigest(),arms=results,oryx_release=json.load(open('/tmp/wolf007-oryx-release.json'))),indent=2)+'\n')
print({a:{k:v[k] for k in ('actual_poses','distinct_headings','distinct_captures','captured_frames','guest_sp')} for a,v in results.items()})
