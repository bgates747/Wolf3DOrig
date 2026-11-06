/* Audio-only MOS utility, adapted from Extender network-hello's bounded
 * player and the AgonJukebox unsigned PCM contract. No BASIC or screen demo.
 * Caller owns channel0 and buffer0xf100; run only from a known-safe MOS CLI.
 */
#include <agon/mos.h>
#include <agon/vdp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SAMPLE_BUFFER 0xf100
#define MAX_RIFF_BYTES 300000UL
#define MAX_SECONDS 15UL
static uint8_t block[4096];
struct Sample { uint32_t offset, bytes; uint16_t rate; };
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 |
           (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static uint16_t le16(const uint8_t *p) { return p[0] | (uint16_t)p[1]<<8; }
static int read_exact(uint8_t f, unsigned n) { return mos_fread(f,(char *)block,n)==n; }
/* Validate the entire declared RIFF before emitting any audio/buffer command.
 * Unknown chunks and odd-sized padding are admitted, duplicate fmt/data are not.
 */
static int parse_wav(uint8_t f, struct Sample *out) {
    uint32_t offset=12,end,size; int format=0,data=0;
    if (!read_exact(f,12) || memcmp(block,"RIFF",4) || memcmp(block+8,"WAVE",4)) return 0;
    size=le32(block+4);
    if (size<36 || size>MAX_RIFF_BYTES-8) return 0;
    end=size+8;
    if (mos_flseek(f,end-1) || !read_exact(f,1)) return 0;
    while (offset<end) {
        if (end-offset<8 || mos_flseek(f,offset) || !read_exact(f,8)) return 0;
        size=le32(block+4);offset+=8;
        if (size>end-offset || (size&1)>end-offset-size) return 0;
        if (!memcmp(block,"fmt ",4)) {
            uint32_t rate;
            if (format || size<16 || !read_exact(f,16)) return 0;
            rate=le32(block+4);
            if (le16(block)!=1 || le16(block+2)!=1 || !rate || rate>65535 ||
                le32(block+8)!=rate || le16(block+12)!=1 || le16(block+14)!=8) return 0;
            out->rate=(uint16_t)rate;format=1;
        } else if (!memcmp(block,"data",4)) {
            if (!format || data || !size || size>(uint32_t)out->rate*MAX_SECONDS) return 0;
            out->offset=offset;out->bytes=size;data=1;
        }
        offset+=size+(size&1);
    }
    return format && data;
}
static void wait_ticks(uint32_t ticks) {
    uint32_t start=getsysvar_time();
    while ((uint32_t)(getsysvar_time()-start)<ticks) {}
}
static void audio_begin(void) { mos_sysvars()[sysvar_vdp_pflags]&=(uint8_t)~0x08; }
static int audio_ok(void) {
    uint32_t start=getsysvar_time();
    while (!(getsysvar_vdp_pflags()&0x08))
        if ((uint32_t)(getsysvar_time()-start)>=240) return 0;
    return getsysvar_audioChannel()==0 && getsysvar_audioSuccess()==1;
}
static int ingress_fence(void) {
    static const uint8_t mode_query[]={23,0,0x86};
    mos_clearvdpflags(0x10);
    mos_puts((const char *)mode_query,sizeof(mode_query),0);
    return mos_waitforvdpflags(0x10)==0;
}
static int cleanup(void) {
    int ok;
    audio_begin();vdp_audio_reset_channel(0);ok=audio_ok();
    vdp_adv_clear_buffer(SAMPLE_BUFFER);
    return ingress_fence() && ok;
}
static int play(uint8_t f,const struct Sample *s) {
    uint32_t remaining=s->bytes;
    const uint8_t create[]={23,0,0x85,0,5,2,SAMPLE_BUFFER&255,SAMPLE_BUFFER>>8,
                            1|8,s->rate&255,s->rate>>8};
    if (mos_flseek(f,s->offset)) return 5;
    /* Enable first so reset is valid even if the caller disabled channel0. */
    audio_begin();vdp_audio_enable_channel(0);if (!audio_ok()) return 4;
    audio_begin();vdp_audio_reset_channel(0);if (!audio_ok()) return 4;
    vdp_adv_clear_buffer(SAMPLE_BUFFER);
    while (remaining) {
        unsigned n=remaining>sizeof(block)?sizeof(block):(unsigned)remaining;
        /* Never emit a declared WRITE length until that payload is in RAM. */
        if (!read_exact(f,n)) return 5;
        vdp_adv_write_block_data(SAMPLE_BUFFER,n,(char *)block);remaining-=n;
    }
    /* Sample playback supports these blocks directly; no full-sample copy. */
    audio_begin();mos_puts((const char *)create,sizeof(create),0);if (!audio_ok()) return 4;
    audio_begin();vdp_audio_set_sample(0,SAMPLE_BUFFER);if (!audio_ok()) return 4;
    audio_begin();vdp_audio_play_sample(0,100);if (!audio_ok()) return 4;
    puts("PLAYWAV PLAY OK");
    wait_ticks((s->bytes*120UL+s->rate-1)/s->rate+60);
    return 0;
}
int main(int argc,char **argv) {
    struct Sample sample={0,0,0};uint8_t f;int result,cleanup_ok;
    if (argc!=2) { puts("Usage: playwav <mono-u8-PCM.wav> (maximum15seconds)");return 2; }
    f=mos_fopen(argv[1],FA_READ);
    if (!f) { puts("PLAYWAV ERROR open");return 3; }
    if (!parse_wav(f,&sample)) { mos_fclose(f);puts("PLAYWAV ERROR format; audio untouched");return 3; }
    result=play(f,&sample);mos_fclose(f);
    cleanup_ok=cleanup();
    if (!cleanup_ok) {
        puts("PLAYWAV CLEANUP UNCONFIRMED");
        if (!result) result=6;
    }
    if (result) printf("PLAYWAV ERROR stage=%d cleanup=%s\r\n",result,
                       cleanup_ok?"ok":"unconfirmed");
    else printf("PLAYWAV OK bytes=%lu rate=%u\r\n",(unsigned long)sample.bytes,(unsigned)sample.rate);
    return result;
}
