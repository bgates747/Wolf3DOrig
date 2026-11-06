#include <dlfcn.h>
#include <cstdio>
int main(int n,char**v){if(n!=2)return 2;void*h=dlopen(v[1],RTLD_NOW|RTLD_LOCAL);if(!h){std::fprintf(stderr,"%s\n",dlerror());return 3;}auto test=(int(*)())dlsym(h,"wolf_fab_bridge_selftest");if(!test)return 4;int rc=test();std::printf("Fab source bridge contract checks: %d failures\n",rc);dlclose(h);return rc?1:0;}
