"""Eight canonical-room pixel/geometry checks using exact frozen AGNB bytes."""
from pathlib import Path
import argparse,hashlib,json,shutil,struct,subprocess,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'agonport/tools/wolf3d_assets'))
from formats.level_package import parse_package
from agnb.container import BufferRecord,build_container,align4


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def chunks(data):
    offset=0
    while offset<len(data):
        if offset+8>len(data):raise ValueError('truncated chunk')
        tag=data[offset:offset+4];length=struct.unpack_from('<I',data,offset+4)[0]
        end=offset+8+length
        if end>len(data):raise ValueError('chunk exceeds parent')
        yield tag,data[offset+8:end]
        offset=align4(end)
    if offset!=len(data):raise ValueError('bad padding')


def prepare(revision,attempt):
    base=HERE/'build'/revision;out=base/attempt;out.mkdir(exist_ok=False)
    raw=out/'assets';raw.mkdir();assets={};sources={}
    for name in ('hud.agnb','level_00/tiles.agnb','level_00/sprites.agnb'):
        source=base/'common-payload'/name;data=source.read_bytes()
        assert data[:4]==b'RIFF'and data[8:12]==b'AGNB'and struct.unpack_from('<I',data,4)[0]+8==len(data)
        records=[]
        for tag,body in chunks(data[12:]):
            if tag==b'VERS':assert body==b'\0\1';continue
            assert tag==b'LIST'and body[:4]==b'BUFR'
            fields=dict(chunks(body[4:]));assert set(fields)=={b'BHDR',b'IMAG',b'DATA'}
            identity=struct.unpack('<H',fields[b'BHDR'])[0]
            w,h,fmt=struct.unpack('<HHB',fields[b'IMAG']);assert fmt==1 and len(fields[b'DATA'])==w*h
            path=raw/f'{identity:04x}.rgba2';assert identity not in assets
            path.write_bytes(fields[b'DATA']);assets[identity]={'path':str(path),'width':w,'height':h,'sha256':sha(path)}
            records.append(BufferRecord(path.stem,identity,w,h,path,w*h))
        assert build_container(records)==data,'canonical writer round-trip failed'
        sources[name]=sha(source)
    level=parse_package((base/'common-payload/level_00/state_medium.w3l').read_bytes())
    assert level.actor_count==0 and level.player_pose==struct.pack('<iiH',0x228000,0x248000,0)
    map_data=','.join(map(str,level.sections['tilemap']))
    doors=[];statics=[]
    for at in range(0,len(level.sections['doors']),10):
        d=level.sections['doors'][at:at+10];doors.append('{%d,%d,%d,%d,%d}'%(int.from_bytes(d[5:7],'little'),d[0],d[1],d[2],d[7]))
    for at in range(0,len(level.sections['statics']),6):
        s=level.sections['statics'][at:at+6];statics.append('{%d,%d,%d}'%(int.from_bytes(s[2:4],'little',signed=True),s[0],s[1]))
    header='''#pragma once
#include <array>
#include <fstream>
#include <stdexcept>
#include "wolf3d_production_contract.h"
namespace wolf3d_renderer_fixture {
constexpr uint16_t kMapId=2,kWallBase=0x1000,kSpriteBase=0x2000,kHudBase=0x4000;
constexpr uint32_t kMapBytes=4096,kTextureBytes=4096,kMaximumAssetBytes=12800;
constexpr int kScenarioCount=8;
struct DoorSpec { uint16_t position; uint8_t x,y,vertical,texture; };
struct ActorSpec { uint16_t slot; int16_t shape; int32_t x,y; uint16_t facing; uint8_t rotations; };
struct StaticSpec { int16_t shape; uint8_t x,y; };
'''+f'constexpr int kDoorCount={level.door_count}, kStaticCount={level.static_count};\n'+'''
struct SceneSpec {
 int32_t player_x,player_y; uint16_t player_angle; int16_t view_weapon_shape;
 uint8_t health,ammo,keys,weapon; uint32_t score; uint8_t level,face,lives,palette_shift;
 DoorSpec doors[kDoorCount]; std::array<ActorSpec,0> actors; StaticSpec statics[kStaticCount];
};
inline SceneSpec scene(int index) {
 SceneSpec s{};s.player_x=0x228000;s.player_y=0x248000;s.player_angle=uint16_t(index*45);
 s.view_weapon_shape=421;s.health=100;s.ammo=8;s.weapon=1;s.level=1;s.lives=3;
 const DoorSpec doors[]={'''+','.join(doors)+'''};
 const StaticSpec statics[]={'''+','.join(statics)+'''};
 for(int i=0;i<kDoorCount;++i)s.doors[i]=doors[i];
 for(int i=0;i<kStaticCount;++i)s.statics[i]=statics[i];
 return s;
}
inline void fill_map(uint8_t *out) { const uint8_t map[]={'''+map_data+'''}; for(unsigned i=0;i<4096;++i)out[i]=map[i]; }
struct Asset {uint16_t id;int w,h;const char *path;};
inline const Asset *asset(uint16_t id) {
 static const Asset all[]={'''+','.join('{%d,%d,%d,%s}'%(key,item['width'],item['height'],json.dumps(item['path']))for key,item in assets.items())+'''};
 for(const auto &value:all) { if(value.id==id) return &value; }
 return nullptr;
}
inline bool valid_buffer(uint16_t id){return asset(id)!=nullptr;}
inline uint32_t asset_bytes(uint16_t id){const auto a=asset(id);return a?uint32_t(a->w*a->h):0;}
inline void asset_dimensions(uint16_t id,int &w,int &h){const auto a=asset(id);if(!a)throw std::runtime_error("missing asset");w=a->w;h=a->h;}
inline void fill_asset(uint16_t id,uint8_t *out){const auto a=asset(id);if(!a)throw std::runtime_error("missing asset");std::ifstream f(a->path,std::ios::binary);f.read(reinterpret_cast<char *>(out),a->w*a->h);if(!f)throw std::runtime_error("asset read failed");}
static const uint16_t all_ids[]={'''+','.join(map(str,assets))+'''};
}
'''
    (out/'renderer_fixture.h').write_text(header)
    inputs=base/'inputs/module'
    for name in ('wolf3d_renderer.cpp','wolf3d_renderer.h','wolf3d_production_contract.h','wolf3d_world_mirror.cpp','wolf3d_world_mirror.h'):
        shutil.copyfile(inputs/name,out/name)
    shutil.copyfile(base/'inputs/wolf3d_tables.inc',out.parent/'wolf3d_tables.inc')
    oracle=(inputs/'renderer_oracle.cpp').read_text()
    start=oracle.index('    for (uint16_t id :');end=oracle.index('\n}\n\nWolf3dWorldState make_world',start)
    oracle=oracle[:start]+'''    for(uint16_t id:fixture::all_ids) buffers[id].push_back(texture(id));'''+oracle[end:]
    oracle=oracle.replace('i < 2;', 'i < fixture::kDoorCount;').replace('i < 3;', 'i < fixture::kStaticCount;')
    (out/'oracle.cpp').write_text(oracle)
    original=(inputs/'test_renderer.cpp').read_text();prefix=original[:original.index('void exercise_errors')]
    prefix=prefix.replace('constexpr size_t kCenterColumn = 128;','')
    prefix=prefix.replace('world.door_count = 2;','world.door_count = fixture::kDoorCount;').replace('world.static_count = 3;','world.static_count = fixture::kStaticCount;')
    prefix=prefix.replace('i < 2;', 'i < fixture::kDoorCount;').replace('i < 3;', 'i < fixture::kStaticCount;')
    main=original[original.index('int main('):]
    for line in ('        exercise_errors(map.data());\n','        exercise_capacity(map.data());\n','        exercise_pushwalls();\n'):main=main.replace(line,'')
    start=main.index('            require(stats.wall_acquires >= 2');end=main.index('            require(stats.weapon_acquires',start);main=main[:start]+main[end:]
    main=main.replace('            write_all(frame_output, workspace, W3P_FRAME_BYTES);','''            std::vector<uint8_t> expected(workspace,workspace+W3P_FRAME_BYTES);
            std::vector<uint8_t> geometry(workspace+W3P_WALL_HEIGHT_OFFSET,workspace+W3P_SPRITE_ARENA_OFFSET);
            std::vector<std::vector<uint8_t>> rows(240,std::vector<uint8_t>(328,0xa5));
            uintptr_t pointers[240];
            for(unsigned y=0;y<240;++y){pointers[y]=reinterpret_cast<uintptr_t>(rows[y].data()+4);for(unsigned x=0;x<320;++x)rows[y][4+x]=0x80;}
            RenderTarget target{nullptr,pointers,0,2,0x3f,0xc0};
            require(render_world_direct(world,supplied,target)==RenderDetail::ok,"canonical direct render failed");
            for(unsigned y=0;y<240;++y){
                for(unsigned x=0;x<320;++x){const uint8_t pixel=rows[y][4+(x^2)];require((pixel&0x3f)==expected[y*320+x],"direct/copy pixel mismatch");require((pixel&0xc0)==0x80,"sync bits changed");}
                for(unsigned i=0;i<4;++i)require(rows[y][i]==0xa5 && rows[y][324+i]==0xa5,"row guard changed");
            }
            require(!std::memcmp(geometry.data(),workspace+W3P_DIRECT_WALL_HEIGHT_OFFSET,geometry.size()),"direct/copy geometry mismatch");
            require(provider.active==0 && provider.acquired==provider.released,"direct asset leak");
            write_all(frame_output, expected.data(), expected.size());''')
    main=main.replace('workspace + W3P_WALL_HEIGHT_OFFSET,\n                      W3P_SPRITE_ARENA_OFFSET - W3P_WALL_HEIGHT_OFFSET','geometry.data(),geometry.size()')
    (out/'renderer.cpp').write_text(prefix+'} // namespace\n\n'+main)
    record={'schema':'wolf-perf003-canonical-parity-inputs-v1','angles':list(range(0,360,45)),'doors':level.door_count,'statics':level.static_count,'enemies':0,'agnb':sources,'assets':assets,'files':{p.name:sha(p)for p in out.iterdir()if p.is_file()}}
    (out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n');print(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revision',required=True);p.add_argument('--attempt',required=True);a=p.parse_args();prepare(a.revision,a.attempt)
