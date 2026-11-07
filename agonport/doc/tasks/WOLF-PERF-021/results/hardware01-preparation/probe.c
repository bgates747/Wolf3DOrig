#include "/Agon/mystuff/agon-extender/agents/remote009/download-r01/source/projects/sdserve/src/service.c"

static unsigned crc_calls;
void __attribute__((no_instrument_function)) __cyg_profile_func_enter(void *f,void *caller) {
    (void)caller;if(f==(void *)sd_crc_update)++crc_calls;
}
void __attribute__((no_instrument_function)) __cyg_profile_func_exit(void *f,void *caller) {(void)f;(void)caller;}
unsigned __attribute__((no_instrument_function)) test_crc_calls(void) {return crc_calls;}
void __attribute__((no_instrument_function)) test_crc_reset(void) {crc_calls=0;}
