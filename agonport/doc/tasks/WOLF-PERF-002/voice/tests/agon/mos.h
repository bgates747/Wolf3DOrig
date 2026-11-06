#include <stdint.h>
#define FA_READ 1
#define sysvar_vdp_pflags 4
uint8_t mos_fopen(const char *,uint8_t);
void mos_fclose(uint8_t);
unsigned mos_fread(uint8_t,char *,unsigned);
uint8_t mos_flseek(uint8_t,uint32_t);
uint32_t getsysvar_time(void);
volatile uint8_t *mos_sysvars(void);
uint8_t getsysvar_vdp_pflags(void);
uint8_t getsysvar_audioChannel(void);
uint8_t getsysvar_audioSuccess(void);
uint8_t mos_clearvdpflags(uint8_t);
uint8_t mos_waitforvdpflags(uint8_t);
void mos_puts(const char *,unsigned,uint8_t);
