/* Headless-only SDL input/capture shim for agent rehearsal. Not guest code. */
#define _POSIX_C_SOURCE 200809L
#include <SDL3/SDL.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

bool SDL_PollEvent(SDL_Event *event) {
    static bool (*real_poll)(SDL_Event *);
    static FILE *commands;
    if (!real_poll) *(void **)(&real_poll) = dlsym(RTLD_NEXT, "SDL_PollEvent");
    if (!commands) {
        const char *name = getenv("W3V_REVIEW_EVENTS");
        if (name) commands = fopen(name, "r");
    }
    char line[1024];
    if (commands && event && fgets(line, sizeof line, commands)) {
        unsigned scan, down;
        if (sscanf(line, "key %u %u", &scan, &down) == 2) {
            memset(event, 0, sizeof *event);
            event->type = down ? SDL_EVENT_KEY_DOWN : SDL_EVENT_KEY_UP;
            event->key.scancode = (SDL_Scancode)scan;
            event->key.key = SDL_GetKeyFromScancode(
                (SDL_Scancode)scan, 0, false
            );
            event->key.down = down != 0;
            return true;
        }
        if (!strncmp(line, "capture ", 8)) {
            line[strcspn(line, "\r\n")] = 0;
            void *handle = dlopen(getenv("W3V_REVIEW_VDP"), RTLD_NOW | RTLD_NOLOAD);
            if (handle) {
                void (*copy)(uint32_t *, uint32_t *, uint8_t *, float *);
                *(void **)(&copy) = dlsym(handle, "copyVgaFramebuffer");
                if (copy) {
                    uint8_t *rgb = malloc(1024 * 768 * 3);
                    uint32_t width = 0, height = 0;
                    float rate = 0;
                    copy(&width, &height, rgb, &rate);
                    FILE *output = fopen(line + 8, "wb");
                    if (output) {
                        fprintf(output, "P6\n%u %u\n255\n", width, height);
                        fwrite(rgb, 3, (size_t)width * height, output);
                        fclose(output);
                    }
                    free(rgb);
                }
                dlclose(handle);
            }
        }
        if (!strncmp(line, "quit", 4)) {
            memset(event, 0, sizeof *event);
            event->type = SDL_EVENT_QUIT;
            return true;
        }
    }
    if (commands) clearerr(commands);
    return real_poll(event);
}
