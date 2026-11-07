// Host-only diagnostic: includes the actual immutable original renderer body.
#include "build/r01/original/production/wolf3d_renderer.cpp"
#include "original_numeric.inc"
#include "candidate_numeric.inc"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <vector>
using namespace wolf3d_production;
namespace {
void require(bool ok,const char *why){if(!ok)throw std::runtime_error(why);}
std::vector<uint8_t> read(const char *p){std::ifstream f(p,std::ios::binary);require(bool(f),"input missing");return {std::istreambuf_iterator<char>(f),{}};}
uint16_t u16(const std::vector<uint8_t>&b,size_t n){return uint16_t(b.at(n))|uint16_t(b.at(n+1))<<8;}
uint32_t u32(const std::vector<uint8_t>&b,size_t n){return uint32_t(u16(b,n))|uint32_t(u16(b,n+2))<<16;}
struct Stats {uint64_t attempted=0,near_rejected=0,divisions=0,narrow=0,wide=0,accepted=0,negative=0;
 uint64_t max_n=0,max_d=0,min_d=UINT64_MAX;};
void scene(const char *name,const std::vector<StaticObject>&objects,const std::vector<uint8_t>&angles,const Player &player){
 Stats s;
 for(size_t pose=0;pose<600;++pose){
  WorldMirror world{};world.player=player;world.player.angle=u16(angles,pose*2);
  require(world.player.angle==((720*(pose+1)/600)%360),"actual angle sequence differs");
  const ViewState view=setup_view(world);
  for(const auto &o:objects){
   if(o.shape<0)continue;
   ++s.attempted;
   const int32_t x=int32_t(o.tile_x)*65536+32768,y=int32_t(o.tile_y)*65536+32768;
   const int32_t gx=x-view.x,gy=y-view.y;
   // Independent arithmetic expression, preserving each existing fixed rounding.
   const auto mul=[](int32_t a,int32_t b){return int32_t((int64_t(a)*int64_t(b))>>16);};
   const int32_t dx=mul(gx,view.cosine)-mul(gy,view.sine)-0x4000;
   const int32_t dy=mul(gy,view.cosine)+mul(gx,view.sine);
   int32_t actual_dx=0,actual_dy=0,screen_x=0;uint32_t height=0;
   const bool visible=transform_point(x,y,view,actual_dx,actual_dy,screen_x,height);
   require(actual_dx==dx&&actual_dy==dy,"actual transform differs from independent input reconstruction");
   if(dx<0x5800){++s.near_rejected;require(!visible&&height==0&&screen_x==127,"near guard differs");continue;}
   ++s.divisions;
   const int64_t numerator=int64_t(dy)*87,denominator=dx;
   const uint64_t magnitude=numerator<0?uint64_t(0)-uint64_t(numerator):uint64_t(numerator);
   const uint64_t divisor=uint64_t(denominator);
   const int64_t expected=numerator/denominator;
   require(original::original_sdiv(numerator,denominator)==expected&&candidate::candidate_sdiv(numerator,denominator)==expected,"exact native helper body differs on actual projection input");
   require(screen_x==127+int32_t(expected),"actual screen x differs");
   require(height==uint32_t(22272/(dx>>8)),"actual projected height differs");
   const bool expected_visible=height!=0&&screen_x>=-127&&screen_x<=383;
   require(visible==expected_visible,"projection acceptance differs");
   if((magnitude>>32)==0&&(divisor>>32)==0)++s.narrow;else ++s.wide;
   if(numerator<0)++s.negative;
   if(visible)++s.accepted;
   s.max_n=std::max(s.max_n,magnitude);s.max_d=std::max(s.max_d,divisor);s.min_d=std::min(s.min_d,divisor);
  }
 }
 require(s.attempted==s.near_rejected+s.divisions&&s.divisions==s.narrow+s.wide,"partition mismatch");
 std::cout<<"{\"scene\":\""<<name<<"\",\"poses\":600,\"objects\":"<<objects.size()<<",\"attempted\":"<<s.attempted<<",\"near_rejected\":"<<s.near_rejected<<",\"divisions\":"<<s.divisions<<",\"narrow\":"<<s.narrow<<",\"wide\":"<<s.wide<<",\"negative\":"<<s.negative<<",\"accepted\":"<<s.accepted<<",\"max_unsigned_numerator\":"<<s.max_n<<",\"min_denominator\":"<<s.min_d<<",\"max_denominator\":"<<s.max_d<<"}\n";
}
}
int main(int argc,char**argv){try{
 require(argc==3,"require exact W3L and binary angle words");const auto b=read(argv[1]),angles=read(argv[2]);
 require(b.size()>=64&&b[0]=='W'&&b[1]=='3'&&b[2]=='L'&&b[3]=='1'&&b[4]==1&&b[6]==0,"wrong level");
 require(angles.size()==1200,"wrong angle extent");Player player{int32_t(u32(b,16)),int32_t(u32(b,20)),0};
 require(player.x==34*65536+32768&&player.y==36*65536+32768,"wrong camera");
 const size_t count=u16(b,10),offset=u16(b,28);require(count==121&&offset+count*6<=b.size(),"wrong static extent");
 std::vector<StaticObject> room;for(size_t i=0;i<count;++i){const size_t at=offset+i*6;room.push_back({int16_t(u16(b,at+2)),b.at(at),b.at(at+1),b.at(at+4)});}
 scene("retained-room",room,angles,player);
 std::vector<StaticObject> rich;for(auto point:std::vector<std::pair<uint8_t,uint8_t>>{{33,36},{35,36},{34,35},{34,37},{33,35},{35,35},{33,37},{35,37}})rich.push_back({14,point.first,point.second,0});
 scene("retained-eight-statics",rich,angles,player);
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
