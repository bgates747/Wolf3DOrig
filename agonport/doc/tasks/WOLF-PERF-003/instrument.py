"""Apply checked, task-only recorder and client changes to frozen inputs."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent


def once(text,old,new):
    if text.count(old)!=1:
        raise ValueError(f'expected one patch anchor, found {text.count(old)}: {old[:100]}')
    return text.replace(old,new)


def standalone_native(source):
    s=source.read_text()
    s=once(s,'#include <algorithm>','#include <algorithm>\n#include "wolf_perf_recorder.h"\n'+'''static inline uint32_t wp_clock() {
    uint32_t value; __asm__ __volatile__("rsr.ccount %0":"=a"(value)::"memory"); return value;
}
static inline uint32_t wp_core() {
    uint32_t value; __asm__ __volatile__("rsr.prid %0":"=a"(value)::"memory"); return value;
}
''')
    s=once(s,'\tbool render_frame(VDUStreamProcessor& processor) {\n\t\tdebug_log("Wolf3D render_frame: begin\\n\\r");',
           '\tbool render_frame(VDUStreamProcessor& processor, uint32_t wp_dispatch) {\n\t\tconst uint32_t wp_c0=wp_core(), wp_begin=wp_clock();')
    s=once(s,'\t\tm_render_sequence++;\n\t\tsend_render_complete',
           '\t\tconst uint32_t wp_end=wp_clock(), wp_c1=wp_core();\n\t\tif (!wp_recorder.finish(uint32_t(m_world.playerAngle), wp_end-wp_begin, wp_end-wp_dispatch, wp_c0, wp_c1)) return false;\n\t\tm_render_sequence++;\n\t\tsend_render_complete')
    s=once(s,'\t\tdebug_log("Wolf3D render_frame: complete, sequence %u\\n\\r",\n\t\t\tm_render_sequence);\n','')
    s=once(s,'\tbool handle_subcommand(VDUStreamProcessor& processor, uint8_t subcmd) {',
           (HERE/'src/standalone_control.h').read_text()+'\n\tbool handle_subcommand(VDUStreamProcessor& processor, uint8_t subcmd) {')
    s=once(s,'case 7:  return render_frame(processor);',
           'case 7:  { const uint32_t start=wp_clock(); return render_frame(processor,start); }\n\t\t\tcase 240: case 241: return wp_control(processor,subcmd);')
    source.write_text(s)
    shutil.copyfile(HERE/'src/recorder.h',source.parent/'wolf_perf_recorder.h')


def standalone_guest(src):
    # Preserve ordinary calls except deferring the exact production producer's
    # two pose-only command packets during measured packing. Replay each RST
    # separately; warm-up and startup use the original immediate wire path.
    p=src/'wolf3d_motion.inc';s=p.read_text();begin=s.index('w3d_submit_dirty_world_render_marked:');end=s.index('; Submit only changed status fields.',begin)
    body=s[begin:end]
    if body.count('    rst.lil 18h')!=5:raise ValueError('standalone command-owner layout changed')
    s=s[:begin]+body.replace('    rst.lil 18h','    call wp_a_capture_wire')+s[end:];p.write_text(s)
    p=src/'wolf3d_render_async.inc';s=p.read_text()
    s=once(s,'    call w3d_try_capture_version_packet\n', '    call wp_a_try_capture\n    jp c,@done\n    call w3d_try_capture_version_packet\n')
    start=s.index('w3d_consume_render_completion:'); end=s.index('; Shared acceptance tail',start)
    body=once(s[start:end],'    call w3d_vdu_present\n','    ; Task harness presents after completion timestamp.\n')
    s=s[:start]+body+s[end:]
    p.write_text(s)


def standalone_bench(bench):
    s=bench
    start=s.index('    ld bc,0f000h\n');end=s.index('    ; ez80asm DS',start)
    s=s[:start]+'''    call wp_a_create_log
    jp c,wp_failed
    call w3d_mark_full_level_dirty
    ; Bind the resident tilemap before replay: dirty updates alone do not INIT.
    call w3d_submit_level_reset
    jp c,wp_failed
    call wp_a_wait
    jp c,wp_failed
    call w3d_vdu_present
    call wp_a_fence
    jp c,wp_failed
    ld a,1
    ld (w3d_player_dirty),a
    call wp_warm_frame
    call wp_a_reset
    jp c,wp_failed
'''+s[end:]
    s=s.replace('call w3d_vdplet_batch_prepare','call wp_a_prepare')
    s=once(s,'    call w3d_vdplet_batch_mark_submitted\n    call w3d_vdplet_batch_accept_success\n',
           '    call wp_a_retire\n')
    start=s.index('    ld hl,(wp_batch_address)\n');end=s.index('    ld ix,(wp_row_ptr)\n    ld hl,(wp_ticks)\n    ld (ix+15),hl',start)
    s=s[:start]+'''    call wp_a_submit
    jp c,wp_failed
'''+s[end:]
    anchor='    call w3d_vdplet_wait_run\n    jp c,wp_failed\n    call w3d_vdplet_batch_accept_success\n    jp c,wp_failed\n'
    if s.count(anchor)!=2:raise ValueError('timed and warm wait anchors changed')
    s=s.replace(anchor,'    call wp_a_wait\n    jp c,wp_failed\n')
    s=s.replace('call w3d_vdplet_query_identity','call wp_a_fence')
    start=s.index('wp_warm_frame:\n');end=s.index('wp_write:\n',start)
    s=s[:start]+'''wp_warm_frame:
    call w3d_submit_dirty_world_render
    jp c,wp_failed
    call wp_a_wait
    jp c,wp_failed
    call w3d_vdu_present
    call wp_a_fence
    jp c,wp_failed
    ret
wp_read16:
    jp wp_a_read16
'''+s[end:]
    return s+'\n    include "standalone.inc"\n'


def vdplet_native(source):
    s=source.read_text()
    helper='''// WOLF-PERF-003: native fully-received-command bracket, no UART logging.
static inline uint32_t wpb_clock() {
    uint32_t value; __asm__ __volatile__("rsr.ccount %0":"=a"(value)::"memory"); return value;
}
static inline uint32_t wpb_core() {
    uint32_t value; __asm__ __volatile__("rsr.prid %0":"=a"(value)::"memory"); return value;
}
static bool wpb_finish(uint32_t start, uint32_t end, uint32_t core0, uint32_t core1) {
    const auto found=buffers.find(0xf000);
    if (found==buffers.end()) return true; // startup before task log ownership
    if (found->second.size()!=1 || found->second[0]->size()<12056) return false;
    uint8_t *p=found->second[0]->getBuffer();
    if (!p || vdpl::u32(p)!=0x314e5057 || vdpl::u32(p+4)!=1) return false;
    const uint32_t count=vdpl::u32(p+8), elapsed=end-start;
    if (!count || count>600 || core0!=core1 || core0!=vdpl::u32(p+12)) return false;
    p+=16+(count-1)*20;
    if (vdpl::u32(p)!=count-1 || !elapsed || elapsed>=0x80000000u || elapsed<vdpl::u32(p+12)) return false;
    for (unsigned i=0;i<4;++i) p[16+i]=uint8_t(elapsed>>(8*i));
    return true;
}
'''
    s=once(s,'void VDUStreamProcessor::vdu_sys_vdplet(',helper+'\nvoid VDUStreamProcessor::vdu_sys_vdplet(')
    anchor='    if (readIntoBuffer(payload,length)) { vdpl_runtime::state.last_status=VDPL_E_ARGUMENT; return; }\n'
    s=once(s,anchor,anchor+'    const uint32_t wpb_start=wpb_clock(), wpb_c0=wpb_core();\n')
    anchor='            else rc=vdpl_runtime::invoke(vdpl::u16(payload+6),vdpl::u16(payload+8),vdpl::u16(payload+10));'
    s=once(s,anchor,'''            else {
                rc=vdpl_runtime::invoke(vdpl::u16(payload+6),vdpl::u16(payload+8),vdpl::u16(payload+10));
                const uint32_t wpb_end=wpb_clock(), wpb_c1=wpb_core();
                if (!rc && vdpl::u16(payload+8)==1 && !wpb_finish(wpb_start,wpb_end,wpb_c0,wpb_c1)) rc=VDPL_E_LIMIT;
            }''')
    source.write_text(s)
