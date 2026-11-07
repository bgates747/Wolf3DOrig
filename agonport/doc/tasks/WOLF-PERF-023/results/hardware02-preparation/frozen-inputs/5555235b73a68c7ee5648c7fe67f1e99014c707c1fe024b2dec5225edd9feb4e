#ifndef AGON_VDP_PCM_SINK_WIRE_H
#define AGON_VDP_PCM_SINK_WIRE_H
/* Optional ordinary audio protocol1. Bytes are explicitly serialized LE;
 * these constants do not introduce a packed C structure or native ABI change.
 * Discover VDPL safely, then INFO25==1, before sending audio16 operands. */
#define PCM_WIRE_VERSION 1u
#define PCM_WIRE_AUDIO_OPERATION 16u
#define PCM_WIRE_INFO_FIELD 25u
#define PCM_WIRE_HEADER_BYTES 15u
#define PCM_WIRE_PAYLOAD_MAX 8u
#define PCM_WIRE_REQUEST_MAX 23u
#define PCM_WIRE_PACKET_BODY_BYTES 14u
#define PCM_WIRE_STATE_BYTES 32u
#define PCM_WIRE_STATE_FRAGMENTS 4u
#define PCM_WIRE_FRAGMENT_BYTES 8u
#define PCM_WIRE_STATE_UART_BYTES 64u
#define PCM_WIRE_ACK_UART_BYTES 16u
/* Header offsets include VDU23,0,133,channel,audio-op. */
#define PCM_WIRE_REQUEST_CHANNEL 3u
#define PCM_WIRE_REQUEST_VERSION 5u
#define PCM_WIRE_REQUEST_OPERATION 6u
#define PCM_WIRE_REQUEST_TOKEN 7u
#define PCM_WIRE_REQUEST_PAYLOAD_BYTES 9u
#define PCM_WIRE_REQUEST_GENERATION 11u
/* Packet BODY offsets: PS1{0..3/A}, token:u16, eight bytes. */
#define PCM_WIRE_REPLY_TOKEN 4u
#define PCM_WIRE_REPLY_DATA 6u
#define PCM_WIRE_ACK_OPERATION 6u
#define PCM_WIRE_ACK_STATUS 7u
#define PCM_WIRE_ACK_GENERATION 8u
#define PCM_WIRE_ACK_FREE 12u
/* One coherent32-byte logical state, transported as four8-byte slices. */
#define PCM_WIRE_STATE_GENERATION 0u
#define PCM_WIRE_STATE_RATE 4u
#define PCM_WIRE_STATE_CAPACITY 8u
#define PCM_WIRE_STATE_PRIME 10u
#define PCM_WIRE_STATE_QUEUED 12u
#define PCM_WIRE_STATE_FREE 14u
#define PCM_WIRE_STATE_ACCEPTED 16u
#define PCM_WIRE_STATE_CONSUMED 20u
#define PCM_WIRE_STATE_UNDERRUN 24u
#define PCM_WIRE_STATE_FLAGS 28u
#define PCM_WIRE_STATE_CHANNEL 29u
#define PCM_WIRE_STATE_STATUS 30u
#define PCM_WIRE_STATE_OPERATION 31u
#define PCM_WIRE_DISCOVER 0u
#define PCM_WIRE_OPEN 1u
#define PCM_WIRE_WRITE 2u
#define PCM_WIRE_STATE 3u
#define PCM_WIRE_RESET 4u
#define PCM_WIRE_MUTE 5u
#define PCM_WIRE_UNMUTE 6u
#define PCM_WIRE_STOP 7u
#define PCM_WIRE_CLOSE 8u
#endif
