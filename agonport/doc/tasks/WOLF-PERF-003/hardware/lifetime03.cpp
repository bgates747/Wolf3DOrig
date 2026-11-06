// Host harness includes the exact extracted native control method and recorder.
#include "wolf_perf_recorder.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <map>
#include <memory>
#include <vector>
struct Buffer {
 std::vector<uint8_t> bytes;
 explicit Buffer(size_t n):bytes(n,0xa5){}
 uint8_t *getBuffer(){return bytes.data();}
 size_t size()const{return bytes.size();}
};
std::map<int,std::vector<std::shared_ptr<Buffer>>> buffers;
constexpr uint8_t PACKET_KEYCODE=0x81;
unsigned wp_core(){return 0xcdcd;}
struct VDUStreamProcessor {
 std::deque<int> words;
 std::vector<uint8_t> reply;
 int readWord_t(){assert(!words.empty());int x=words.front();words.pop_front();return x;}
 void send_packet(int kind,size_t n,const uint8_t*p){assert(kind==0x81);reply.assign(p,p+n);}
};
struct Control {
#include "exact_control.inc"
};
int main(){
 // Old native behavior: full recorder suppresses next render completion.
 WolfPerfRecorder old;std::vector<uint8_t> oldstore(WolfPerfRecorder::bytes);
 assert(old.reset(oldstore.data(),oldstore.size(),0xcdcd));
 for(unsigned n=0;n<600;++n)assert(old.finish(n%360,100,200,0xcdcd,0xcdcd));
 assert(!old.finish(0,100,200,0xcdcd,0xcdcd));
 puts("REPRODUCED old full-recorder refusal before next guest warmup");
 Control c;VDUStreamProcessor p;unsigned cookie=0;
 auto command=[&](int op,int off,bool expected){
  ++cookie;p.words={int(cookie),off};p.reply.clear();
  assert(c.wp_control(p,op)==expected);
  assert(p.reply.size()==10 && p.reply[0]=='P' && p.reply[3]=='R');
  assert(p.reply[4]==1 && p.reply[5]==(0x80|unsigned(expected)));
  assert(p.reply[6]==(cookie&255)&&p.reply[7]==(cookie>>8));
 };
 for(unsigned count:{0u,600u,433u,600u,0u,600u}){
  command(242,0,true); // acknowledged pre-create disarm
  buffers.erase(0xf000);
  for(unsigned n=0;n<2;++n)assert(c.wp_recorder.finish(n,100,200,0xcdcd,0xcdcd));
  buffers[0xf000]={std::make_shared<Buffer>(WolfPerfRecorder::bytes)};
  command(240,0,true);
  for(unsigned n=0;n<count;++n)assert(c.wp_recorder.finish((720*(n+1)/600)%360,100,200,0xcdcd,0xcdcd));
  command(241,0,true);
  auto ptr=c.wp_recorder.data;command(242,1,false);assert(c.wp_recorder.data==ptr);
  if(count==600){assert(!c.wp_recorder.finish(0,100,200,0xcdcd,0xcdcd));command(241,0,false);}
  command(242,0,true); // release recovers even a failed recorder
  assert(c.wp_recorder.data==nullptr && c.wp_recorder.count==0 && !c.wp_recorder.failed);
  buffers.erase(0xf000); // sanitizer verifies subsequent warmups cannot use freed store
  command(241,0,false);
  for(unsigned n=0;n<2;++n)assert(c.wp_recorder.finish(n,100,200,0xcdcd,0xcdcd));
 }
 buffers[0xf000]={std::make_shared<Buffer>(15)};command(240,0,false);command(242,0,true);
 assert(c.wp_recorder.finish(0,100,200,0xcdcd,0xcdcd));
 puts("PASS exact native control: six CPU/full/subset lifecycles, release-before-free, reply binding, invalid offset, stale read, overflow and failed-arm recovery");
}
