#!/usr/bin/env python3
"""Generate one speech clip and package it for the existing Wolf audio loader."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,wave
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;ROOT=TASK.parents[3]
TEXT='The Wolf Agent notifies you that an animated test fixture is starting now.'
OUT=TASK/'build/voice';JUKE=Path('/Agon/mystuff/AgonJukebox')
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 mp3=OUT/'wolf-start.mp3';wav=OUT/'wolf-start.wav'
 if not mp3.exists():
  from gtts import gTTS
  gTTS(text=TEXT,lang='en',tld='co.uk',timeout=(5,20)).save(str(mp3))
 tempdir=OUT/'converter-tmp';tempdir.mkdir(exist_ok=True)
 subprocess.run([str(JUKE/'.venv/bin/python'),str(JUKE/'scripts/make_wav.py'),str(mp3),'-o',str(wav),'--sample-rate','16000','--compress'],check=True,env=dict(os.environ,TMPDIR=str(tempdir.resolve())))
 spec=importlib.util.spec_from_file_location('jukebox_wav',JUKE/'scripts/make_wav.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.validate_agon_wav(wav)
 with wave.open(str(wav),'rb') as f:
  assert (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getcomptype())==(1,1,16000,'NONE')
  frames=f.getnframes();pcm=f.readframes(frames);assert len(pcm)==frames
 assert 0<frames<=300000
 sys.path.insert(0,str(ROOT/'agonport/tools/wolf3d_assets'))
 from agnb.audio import AudioBufferRecord,build_audio_container
 (OUT/'voice.agnb').write_bytes(build_audio_container([AudioBufferRecord(0,'Wolf test start',0xf100,16000,pcm)]))
 ticks=(frames*120+15999)//16000+60
 (OUT/'voice_duration.inc').write_text(f'WP_VOICE_WAIT_TICKS: equ {ticks}\n')
 files=[mp3,wav,OUT/'voice.agnb',OUT/'voice_duration.inc']
 (OUT/'manifest.json').write_text(json.dumps(dict(text=TEXT,engine='gTTS2.5.4',language='en',tld='co.uk',sample_rate=16000,pcm_bytes=frames,seconds=frames/16000,wait_ticks=ticks,buffer_id=0xf100,files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}),indent=2)+'\n')
 print('Prepared speech; PCM seconds:',frames/16000)
if __name__=='__main__':main()
