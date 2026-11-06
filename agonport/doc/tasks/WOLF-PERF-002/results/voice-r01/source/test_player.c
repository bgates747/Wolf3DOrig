/* Exercise the actual C parser and playback/error path with bounded fake MOS. */
#include <assert.h>
#define main player_main
#include "../player/src/main.c"
#undef main
static uint8_t file[10000],sv[32];
static unsigned length,cursor,commands,writes;static uint32_t ticks,fault;
uint8_t mos_fopen(const char *p,uint8_t mode){(void)p;(void)mode;cursor=0;return 1;}
void mos_fclose(uint8_t f){(void)f;}
unsigned mos_fread(uint8_t f,char *out,unsigned n){(void)f;if(cursor==fault)return 0;if(n>length-cursor)n=length-cursor;memcpy(out,file+cursor,n);cursor+=n;return n;}
uint8_t mos_flseek(uint8_t f,uint32_t n){(void)f;if(n>length)return 1;cursor=n;return 0;}
uint32_t getsysvar_time(void){return ticks++;}
volatile uint8_t *mos_sysvars(void){return sv;}
uint8_t getsysvar_vdp_pflags(void){return sv[4];}
uint8_t getsysvar_audioChannel(void){return 0;}
uint8_t getsysvar_audioSuccess(void){return 1;}
uint8_t mos_clearvdpflags(uint8_t m){sv[4]&=~m;return 0;}
uint8_t mos_waitforvdpflags(uint8_t m){return (sv[4]&m)?0:1;}
void mos_puts(const char *p,unsigned n,uint8_t z){(void)z;commands++;if(n==3&&(uint8_t)p[2]==0x86)sv[4]|=0x10;else sv[4]|=8;}
static void ack(void){commands++;sv[4]|=8;}
void vdp_audio_enable_channel(int n){assert(n==0);ack();}
void vdp_audio_reset_channel(int n){assert(n==0);ack();}
void vdp_adv_clear_buffer(unsigned n){assert(n==SAMPLE_BUFFER);commands++;}
void vdp_adv_write_block_data(unsigned id,unsigned n,char *p){assert(id==SAMPLE_BUFFER&&n<=4096&&p);writes++;commands++;}
void vdp_adv_consolidate(unsigned n){assert(n==SAMPLE_BUFFER);commands++;}
void vdp_audio_set_sample(int ch,unsigned n){assert(ch==0&&n==SAMPLE_BUFFER);ack();}
void vdp_audio_play_sample(int ch,int v){assert(ch==0&&v==100);ack();}
static void put16(unsigned at,unsigned n){file[at]=n;file[at+1]=n>>8;}
static void put32(unsigned at,uint32_t n){for(unsigned i=0;i<4;i++)file[at+i]=n>>(8*i);}
static void valid(unsigned bytes){
 memset(file,0,sizeof(file));memset(sv,0,sizeof(sv));commands=writes=cursor=0;ticks=0;fault=UINT32_MAX;
 memcpy(file,"RIFF",4);memcpy(file+8,"WAVEfmt ",8);put32(16,16);put16(20,1);put16(22,1);put32(24,16000);put32(28,16000);put16(32,1);put16(34,8);memcpy(file+36,"data",4);put32(40,bytes);length=44+bytes+(bytes&1);put32(4,length-8);
}
static int run(void){char *args[]={"playwav","clip.wav"};return player_main(2,args);}
static void reject(void){assert(run()==3);assert(commands==0);}
int main(void){
 valid(400);assert(run()==0&&writes==1); /* successful leaf returns to caller */
 valid(400);length--;reject(); /* truncated declared RIFF */
 valid(400);put16(22,2);reject(); /* stereo */
 valid(400);put16(34,16);reject(); /* wrong bit depth */
 valid(400);put32(24,0);reject(); /* invalid rate */
 valid(400);put32(40,UINT32_MAX);reject(); /* wrapping chunk size */
 valid(401);assert(run()==0); /* odd data padding */
 valid(400);memmove(file+46,file+36,length-36);memcpy(file+36,"JUNK",4);put32(40,1);file[44]=7;file[45]=0;length+=10;put32(4,length-8);assert(run()==0); /* unknown odd chunk */
 valid(400);memcpy(file+length,"data",4);put32(length+4,1);file[length+8]=0;file[length+9]=0;length+=10;put32(4,length-8);reject(); /* duplicate data */
 valid(8200);fault=44+4096;assert(run()==5&&writes==1); /* no WRITE header for missing payload */
 puts("10 actual-player parser/transport checks passed");return 0;
}
