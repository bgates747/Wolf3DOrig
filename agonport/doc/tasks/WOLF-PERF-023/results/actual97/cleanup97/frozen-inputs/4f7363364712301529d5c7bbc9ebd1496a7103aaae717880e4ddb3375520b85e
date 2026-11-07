#ifndef AGON_VDP_AUDIO_QUEUE_PROTOCOL_H
#define AGON_VDP_AUDIO_QUEUE_PROTOCOL_H
#include <stdint.h>
/* Audio command 15. Integers in operation payloads are little-endian.
   This protocol does not depend on the native module loader. */
#define AUDIOQ_COMMAND 15u
#define AUDIOQ_VERSION 1u
#define AUDIOQ_CHANNELS 32u
#define AUDIOQ_GROUP 255u
#define AUDIOQ_DISCOVER 0u
#define AUDIOQ_OPEN 1u
#define AUDIOQ_STREAM_CREATE 2u
#define AUDIOQ_APPEND 3u
#define AUDIOQ_END 4u
#define AUDIOQ_SAMPLE 5u
#define AUDIOQ_STREAM 6u
#define AUDIOQ_TONE 7u
#define AUDIOQ_SILENCE 8u
#define AUDIOQ_CONTROL 9u
#define AUDIOQ_QUERY 10u
#define AUDIOQ_START 0u
#define AUDIOQ_PAUSE 1u
#define AUDIOQ_MUTE 2u
#define AUDIOQ_UNMUTE 3u
#define AUDIOQ_RESET 4u
#define AUDIOQ_CLOSE 5u
#define AUDIOQ_OK 0u
#define AUDIOQ_ARGUMENT 1u
#define AUDIOQ_UNSUPPORTED 2u
#define AUDIOQ_NOT_OPEN 3u
#define AUDIOQ_FULL 4u
#define AUDIOQ_MEMORY 5u
#define AUDIOQ_BUFFER 6u
#define AUDIOQ_BUSY 7u
#define AUDIOQ_ENDED 8u
#define AUDIOQ_LIMIT 9u
#define AUDIOQ_ACK 1u
#define AUDIOQ_REPLY 2u
/* Query flags: open, running, muted, playing, waiting for initial prime. */
#define AUDIOQ_FLAG_OPEN 1u
#define AUDIOQ_FLAG_RUNNING 2u
#define AUDIOQ_FLAG_MUTED 4u
#define AUDIOQ_FLAG_PLAYING 8u
#define AUDIOQ_FLAG_PRIMING 16u
/* Stream query 22 flags: EOS, initially primed. */
#define AUDIOQ_STREAM_EOS 1u
#define AUDIOQ_STREAM_PRIMED 2u
#endif
