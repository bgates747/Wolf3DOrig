// Actual setup_view versus retained original fine-angle quarter reconstruction.
#include "wolf3d_renderer.cpp"
#include "test_sine_reference.inc"
#include <iostream>
#include <stdexcept>
using namespace wolf3d_production;
namespace {
int32_t original_sine(int32_t angle) {
    angle%=3600;
    if(angle<0)angle+=3600;
    if(angle<=900)return kOriginalSinQuarter[angle];
    if(angle<=1800)return kOriginalSinQuarter[1800-angle];
    if(angle<=2700)return -kOriginalSinQuarter[angle-1800];
    return -kOriginalSinQuarter[3600-angle];
}
}
int main() {
    WorldMirror world{}; unsigned count=0;
    for(unsigned angle=0;angle<65536;++angle) {
        world.player.angle=static_cast<uint16_t>(angle);
        const int32_t sine=original_sine(static_cast<int32_t>(angle)*10);
        const int32_t cosine=original_sine(static_cast<int32_t>(angle)*10+900);
        for(int32_t position : {int32_t(0),int32_t(34*65536+32768),int32_t(-65536),int32_t(1<<25)}) {
            world.player.x=position;world.player.y=-position;
            auto view=setup_view(world);
            const int32_t x=position-static_cast<int32_t>((int64_t(kFocalLength)*cosine)>>16);
            const int32_t y=-position+static_cast<int32_t>((int64_t(kFocalLength)*sine)>>16);
            if(view.sine!=sine || view.cosine!=cosine || view.x!=x || view.y!=y)
                throw std::runtime_error("whole uint16 setup domain differs from original fine-angle projection");
            ++count;
        }
    }
    std::cout<<"PASS "<<count<<" actual setup views, all65536 uint16 angles/4 positions, original quarter oracle and exact focal signs/rounding\n";
}
