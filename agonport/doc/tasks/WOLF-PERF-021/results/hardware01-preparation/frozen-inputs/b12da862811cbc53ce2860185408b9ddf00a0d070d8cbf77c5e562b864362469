/* Test-only filesystem adapter. This does not model FAT power-loss behavior. */
#ifndef SDSERVE_HOST_MOS_H
#define SDSERVE_HOST_MOS_H
#include <stdint.h>
#include <stdio.h>
#include <dirent.h>
typedef struct { FILE *file;uint8_t error; } FIL;
typedef struct { DIR *dir;char path[512]; } TEST_DIR;
#define DIR TEST_DIR
typedef struct { uint32_t fsize;uint8_t fattrib;char fname[256]; } FILINFO;
enum { FR_OK=0,FR_DISK_ERR=1,FR_NO_FILE=4,FR_NO_PATH=5,FR_DENIED=7,FR_EXIST=8 };
#define AM_DIR 16
#define FA_READ 1
#define FA_WRITE 2
#define FA_CREATE_NEW 4
uint8_t ffs_fopen(FIL *,const char *,uint8_t);
uint8_t ffs_fclose(FIL *);
unsigned ffs_fread(FIL *,char *,unsigned);
unsigned ffs_fwrite(FIL *,const char *,unsigned);
uint8_t ffs_ferror(FIL *);
uint8_t ffs_fsync(FIL *);
uint8_t ffs_fsize(FIL *,uint32_t *);
uint8_t ffs_flseek_p(FIL *,uint32_t *);
uint8_t ffs_dopen(DIR *,const char *);
uint8_t ffs_dclose(DIR *);
uint8_t ffs_dread(DIR *,FILINFO *);
uint8_t ffs_stat(FILINFO *,const char *);
uint8_t ffs_mkdir(const char *);
uint8_t ffs_unlink(const char *);
uint8_t ffs_rename(const char *,const char *);
#endif
