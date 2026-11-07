/* PORT-017 foreground file engine. Uses public MOS/FatFS calls, never UART.
 * WRITE acknowledges the checked open-file write; FINISH syncs/closes and
 * independently reads the stage by default. Fast-v2 performs no CRC work:
 * packet/descriptor fields are reserved zero; SDT2 metadata has no checksum.
 * Framing, offsets/counts and filesystem errors remain checked. Old SDT1
 * metadata requires the checked mode; fast recovery never evaluates its CRC.
 * FAT rename is recoverable, NOT power-atomic.
 * Wire contract: agon-extender/docs/protocols/mainboard-sd.md.
 */
#include <agon/mos.h>
#include <string.h>
#include "service.h"

static char root[121],target[121],part[130],meta[130],backup[130];
static uint32_t boot_id,session,sequence,transfer,expected_size,expected_crc,offset;
static uint8_t active,finished,exiting,fast_mode;
static FIL stage;
/* R05-12: only foreground fast READs share this handle. Non-READ operations
 * close it before metadata/mutations; external concurrent file mutation is not
 * supported. This removes per-record filesystem setup without a wire change. */
static FIL reader;
static char reader_path[121];
static uint32_t reader_size,reader_at;
static uint8_t reader_open;
static uint8_t previous[SD_MAX_RECORD],cached[SD_MAX_RECORD];
static unsigned previous_size,cached_size;
static uint8_t scratch[256],fs_error;
/* A07: one bounded rename descriptor; no recursion or new resident ROM code.
 * Final fragment alone executes ffs_rename. Replay is handled by the existing
 * exact-request cache; interruption never turns into a delayed rename. */
static uint8_t move_descriptor[248];
static unsigned move_total,move_at;
static uint32_t move_crc;
static int folded_equal(const char *a,const char *b,size_t n) {
    while(n--) { unsigned char x=*a++,y=*b++;
        if(x>='A'&&x<='Z')x+=32;
        if(y>='A'&&y<='Z')y+=32;
        if(x!=y)return 0;
    }return 1;
}

static int fail(uint8_t error) { fs_error=error;return SD_FILE_ERROR; }
static int path_ok(const char *p) {
    size_t n=strlen(p),rn=strlen(root),i,start=1;
    if(!n || n>120 || p[0]!='/' || (n>1 && p[n-1]=='/')) return 0;
    if(rn>1 && (n<rn || !folded_equal(p,root,rn) || (p[rn] && p[rn]!='/'))) return 0;
    for(i=1;i<=n;++i) {
        unsigned char c=p[i];
        if(c && (c<32 || c>126 || c==':' || c=='\\' || c=='*' || c=='?')) return 0;
        if(c=='/' || !c) {
            size_t len=i-start;
            if(!len && n!=1) return 0;
            if((len==1 && p[start]=='.') || (len==2 && !memcmp(p+start,"..",2))) return 0;
            if(len && (p[i-1]=='.' || p[i-1]==' ')) return 0;
            start=i+1;
        }
    }
    return 1;
}
static int path_read(const uint8_t *p,unsigned n,char *out) {
    if(n<2 || p[0]>120 || n!=(unsigned)p[0]+1 || memchr(p+1,0,p[0])) return 0;
    memcpy(out,p+1,p[0]);out[p[0]]=0;return path_ok(out);
}
static int siblings(const char *path) {
    size_t n=strlen(path);
    if(n>112) return 0; /* Sibling names must still fit the 120-byte READ path. */
    // Reserve journal siblings, including case-insensitive FAT aliases.
    char lower[121];size_t i;
    for(i=0;i<=n;++i) lower[i]=(path[i]>='A'&&path[i]<='Z')?path[i]+32:path[i];
    if(!strcmp(strrchr(lower,'/')+1,"sdserve.bin")) return 0;
    if(!strcmp(path,"/") || strstr(lower,".p17part") || strstr(lower,".p17meta") ||
       strstr(lower,".p17bak")) return 0;
    strcpy(target,path);strcpy(part,path);strcat(part,".p17part");
    strcpy(meta,path);strcat(meta,".p17meta");strcpy(backup,path);strcat(backup,".p17bak");
    return 1;
}
/* Root and live utility/journal protection applies to NEW mutations only;
 * READ/RECOVER retain their existing ability to inspect recovery artifacts. */
static int mutable_path(const char *p) {
    char lower[121];size_t i,n=strlen(p),rn=strlen(root);
    if(!path_ok(p) || n==1 || (n==rn && folded_equal(p,root,n)))return 0;
    for(i=0;i<=n;++i)lower[i]=(p[i]>='A'&&p[i]<='Z')?p[i]+32:p[i];
    if(strstr(lower,".p17part") || strstr(lower,".p17meta") || strstr(lower,".p17bak") ||
       !strcmp(strrchr(lower,'/')+1,"sdserve.bin"))return 0;
    if(!strcmp(lower,"/emos") || !strcmp(lower,"/extender"))return 0;
    return 1;
}
static int related(const char *a,const char *b) {
    size_t an=strlen(a),bn=strlen(b),n=an<bn?an:bn;
    return folded_equal(a,b,n) && (an==bn || (an<bn?b[n]:a[n])=='/');
}
static int exists(const char *path,FILINFO *info) {
    uint8_t r=ffs_stat(info,path);
    if(r==FR_NO_FILE || r==FR_NO_PATH) return 0;
    if(r) { fs_error=r;return -1; } return 1;
}
static int close_file(FIL *f,int status) {
    uint8_t r=ffs_fclose(f);return status?status:(r?fail(r):SD_OK);
}
static int reader_close(int status) {
    if(!reader_open)return status;
    reader_open=0;return close_file(&reader,status);
}
static int fast_read(const char *path,uint32_t at,unsigned count,uint8_t *out,unsigned *out_n) {
    uint8_t r;unsigned actual;int result;
    if(!reader_open || strcmp(path,reader_path)) {
        result=reader_close(SD_OK);if(result)return result;
        r=ffs_fopen(&reader,path,FA_READ);if(r)return fail(r);
        reader_open=1;strcpy(reader_path,path);reader_at=0;
        r=ffs_fsize(&reader,&reader_size);if(r)return reader_close(fail(r));
    }
    if(at>reader_size)return reader_close(SD_BAD_REQUEST);
    if(at!=reader_at && (r=ffs_flseek_p(&reader,&at)))return reader_close(fail(r));
    actual=ffs_fread(&reader,(char *)out+4,count);r=ffs_ferror(&reader);
    if(r)return reader_close(fail(r));
    if(actual!=(reader_size-at<count?reader_size-at:count))return reader_close(fail(FR_DISK_ERR));
    reader_at=at+actual;
    if(reader_at==reader_size && (result=reader_close(SD_OK)))return result;
    sd_put32(out,reader_size);*out_n=4+actual;return SD_OK;
}
static int read_exact(FIL *f,uint8_t *p,unsigned n) {
    unsigned got=ffs_fread(f,(char *)p,n);
    uint8_t r=ffs_ferror(f);
    return r?fail(r):got!=n?fail(FR_DISK_ERR):SD_OK;
}
static int write_exact(FIL *f,const uint8_t *p,unsigned n) {
    unsigned got=ffs_fwrite(f,(const char *)p,n);
    uint8_t r=ffs_ferror(f);
    return r?fail(r):got!=n?fail(FR_DENIED):SD_OK;
}
static int digest(const char *path,uint32_t *size,uint32_t *crc) {
    FIL f;uint8_t r=ffs_fopen(&f,path,FA_READ);int result=SD_OK;
    uint32_t length=0,c=UINT32_C(0xffffffff);
    if(r) return fail(r);
    while(!result) {
        unsigned n=ffs_fread(&f,(char *)scratch,sizeof(scratch));
        r=ffs_ferror(&f);
        if(r) { result=fail(r);break; }
        if(UINT32_MAX-length<n) { result=SD_INTEGRITY;break; }
        length+=n;c=sd_crc_update(c,scratch,n);service_progress();
        if(n<sizeof(scratch)) break;
    }
    result=close_file(&f,result);
    if(!result) { *size=length;*crc=c^UINT32_C(0xffffffff); } return result;
}
static int checked_digest(const char *path,uint32_t length,uint32_t crc) {
    uint32_t actual,hash;int r=digest(path,&actual,&hash);
    return r?r:(actual!=length || hash!=crc)?SD_INTEGRITY:SD_OK;
}
static int size_matches(const char *path,uint32_t size) {
    FILINFO info;uint8_t r=ffs_stat(&info,path);
    return r?fail(r):(info.fattrib&AM_DIR || info.fsize!=size)?SD_INTEGRITY:SD_OK;
}
static int readable(const char *path) {
    FIL f;uint32_t size;unsigned got;uint8_t r=ffs_fopen(&f,path,FA_READ);int result;
    if(r)return fail(r);
    /* Explicit fast backup cleanup checks accessibility, not the whole file. */
    r=ffs_fsize(&f,&size);if(r)return close_file(&f,fail(r));
    got=ffs_fread(&f,(char *)scratch,1);r=ffs_ferror(&f);
    result=r?fail(r):got!=(size?1U:0U)?fail(FR_DISK_ERR):SD_OK;
    return close_file(&f,result);
}
static int state(uint8_t *bits,uint8_t *metadata) {
    const char *paths[4]={target,part,meta,backup};FILINFO info;unsigned i;
    *bits=0;
    for(i=0;i<4;++i) {
        int yes=exists(paths[i],&info);if(yes<0) return SD_FILE_ERROR;
        if(yes) { if(info.fattrib&AM_DIR) return SD_RECOVERY_REQUIRED;*bits|=1<<i; }
    }
    if(*bits&4) {
        FIL f;uint8_t r=ffs_fopen(&f,meta,FA_READ);uint32_t size=0;int result;
        if(r) return fail(r);
        r=ffs_fsize(&f,&size);
        result=r?fail(r):size!=20?SD_INTEGRITY:read_exact(&f,metadata,20);
        result=close_file(&f,result);
        if(result || !sd_u32(metadata+4)) *bits|=16;
        else if(fast_mode) {
            if(memcmp(metadata,"SDT2",4) || sd_u32(metadata+12) || sd_u32(metadata+16)) *bits|=16;
        } else if(memcmp(metadata,"SDT1",4) ||
                  sd_u32(metadata+16)!=sd_crc(metadata,16)) *bits|=16;
    }
    return SD_OK;
}
static int remove_if_present(const char *p) {
    uint8_t r=ffs_unlink(p);return (r==FR_NO_FILE || r==FR_NO_PATH)?SD_OK:r?fail(r):SD_OK;
}
static int handle(uint8_t op,const uint8_t *p,unsigned n,uint8_t *out,unsigned *out_n) {
    char path[121];FILINFO info;uint8_t r,bits,metadata[20];int result;uint32_t tid;
    *out_n=0;
    if(op!=SD_READ && (result=reader_close(SD_OK)))return result;
    if(op!=SD_MOVE)move_total=move_at=0;
    switch(op) {
    case SD_HELLO:
        if(n) return SD_BAD_REQUEST;
        sd_put32(out,boot_id);sd_put16(out+4,212);sd_put16(out+6,15 | 32 | (fast_mode?16|64:0));*out_n=8;return SD_OK;
    case SD_STAT: {
        if(!path_read(p,n,path)) return SD_BAD_REQUEST;
        /* Stock MOS 3.0.2 FatFS f_stat rejects the origin directory with
         * FR_INVALID_NAME. Validate root with the directory API instead;
         * do not fabricate success when media is absent or inaccessible. */
        if(!strcmp(path,"/")) {
            DIR dir;
            r=ffs_dopen(&dir,path);if(r) return fail(r);
            r=ffs_dclose(&dir);if(r) return fail(r);
            sd_put32(out,0);out[4]=AM_DIR;*out_n=5;return SD_OK;
        }
        r=ffs_stat(&info,path);if(r) return fail(r);
        sd_put32(out,info.fsize);out[4]=info.fattrib;*out_n=5;return SD_OK;
    }
    case SD_READ: {
        FIL f;uint32_t size;unsigned count,actual;uint32_t at;
        if(n<8 || (count=sd_u16(p+4))>216 || !path_read(p+6,n-6,path)) return reader_close(SD_BAD_REQUEST);
        at=sd_u32(p);if(fast_mode)return fast_read(path,at,count,out,out_n);
        r=ffs_fopen(&f,path,FA_READ);if(r) return fail(r);
        r=ffs_fsize(&f,&size);result=r?fail(r):at>size?SD_BAD_REQUEST:SD_OK;
        if(!result && (r=ffs_flseek_p(&f,&at))) result=fail(r);
        actual=0;
        if(!result) {
            actual=ffs_fread(&f,(char *)out+4,count);r=ffs_ferror(&f);
            if(r) result=fail(r);
            else if(actual!=(size-at<count?size-at:count)) result=fail(FR_DISK_ERR);
        }
        result=close_file(&f,result);
        if(!result) { sd_put32(out,size);*out_n=4+actual; }return result;
    }
    case SD_LIST: {
        DIR dir;uint32_t cursor,i=0;
        if(n<6 || !path_read(p+4,n-4,path)) return SD_BAD_REQUEST;
        cursor=sd_u32(p);if(cursor>65535) return SD_BAD_REQUEST;
        r=ffs_dopen(&dir,path);if(r) return fail(r);
        do { r=ffs_dread(&dir,&info);service_progress(); }
        while(!r && info.fname[0] && i++<cursor);
        result=r?fail(r):SD_OK;r=ffs_dclose(&dir);if(!result && r) result=fail(r);
        if(result) return result;
        sd_put32(out,info.fname[0]?cursor+1:cursor);out[4]=info.fname[0]?0:1;*out_n=5;
        if(info.fname[0]) {
            size_t len=strlen(info.fname);if(len>209) return SD_BAD_REQUEST;
            out[5]=info.fattrib;sd_put32(out+6,info.fsize);out[10]=len;
            memcpy(out+11,info.fname,len);*out_n=11+len;
        }return SD_OK;
    }
    case SD_BEGIN: {
        FIL journal;
        if(active) return SD_BUSY;
        if(n<14 || !(tid=sd_u32(p)) || !path_read(p+12,n-12,path) || !siblings(path)) return SD_BAD_REQUEST;
        if(fast_mode && sd_u32(p+8))return SD_BAD_REQUEST;
        result=state(&bits,metadata);if(result) return result;
        if(bits&14) return SD_RECOVERY_REQUIRED;
        memcpy(metadata,fast_mode?"SDT2":"SDT1",4);memcpy(metadata+4,p,12);
        sd_put32(metadata+16,fast_mode?0:sd_crc(metadata,16));
        r=ffs_fopen(&journal,meta,FA_WRITE|FA_CREATE_NEW);if(r) return fail(r);
        result=write_exact(&journal,metadata,20);
        if(!result && (r=ffs_fsync(&journal))) result=fail(r);
        result=close_file(&journal,result);if(result) return result;
        r=ffs_fopen(&stage,part,FA_WRITE|FA_CREATE_NEW);if(r) return fail(r);
        transfer=tid;expected_size=sd_u32(p+4);expected_crc=sd_u32(p+8);
        offset=0;active=1;finished=0;
        sd_put32(out,transfer);sd_put32(out+4,offset);*out_n=8;return SD_OK;
    }
    case SD_WRITE:
        if(n<9 || n>220) return SD_BAD_REQUEST;
        if(!active || finished || sd_u32(p)!=transfer) return SD_BAD_REQUEST;
        if(sd_u32(p+4)!=offset || n-8>expected_size-offset) return SD_BAD_REQUEST;
        result=write_exact(&stage,p+8,n-8);
        if(result) { (void)close_file(&stage,result);active=0;return result; }
        offset+=n-8;sd_put32(out,transfer);sd_put32(out+4,offset);*out_n=8;return SD_OK;
    case SD_FINISH:
        if(n!=4) return SD_BAD_REQUEST;
        if(!active || sd_u32(p)!=transfer) return SD_BAD_REQUEST;
        if(offset!=expected_size) return SD_INTEGRITY;
        if(!finished) {
            r=ffs_fsync(&stage);result=close_file(&stage,r?fail(r):SD_OK);
            active=0;if(result) return result;
            if(!fast_mode) { result=checked_digest(part,expected_size,expected_crc);if(result) return result; }
            active=1;finished=1;
        }
        /* Fast mode returns the declared size and a reserved zero field.
         * HELLO bits0x10/0x40 distinguish it from the old CRC-bearing fast path. */
        sd_put32(out,expected_size);sd_put32(out+4,expected_crc);*out_n=8;return SD_OK;
    case SD_ACTIVATE:
        if(n!=4) return SD_BAD_REQUEST;
        if(!active || !finished || sd_u32(p)!=transfer) return SD_BAD_REQUEST;
        active=0;finished=0;
        result=state(&bits,metadata);if(result) return result;
        if((bits&30)!=6) return SD_RECOVERY_REQUIRED;
        if(bits&1) { r=ffs_rename(target,backup);if(r) return fail(r); }
        r=ffs_rename(part,target);if(r) return fail(r);
        if(!fast_mode) { result=checked_digest(target,expected_size,expected_crc);if(result) return result; }
        r=ffs_unlink(meta);return r?fail(r):SD_OK;
    case SD_CANCEL:
        if(n!=4) return SD_BAD_REQUEST;
        if(!active || sd_u32(p)!=transfer) return SD_BAD_REQUEST;
        result=finished?SD_OK:close_file(&stage,SD_OK);active=finished=0;
        if(result) return result;
        result=remove_if_present(part);return result?result:remove_if_present(meta);
    case SD_RECOVER:
        if(active) return SD_BUSY;
        if(n<3 || p[0]>3 || !path_read(p+1,n-1,path) || !siblings(path)) return SD_BAD_REQUEST;
        result=state(&bits,metadata);if(result) return result;
        if(p[0] && (bits&16)) return SD_RECOVERY_REQUIRED;
        if(p[0]==1) {
            if((bits&9)!=8) return SD_RECOVERY_REQUIRED;
            r=ffs_rename(backup,target);if(r) return fail(r);
        } else if(p[0]==2) {
            if(!(bits&1) && ((bits&8) || !(bits&4))) return SD_RECOVERY_REQUIRED;
            // Metadata without a part may mean the new file was activated.
            if((bits&7)==5) {
                result=fast_mode?size_matches(target,sd_u32(metadata+8)):
                    checked_digest(target,sd_u32(metadata+8),sd_u32(metadata+12));
                if(result) return result;
            }
            result=remove_if_present(part);if(result) return result;
            result=remove_if_present(meta);if(result) return result;
        } else if(p[0]==3) {
            uint32_t size,crc;
            if(!(bits&1) || (bits&6)) return SD_RECOVERY_REQUIRED;
            result=fast_mode?readable(target):digest(target,&size,&crc);if(result) return result;
            result=remove_if_present(backup);if(result) return result;
        }
        result=state(&bits,metadata);if(!result) { out[0]=bits;*out_n=1; }return result;
    case SD_MKDIR:
        if(active)return SD_BUSY;
        if(!path_read(p,n,path) || !mutable_path(path))return SD_BAD_REQUEST;
        r=ffs_mkdir(path);return r?fail(r):SD_OK;
    case SD_REMOVE:
        if(active)return SD_BUSY;
        if(n<3 || p[0]>1 || !path_read(p+1,n-1,path) || !mutable_path(path))return SD_BAD_REQUEST;
        if(p[0])return SD_OK; /* Guard-only preflight before recursive host deletion. */
        r=ffs_unlink(path);return r?fail(r):SD_OK;
    case SD_MOVE: {
        unsigned total,at,count,a,b;uint32_t crc;char destination[121];
        if(active)return SD_BUSY;
        if(n<9 || n>192){move_total=move_at=0;return SD_BAD_REQUEST;}
        total=sd_u16(p);at=sd_u16(p+2);crc=sd_u32(p+4);count=n-8;
        if(fast_mode && crc){move_total=move_at=0;return SD_BAD_REQUEST;}
        if(!at){move_total=move_at=0;move_crc=crc;if(total>=10 && total<=248)move_total=total;}
        if(!move_total || total!=move_total || at!=move_at || crc!=move_crc || count>total-at) {
            move_total=move_at=0;return SD_BAD_REQUEST;
        }
        memcpy(move_descriptor+at,p+8,count);move_at+=count;
        sd_put16(out,move_at);out[2]=move_at==move_total;*out_n=3;
        if(move_at<move_total)return SD_OK;
        move_total=move_at=0;
        if(!fast_mode && sd_crc(move_descriptor,total)!=crc)return SD_INTEGRITY;
        a=sd_u16(move_descriptor+2);b=sd_u16(move_descriptor+4);
        if(move_descriptor[0]!=6 || move_descriptor[1] || move_descriptor[6] || move_descriptor[7] ||
           a>120 || b>120 || 8+a+b!=total || memchr(move_descriptor+8,0,a+b))return SD_BAD_REQUEST;
        memcpy(path,move_descriptor+8,a);path[a]=0;
        memcpy(destination,move_descriptor+8+a,b);destination[b]=0;
        if(!mutable_path(path) || !mutable_path(destination) || related(path,destination))return SD_BAD_REQUEST;
        result=exists(destination,&info);if(result<0)return SD_FILE_ERROR;
        if(result)return fail(FR_EXIST);
        r=ffs_rename(path,destination);return r?fail(r):SD_OK;
    }
    case SD_EXIT:
        if(n) return SD_BAD_REQUEST;
        if(active) return SD_BUSY;
        exiting=1;return SD_OK;
    default:return SD_UNSUPPORTED;
    }
}

int service_init_mode(const char *scope,uint32_t boot,int fast) {
    if(strlen(scope)>120) return 0;
    strcpy(root,"/");if(!path_ok(scope)) return 0;
    if(reader_close(SD_OK))return 0;
    strcpy(root,scope);boot_id=boot?boot:1;session=sequence=0;
    move_total=move_at=0;active=finished=exiting=0;fast_mode=fast!=0;previous_size=cached_size=0;return 1;
}
int service_init(const char *scope,uint32_t boot) { return service_init_mode(scope,boot,0); }
unsigned service_request(const uint8_t *in,unsigned n,uint8_t *out) {
    uint32_t sid,seq;unsigned payload=0;int status;
    if(n<SD_HEADER || in[2]!=(fast_mode?SD_FAST_VERSION:SD_CHECKED_VERSION) ||
       !sd_valid(in,n) || in[3]!=SD_REQUEST || in[13] || !(seq=sd_u32(in+8))) return 0;
    sid=sd_u32(in+4);
    if(sid==session && seq==sequence) {
        if(n==previous_size && !memcmp(in,previous,n)) { memcpy(out,cached,cached_size);return cached_size; }
        status=SD_SEQUENCE;
    } else if(sid!=session && (in[12]!=SD_HELLO || seq!=1)) status=SD_STALE;
    else if(sid!=session && active) status=SD_BUSY;
    else if(sid==session && (sequence==UINT32_MAX || seq!=sequence+1)) status=SD_SEQUENCE;
    else {
        fs_error=0;status=handle(in[12],in+SD_HEADER,n-SD_HEADER,out+SD_HEADER,&payload);
        if(status) { payload=0;if(status==SD_FILE_ERROR) { out[SD_HEADER]=fs_error;payload=1; } }
        sd_header_mode(out,SD_RESPONSE,sid,seq,in[12],status,payload,fast_mode);sd_seal(out);
        session=sid;sequence=seq;previous_size=n;memcpy(previous,in,n);
        cached_size=SD_HEADER+payload;memcpy(cached,out,cached_size);return cached_size;
    }
    sd_header_mode(out,SD_RESPONSE,sid,seq,in[12],status,0,fast_mode);sd_seal(out);return SD_HEADER;
}
int service_exiting(void) { return exiting; }
void service_stop(void) {
    (void)reader_close(SD_OK);
    if(active && !finished) (void)ffs_fclose(&stage);
    // Preserve an interrupted transfer and journal for explicit recovery.
    active=finished=0;move_total=move_at=0;
}
