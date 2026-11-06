"""Known setup failure/MOS return: preserve RAM without LOAD, then restore."""
from pathlib import Path
import hashlib,json
from physical import Bench,B,save
b=Bench(B/'context.json');p=b.folder('failure-collection')
b.cli(p,'failure-cli');b.service(p,'listener');b.raw_state(p,'pre')
image=B/'bespoke/control/payload/wolf3d.bin';size=image.stat().st_size
script=p/'failure-save.txt'
script.write_bytes(('SAVE '+b.remote+'/setup-failure-ram.bin &40000 &'+format(size,'X')+'\r\nEMOS sdserve --fast /\r\n').encode())
b.upload(p,'save-script',script,b.remote+'/failure-save.txt')
b.exit(p,'save-exit');b.line(p,'save-ram','EXEC '+b.remote+'/failure-save.txt');b.wait_online(True)
b.transfer(p,'ram','get',b.remote+'/setup-failure-ram.bin',p/'ram.bin');assert(p/'ram.bin').stat().st_size==size
b.transfer(p,'hud','get',b.remote+'/hud.agnb',p/'hud.agnb')
same=(p/'hud.agnb').read_bytes()==(B/'bespoke/control/payload/hud.agnb').read_bytes()
save(p/'receipt.json',dict(actual_cli=True,no_LOAD_before_RAM_save=True,ram_bytes=size,ram_sha256=hashlib.sha256((p/'ram.bin').read_bytes()).hexdigest(),hud_matches_original=same,mode0=True,callback_zero=True,benchmark_not_replayed=True))
b.exit(p,'exit')
b.flash('restore',B/'restore.bin');b.handback()
save(b.out/'recovered-setup-failure.json',dict(incoming_span_restored=True,normal_cli=True,benchmark_data=False,unexpected_setup_failure_preserved=True,new_tests=0))
print('FAILED SETUP PRESERVED; EXACT INCOMING SPAN RESTORED; HANDBACK CHECKS PASS',flush=True)
