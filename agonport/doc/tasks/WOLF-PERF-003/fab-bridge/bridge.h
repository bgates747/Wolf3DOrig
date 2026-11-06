#ifndef WOLF_FAB_SOURCE_BRIDGE_H
#define WOLF_FAB_SOURCE_BRIDGE_H
// SINGLE-MODULE HOST-SOURCE VISUAL ADAPTER. Not an Xtensa loader/runtime.
// Actual buffered VDU assets/producer and live Fab hidden rows are used.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <array>
#include <limits>
#define WOLF3D_HOST_TEST 1
#define vdplet_entry wolf_fab_production_entry
#include "host-module/production/wolf3d_module.cpp"
#undef vdplet_entry
#include "expected_package.h"
namespace wolf_fab {
struct Lease {uint32_t token=0,offset=0,bytes=0;uint16_t access=0;std::shared_ptr<BufferStream> owner;bool workspace=false;};
struct State {
 bool loaded=false,busy=false,frame=false;uint32_t sequence=0,frame_token=0,loads=0,unloads=0,renders=0,errors=0,residual=0;
 uint16_t argument=65535,last=0;std::shared_ptr<BufferStream> argument_owner;
 std::array<Lease,4> leases;std::vector<uint8_t> workspace;
} state;
static void report() {
 const char *path=std::getenv("WOLF_FAB_BRIDGE_REPORT");if(!path)return;
 FILE*f=std::fopen(path,"w");if(!f)return;
 std::fprintf(f,"{\"adapter\":\"native-production-source;not-Xtensa\",\"loads\":%u,\"unloads\":%u,\"renders\":%u,\"errors\":%u,\"residual_cleanup\":%u,\"loaded\":%s,\"busy\":%s,\"frame\":%s}\n",state.loads,state.unloads,state.renders,state.errors,state.residual,state.loaded?"true":"false",state.busy?"true":"false",state.frame?"true":"false");std::fclose(f);
}
static std::shared_ptr<BufferStream> owner(uint16_t id){auto it=buffers.find(id);return it!=buffers.end()&&it->second.size()==1?it->second[0]:nullptr;}
static void close_frame(){if(state.frame)canvas->endUpdate();state.frame=false;state.frame_token=0;}
static int32_t acquire(void*,uint16_t id,uint16_t access,uint32_t offset,uint32_t bytes,vdplet_view_v1*out){
 if(!state.busy||!out||out->struct_bytes<sizeof(*out)||(access!=VDPL_READ&&access!=VDPL_WRITE))return VDPL_E_ARGUMENT;
 auto o=owner(id);if(!o)return VDPL_E_BUFFER;
 if(access==VDPL_WRITE&&(id==state.argument||o==state.argument_owner))return VDPL_E_ARGUMENT;
 bool workspace=id==0x7100;uint32_t size=workspace?state.workspace.size():o->size();
 if(offset>size)return VDPL_E_BOUNDS;if(bytes==VDPL_WHOLE_BUFFER)bytes=size-offset;if(bytes>size-offset)return VDPL_E_BOUNDS;
 Lease*free=nullptr;
 for(auto&l:state.leases){if(!l.token){if(!free)free=&l;continue;}if(l.owner==o&&(access==VDPL_WRITE||l.access==VDPL_WRITE)&& (offset<=l.offset?l.offset-offset<bytes:offset-l.offset<l.bytes))return VDPL_E_BUSY;}
 if(!free||state.sequence==UINT32_MAX)return VDPL_E_LIMIT;
 *free={++state.sequence,offset,bytes,access,o,workspace};uint8_t*data=workspace?state.workspace.data():o->getBuffer();
 *out={sizeof(*out),free->token,data+offset,bytes,access};return VDPL_OK;
}
static int32_t release(void*,uint32_t token){if(!state.busy||!token)return VDPL_E_ARGUMENT;for(auto&l:state.leases)if(l.token==token){l=Lease{};return VDPL_OK;}return VDPL_E_HANDLE;}
static int32_t color(void*,uint32_t operation,vdplet_color_frame_v1*f){
 if(!state.busy||!f||f->struct_bytes<sizeof(*f))return VDPL_E_ARGUMENT;
 f->data=nullptr;f->row_bytes=0;
 if(operation==VDPL_COLOR_FRAME_BEGIN){
  if(state.frame||f->lease)return VDPL_E_BUSY;
  if(!_VGAController||!canvas||!_VGAController->isDoubleBuffered()||_VGAController->nativePixelFormat()!=fabgl::NativePixelFormat::SBGR2222)return VDPL_E_UNSUPPORTED;
  if(f->x||f->y||f->width!=320||f->height!=240||_VGAController->getViewPortWidth()!=320||_VGAController->getViewPortHeight()!=240)return VDPL_E_BOUNDS;
  canvas->beginUpdate();canvas->waitCompletion(false);
  for(unsigned y=0;y<240;++y){auto row=_VGAController->getScanline(y);if(!row||(reinterpret_cast<uintptr_t>(row)&3)){canvas->endUpdate();return VDPL_E_FORMAT;}}
  state.frame=true;state.frame_token=++state.sequence;f->lease=state.frame_token;return VDPL_OK;
 }
 if(!state.frame||!f->lease||f->lease!=state.frame_token)return VDPL_E_HANDLE;
 if(operation==VDPL_COLOR_FRAME_END){close_frame();f->lease=0;return VDPL_OK;}
 if(operation!=VDPL_COLOR_FRAME_ROW)return VDPL_E_ARGUMENT;if(f->row>=240)return VDPL_E_BOUNDS;
 f->data=_VGAController->getScanline(f->row);f->row_bytes=320;f->native_format=VDPL_NATIVE_RGB222;f->x_bias=0;f->pixel_xor=2;f->color_mask=0x3f;f->preserve_mask=0xc0;return VDPL_OK;
}
static vdplet_host_v1_6 host=[](){vdplet_host_v1_6 h{};auto&b=h.base.base.base.base.base.base;b.struct_bytes=sizeof(h);b.abi_major=1;b.abi_minor=6;b.capabilities=257;b.context=&state;b.buffer_acquire=acquire;b.buffer_release=release;h.color_frame=color;return h;}();
static int32_t invoke(uint16_t operation,uint16_t entry,uint16_t argument){
 if(state.busy)return VDPL_E_BUSY;if(!state.loaded)return VDPL_E_HANDLE;
 auto o=argument==65535?nullptr:owner(argument);if(operation==VDPL_RUN&&!o)return VDPL_E_BUFFER;
 state.busy=true;state.argument=argument;state.argument_owner=o;
 vdplet_request_v1 r{sizeof(r),operation,entry,argument,0,o?o->size():0};
 int32_t result=wolf_fab_production_entry(&host.base.base.base.base.base.base,&r);
 if(state.frame){++state.residual;close_frame();}
 for(auto&l:state.leases){if(l.token)++state.residual;l=Lease{};}
 state.argument_owner.reset();state.argument=65535;state.busy=false;
 if(!result&&operation==VDPL_RUN&&entry==W3P_ENTRY_APPLY_AND_RENDER)++state.renders;
 return result;
}
static uint16_t u16(const uint8_t*p){return p[0]|uint16_t(p[1])<<8;}
static uint32_t u32(const uint8_t*p){return u16(p)|uint32_t(u16(p+2))<<16;}
static int32_t install(uint16_t id,uint32_t bytes){
 if(state.loaded||state.busy)return VDPL_E_BUSY;auto o=owner(id);if(!o)return VDPL_E_BUFFER;
 if(bytes!=sizeof(wolf_expected_package)||o->size()!=bytes||std::memcmp(o->getBuffer(),wolf_expected_package,bytes))return VDPL_E_FORMAT;
 // Native pointer-width adaptation, invisible to the eZ80 buffer protocol.
 state.workspace.assign(W3P_DIRECT_WORKSPACE_BYTES,0);state.loaded=true;
 int32_t rc=invoke(VDPL_INIT,0,65535);if(rc){state.loaded=false;state.workspace.clear();return rc;}++state.loads;return VDPL_OK;
}
static int32_t unload(uint16_t handle){if(handle!=1||!state.loaded)return VDPL_E_HANDLE;if(state.busy)return VDPL_E_BUSY;int32_t rc=invoke(VDPL_FINI,0,65535);if(!rc){state.loaded=false;state.workspace.clear();++state.unloads;}return rc;}
static int32_t info(uint16_t field,uint16_t&value){switch(field){case 0:value=0x0100;break;case 1:value=257;break;case 2:value=state.loaded?1:0;break;case 3:value=state.last;break;case 8:value=state.loads;break;default:return VDPL_E_UNSUPPORTED;}return VDPL_OK;}
}
// Member dispatch retains ordinary parser framing/timeout and MOS callback path.
void VDUStreamProcessor::vdu_sys_wolf_fab(bool discovery){
 using namespace wolf_fab;static bool registered=false;if(!registered){std::atexit(report);registered=true;std::fprintf(stderr,"WOLF FAB: native production-source VDPlet bridge (NOT Xtensa execution)\n");}
 auto reply=[this](uint8_t kind,uint16_t token,uint16_t value){uint8_t p[]={'V','D','P','L',1,kind,uint8_t(token),uint8_t(token>>8),uint8_t(value),uint8_t(value>>8)};send_packet(PACKET_KEYCODE,sizeof(p),p);};
 if(discovery){reply(VDPL_REPLY_IDENT,0,257);return;}
 int length=readWord_t();if(length<0)return;uint8_t p[32]{};
 if(length>32){discardBytes(length);state.last=VDPL_E_ARGUMENT;return;}
 if(readIntoBuffer(p,length)||length<6){state.last=VDPL_E_ARGUMENT;return;}
 uint16_t token=u16(p+2),value=0;uint8_t op=p[1],flags=p[4],kind=VDPL_REPLY_DONE;int32_t rc=VDPL_OK;
 if(p[0]!=1)rc=VDPL_E_ABI;else if((flags&~1)||p[5])rc=VDPL_E_ARGUMENT;
 else switch(op){
 case VDPL_LOAD:if(length!=14||u16(p+12))rc=VDPL_E_ARGUMENT;else{rc=install(u16(p+6),u32(p+8));value=state.loaded?1:0;kind=VDPL_REPLY_LOADED;}break;
 case VDPL_INVOKE:if(length!=12)rc=VDPL_E_ARGUMENT;else if(u16(p+6)!=1)rc=VDPL_E_HANDLE;else rc=invoke(VDPL_RUN,u16(p+8),u16(p+10));break;
 case VDPL_UNLOAD:if(length!=8)rc=VDPL_E_ARGUMENT;else rc=unload(u16(p+6));break;
 case VDPL_INFO:if(length!=8)rc=VDPL_E_ARGUMENT;else{rc=info(u16(p+6),value);kind=VDPL_REPLY_VALUE;}break;
 default:rc=VDPL_E_UNSUPPORTED;
 }
 if(rc||(op!=VDPL_INFO&&op!=VDPL_READ16))state.last=rc;
 if(rc){++state.errors;kind=VDPL_REPLY_ERROR;value=rc;std::fprintf(stderr,"WOLF FAB bridge error op=%u status=%d\n",op,rc);}
 if(flags&1)reply(kind,token,value);
}
#endif
extern "C" int wolf_fab_bridge_selftest(){
 using namespace wolf_fab;int failures=0;auto expect=[&](int a,int b){if(a!=b)++failures;};
 const uint16_t id=0x7ffe;auto b=std::make_shared<BufferStream>(sizeof(wolf_expected_package));std::memcpy(b->getBuffer(),wolf_expected_package,sizeof(wolf_expected_package));buffers[id]={b};
 b->getBuffer()[0]^=1;expect(install(id,b->size()),VDPL_E_FORMAT);b->getBuffer()[0]^=1;
 expect(install(id,b->size()),VDPL_OK);expect(install(id,b->size()),VDPL_E_BUSY);
 vdplet_view_v1 r{sizeof(r),0,nullptr,0,0};expect(acquire(nullptr,id,VDPL_READ,0,4,&r),VDPL_E_ARGUMENT);
 state.busy=true;expect(acquire(nullptr,id,VDPL_READ,0,4,&r),VDPL_OK);uint32_t token=r.lease;
 vdplet_view_v1 w{sizeof(w),0,nullptr,0,0};expect(acquire(nullptr,id,VDPL_WRITE,0,4,&w),VDPL_E_BUSY);
 expect(acquire(nullptr,id,VDPL_READ,b->size(),1,&w),VDPL_E_BOUNDS);
 expect(release(nullptr,token),VDPL_OK);expect(release(nullptr,token),VDPL_E_HANDLE);expect(unload(1),VDPL_E_BUSY);
 vdplet_color_frame_v1 f{};f.struct_bytes=sizeof(f);f.width=320;f.height=240;expect(color(nullptr,VDPL_COLOR_FRAME_BEGIN,&f),VDPL_E_UNSUPPORTED);
 state.busy=false;expect(unload(2),VDPL_E_HANDLE);expect(unload(1),VDPL_OK);
 expect(state.loaded,0);expect(state.frame,0);expect(state.residual,0);buffers.erase(id);state=State{};
 return failures;
}
