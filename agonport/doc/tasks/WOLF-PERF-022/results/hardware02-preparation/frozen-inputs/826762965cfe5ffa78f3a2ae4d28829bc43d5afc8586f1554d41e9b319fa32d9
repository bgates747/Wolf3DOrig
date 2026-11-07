/* Foreground service; caller owns transport and supplies bounded heartbeat. */
#ifndef SDSERVE_SERVICE_H
#define SDSERVE_SERVICE_H
#include "sd_wire.h"
int service_init(const char *root,uint32_t boot);
/* Configure at startup: fast-v2 performs no CRC or whole-file verification. */
int service_init_mode(const char *root,uint32_t boot,int fast);
unsigned service_request(const uint8_t *request,unsigned length,uint8_t *reply);
int service_exiting(void);
void service_stop(void);
void service_progress(void);
#endif
