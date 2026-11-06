// Test the actual source function. Host arithmetic provider remains distinct
// from the target helper; package identity checks cover target code identity.
#include "wolf3d_renderer.cpp"
#include <iostream>

int main() {
    struct Case { int32_t a, b, expected; };
    const Case cases[] = {
        {0, 1, 0}, {1, 1, 65536}, {-1, 1, -65536},
        {1, -1, -65536}, {-1, -1, 65536},
        {1, 3, 21845}, {-1, 3, -21845}, {1, -3, -21845},
        {-32768, 65536, -32768}, {32768, 65536, 32768},
        {INT32_MIN, 65536, INT32_MIN}, {INT32_MAX, 65536, INT32_MAX},
        {INT32_MIN, INT32_MIN, 65536}, {INT32_MAX, INT32_MIN, -65535},
        {65536, 65536, 65536}, {-65536, 65536, -65536},
    };
    for (const auto &c : cases) {
        volatile int32_t a = c.a, b = c.b;
        if (wolf3d_production::fixed_div(a, b) != c.expected) {
            std::cerr << "defined fixed_div mismatch\n";
            return 1;
        }
    }
    std::cout << "PASS 16 actual-source signed/boundary fixed_div cases with defined scaling\n";
}
