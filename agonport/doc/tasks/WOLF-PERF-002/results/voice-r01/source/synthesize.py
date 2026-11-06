#!/usr/bin/env python3
"""Create one fresh audio-notification WAV; never deploy or play hardware."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,tempfile,wave

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--text',required=True);p.add_argument('--output',required=True,type=Path)
 p.add_argument('--jukebox',type=Path,default=Path('/Agon/mystuff/AgonJukebox'))
 a=p.parse_args();out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
 if out.suffix.lower()!='.wav' or not a.text.strip():p.error('Provide nonempty text and a .wav output')
 mp3=out.with_suffix('.mp3');manifest=out.with_suffix('.json')
 for f in (out,mp3,manifest):
  if f.exists():raise FileExistsError(f'Use a fresh output; refusing to overwrite {f}')
 converter=a.jukebox.resolve()/'scripts/make_wav.py';python=a.jukebox.resolve()/'.venv/bin/python'
 if not converter.is_file() or not python.is_file():raise FileNotFoundError('AgonJukebox converter/environment not found')
 from gtts import gTTS
 with tempfile.TemporaryDirectory(prefix='audio-notify-',dir=out.parent)as temp:
  root=Path(temp);source=root/'speech.mp3';wav=root/'speech.wav'
  gTTS(text=a.text,lang='en',tld='co.uk',timeout=(5,20)).save(str(source))
  subprocess.run([str(python),str(converter),str(source),'-o',str(wav),'--sample-rate','16000','--compress'],check=True,env=dict(os.environ,TMPDIR=str(root)))
  spec=importlib.util.spec_from_file_location('jukebox_wav',converter);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate_agon_wav(wav)
  with wave.open(str(wav),'rb')as f:
   frames=f.getnframes();rate=f.getframerate()
   if (f.getnchannels(),f.getsampwidth(),rate,f.getcomptype())!=(1,1,16000,'NONE')or not 0<frames<=rate*15:raise ValueError('Speech must fit the player: u8 mono16000Hz, maximum15seconds')
  for src,dst in ((wav,out),(source,mp3)):
   with src.open('rb')as r,dst.open('xb')as w:shutil.copyfileobj(r,w)
  with manifest.open('x')as f:json.dump(dict(schema='audio-notify-speech-v1',text=a.text,engine='gTTS2.5.4',language='en',tld='co.uk',rate=rate,pcm_bytes=frames,seconds=frames/rate,converter_sha256=hashlib.sha256(converter.read_bytes()).hexdigest(),sha256={q.name:hashlib.sha256(q.read_bytes()).hexdigest()for q in (out,mp3)}),f,indent=2);f.write('\n')
 print('Prepared',out,'duration',frames/rate,'seconds; no deployment/playback performed')
if __name__=='__main__':main()
