#!/usr/bin/env python3
"""Task-siloed diagnostic build. No production or donor files are modified."""
from pathlib import Path
import hashlib, importlib.util, json, shutil, struct, subprocess, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BUILD=HERE/'build'
GAME=ROOT/'src/asm/wolf3d/src'
PROD=ROOT/'agonport/vdplet/production'
SDK=Path('/Agon/mystuff/agon-vdplet/build/vdpl-014/baseline')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def replace(s,old,new):
 if s.count(old)!=1: raise ValueError(f'patch anchor count {s.count(old)}: {old[:100]}')
 return s.replace(old,new)
def prepare():
 BUILD.mkdir(exist_ok=True)
 native=BUILD/'native-source';native.mkdir(exist_ok=True)
 for p in PROD.glob('*'):
  if p.suffix in ('.h','.cpp'):shutil.copyfile(p,native/p.name)
 shutil.copyfile(PROD.parent/'wolf3d_tables.inc',BUILD/'wolf3d_tables.inc')
 s=(native/'wolf3d_module.cpp').read_text()
 s=s.replace('int32_t vdplet_entry(', 'int32_t wp_production_entry(')
 pre='''// Task diagnostic: CCOUNT intervals, adapted from Rally phase_probe.c.
static unsigned wp_render_cycles, wp_scope_cycles, wp_log_count;
static inline unsigned wp_clock() { unsigned x; __asm__ __volatile__("rsr.ccount %0":"=a"(x)::"memory"); return x; }
static inline unsigned wp_core() { unsigned x; __asm__ __volatile__("rsr.prid %0":"=a"(x)::"memory"); return x; }
'''
 s=pre+s
 s=replace(s,'    if (direct_rows) {\n        uintptr_t', '    const unsigned wp_scope_start = wp_clock();\n    if (direct_rows) {\n        uintptr_t')
 s=replace(s,'            const RenderDetail rendered = render_world_direct(', '            const unsigned wp_core_start = wp_clock();\n            const RenderDetail rendered = render_world_direct(')
 s=replace(s,'                g_module.mirror, resources, target);', '                g_module.mirror, resources, target);\n            wp_render_cycles = wp_clock() - wp_core_start;')
 s=replace(s,'    preserve_first_error(\n        status, host->buffer_release(host->context, tilemap.lease));', '    wp_scope_cycles = wp_clock() - wp_scope_start;\n    preserve_first_error(\n        status, host->buffer_release(host->context, tilemap.lease));')
 s+='''
static void wp_put32(unsigned char *p,unsigned x) { for(unsigned i=0;i<4;++i)p[i]=(unsigned char)(x>>(8*i)); }
extern "C" __attribute__((visibility("default")))
int32_t vdplet_entry(const vdplet_host_v1 *h,const vdplet_request_v1 *r) {
 if(!h || !r) return VDPL_E_ABI;
 if(r->operation==VDPL_INIT)wp_log_count=0;
 if(r->operation==VDPL_RUN && r->entry_id==100) {wp_log_count=0;return VDPL_OK;}
 unsigned c0=wp_core(),t0=wp_clock();
 int32_t rc=wp_production_entry(h,r);
 unsigned total=wp_clock()-t0;
 if(rc || r->operation!=VDPL_RUN || r->entry_id!=W3P_ENTRY_APPLY_AND_RENDER)return rc;
 if(wp_log_count>=602 || c0!=wp_core())return VDPL_E_LIMIT;
 vdplet_view_v1 v={sizeof(v),0,nullptr,0,0};
 rc=h->buffer_acquire(h->context,0xf000,VDPL_WRITE,0,12056,&v);
 if(rc)return rc;
 if(!v.data || v.bytes<12056)rc=VDPL_E_BOUNDS;
 else {
  unsigned char *p=v.data+16+wp_log_count*20;
  wp_put32(p,wp_log_count);wp_put32(p+4,wolf3d_production::g_module.mirror.player.angle);
  wp_put32(p+8,wp_render_cycles);wp_put32(p+12,wp_scope_cycles);wp_put32(p+16,total);
  ++wp_log_count;
  wp_put32(v.data,0x314e5057);wp_put32(v.data+4,1);wp_put32(v.data+8,wp_log_count);wp_put32(v.data+12,c0);
 }
 int32_t release=h->buffer_release(h->context,v.lease);
 return rc?rc:release;
}
'''
 (native/'wolf3d_module.cpp').write_text(s)
 subprocess.run([sys.executable,str(SDK/'tools/build_module.py'),str(native/'wolf3d_module.cpp'),'--output',str(BUILD/'module'),'--name','wolf_perf','--capabilities','257','--abi-minor','6','--text-limit','65536','--data-limit','16384','--stack-limit','2048','--image-limit','131072','--build-id','0x20261104'],check=True)
 module=BUILD/'module/wolf_perf.vdpl'
 build=load('wolf_builder',ROOT/'src/asm/wolf3d/scripts/build.py')
 asm=build.resolve_assembler(None)
 sys.path.insert(0,str(ROOT/'agonport/tools/wolf3d_assets'))
 from formats.level_package import LevelPackage,parse_package,build_package
 acceptance=load('wolf_acceptance',ROOT/'src/asm/wolf3d_acceptance/scripts/prepare.py')
 package_source=ROOT/'agonport/assets/generated/wolf3d'
 manifests=[]
 for mode,label in [(1,'cpu'),(2,'unpaced'),(3,'paced'),(1,'cpu-fail')]:
  out=BUILD/label;src=out/'source';src.mkdir(parents=True,exist_ok=True)
  for p in GAME.iterdir():
   if p.is_file():shutil.copyfile(p,src/p.name)
  build.select_backend(src/'wolf3d_backend.inc','vdplet-direct')
  build.select_package(src/'wolf3d_vdplet_package.inc',module.stat().st_size)
  # Production's fixed 0x60000 staging address overlaps this application's
  # executable includes. Reserve real task-owned storage after the fixture.
  client=src/'wolf3d_vdplet_client.inc'
  c=replace(client.read_text(),'W3D_VDPLET_PACKAGE_ADDRESS:    equ 060000h','W3D_VDPLET_PACKAGE_ADDRESS:    equ 0a0000h')
  c=replace(c,'W3D_VDPLET_PACKAGE_LIMIT:      equ 020000h',f'W3D_VDPLET_PACKAGE_LIMIT:      equ {module.stat().st_size+1}')
  client.write_text(c)
  lines=[]; stack=[]; active=True
  for line in (HERE/'src/bench.inc').read_text().splitlines():
   t=line.strip()
   if t.startswith('.if WP_MODE'):
    expr=t[len('.if WP_MODE'):].strip(); op,num=expr[0],int(expr[1:]); cond=(mode==num if op=='=' else mode>num)
    stack.append((active,cond));active=active and cond
   elif t=='.else':
    parent,cond=stack[-1];active=parent and not cond
   elif t=='.endif': active=stack.pop()[0]
   elif active: lines.append(line)
  assert not stack
  bench='\n'.join(lines)+'\n'
  if label=='cpu-fail':bench=replace(bench,'    call wp_prt_init\n','    call wp_prt_init\n    jp wp_failed ; intentional owned-timer failure control\n')
  (src/'bench.inc').write_text(bench)
  (src/'angles.inc').write_text('\n'.join('    dw '+str((720*n//600)%360) for n in range(1,601))+'\n')
  s=(src/'wolf3d.asm').read_text()
  s=replace(s,'    include "wolf3d_start.inc"','    include "wolf3d_start.inc"\nWP_MODE: equ '+str(mode))
  s=replace(s,'    call w3d_shell_run\n    push af','    ld a,W3D_SHELL_RESULT_NEW_GAME\n    push af')
  s=replace(s,'    call w3d_music_start_current_floor\n','    call wp_run\n    jp w3d_gameplay_exit_shutdown\n')
  # Physical appliance setup only: avoid redundant mode switch and settle
  # after confirmed native mode selection, outside every measurement bracket.
  s=replace(s,'    jr nz,@configure\n    call w3d_arm_gameplay_mode_fence',
    '    jr nz,@configure\n    MOSCALL mos_sysvars\n    ld a,(ix+sysvar_scrMode)\n    cp 136\n    jr z,@mode_ready\n    call w3d_arm_gameplay_mode_fence')
  s=replace(s,'    call w3d_wait_for_gameplay_mode\n    ret c\n    ld a,1',
    '    call w3d_wait_for_gameplay_mode\n    ret c\n@mode_ready:\n    call wp_settle_display\n    ld a,1')

  s+='\n    include "bench.inc"\n'
  (src/'wolf3d.asm').write_text(s)
  payload=out/'payload';payload.mkdir(exist_ok=True)
  shutil.copyfile(module,payload/'wolf3d.vdpl')
  subprocess.run([str(asm),'wolf3d.asm','wp.bin','-l','-c'],cwd=src,check=True)
  shutil.copyfile(src/'wp.bin',payload/'wolf3d.bin')
  scratch=0xa0000
  image_end=0x40000+(payload/'wolf3d.bin').stat().st_size
  if image_end>scratch or scratch+module.stat().st_size>0xb0000:
   raise ValueError('staging overlap or insufficient MOS stack reserve')
  layout={'image_base':0x40000,'executable_and_data_end':image_end,'package_scratch':scratch,'package_scratch_bytes':module.stat().st_size,'image_end':image_end,'stack_reserve_start':0xb0000}
  (out/'memory-layout.json').write_text(json.dumps(layout,indent=2)+'\n')
  for filename,rel in [('hud.agnb','hud/hud.agnb'),('sfx.agnb','audio/sfx.agnb'),('shell.agnb','shell/shell.agnb')]:shutil.copyfile(package_source/rel,payload/filename)
  dest=payload/'level_00';dest.mkdir(exist_ok=True)
  for filename in ['tiles.agnb','sprites.agnb']:shutil.copyfile(package_source/'levels/level_00'/filename,dest/filename)
  for difficulty in ['baby','easy','medium','hard']:
   p=package_source/f'levels/level_00/state_{difficulty}.w3l';level=parse_package(p.read_bytes())
   acceptance.require_open(level,(34,36))
   sections=dict(level.sections);sections['actors']=b''
   new=LevelPackage(level=0,difficulty=level.difficulty,door_count=level.door_count,static_count=level.static_count,actor_count=0,random_index=0,player_pose=struct.pack('<iiH',0x228000,0x248000,0),sections=sections)
   data=build_package(new);assert parse_package(data).actor_count==0
   (dest/p.name).write_bytes(data)
  (payload/'wolf3d.cfg').write_bytes(b'') # config falls back, then task disables audio below
  expected={'schema':'wolf-perf-001-inputs-v1','mode':label,'steps':600,'degrees':720,'nominal_seconds':20,'tile':[34,36],'enemies':0,'files':{str(p.relative_to(payload)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(payload.rglob('*')) if p.is_file() and p.suffix!='.lst' and p.name!='expected.json'}}
  (payload/'expected.json').write_text(json.dumps(expected,indent=2)+'\n');manifests.append(expected)
 (BUILD/'inputs.json').write_text(json.dumps({'modes':manifests,'production_sources':{str(p.relative_to(ROOT)):sha(p) for p in sorted(GAME.iterdir()) if p.is_file()},'module_sources':{str(p.relative_to(ROOT)):sha(p) for p in sorted(PROD.glob('*.cpp'))}},indent=2)+'\n')
if __name__=='__main__':prepare()
