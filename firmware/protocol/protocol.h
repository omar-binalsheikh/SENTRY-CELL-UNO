#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

#define PROTOCOL_SOF 0xA5U
#define PROTOCOL_VERSION 0x01U
#define PROTOCOL_MAX_PAYLOAD 8U
#define PROTOCOL_INTERBYTE_TIMEOUT_MS 100UL

#define PROTOCOL_TYPE_PING 0x01U
#define PROTOCOL_TYPE_ECHO 0x02U
#define PROTOCOL_TYPE_GET_COMM_STATUS 0x03U
#define PROTOCOL_TYPE_GET_TIMING_STATUS 0x04U
#define PROTOCOL_TYPE_GET_JITTER_STATUS 0x05U
#define PROTOCOL_TYPE_GET_RUNTIME_MEMORY_STATUS 0x06U
#define PROTOCOL_TYPE_GET_CPU_LOAD_STATUS 0x07U
#define PROTOCOL_TYPE_GET_OVERRUN_STATUS 0x08U
#define PROTOCOL_TYPE_GET_RESET_CAUSE 0x09U
#define PROTOCOL_TYPE_INJECT_WATCHDOG_BLOCK 0x0AU
#define PROTOCOL_TYPE_GET_WATCHDOG_STATUS 0x0BU
#define PROTOCOL_TYPE_PONG 0x81U
#define PROTOCOL_TYPE_COMM_STATUS 0x83U
#define PROTOCOL_TYPE_TIMING_STATUS 0x84U
#define PROTOCOL_TYPE_JITTER_STATUS 0x85U
#define PROTOCOL_TYPE_RUNTIME_MEMORY_STATUS 0x86U
#define PROTOCOL_TYPE_CPU_LOAD_STATUS 0x87U
#define PROTOCOL_TYPE_OVERRUN_STATUS 0x88U
#define PROTOCOL_TYPE_RESET_CAUSE 0x89U
/* Persistent watchdog ISR marker captured at boot; not an MCUSR value. */
#define PROTOCOL_TYPE_WATCHDOG_STATUS 0x8BU
#define PROTOCOL_TYPE_ACK 0x90U
#define PROTOCOL_TYPE_NACK 0x91U

#define PROTOCOL_NACK_UNSUPPORTED_TYPE 0x01U
#define PROTOCOL_NACK_INVALID_LENGTH 0x02U

typedef struct {
    uint8_t type;
    uint8_t sequence;
    uint8_t length;
    uint8_t payload[PROTOCOL_MAX_PAYLOAD];
} protocol_frame_t;

void protocol_init(void);
void protocol_process_byte(uint8_t byte, uint32_t now_ms);
void protocol_check_timeout(uint32_t now_ms);
uint8_t protocol_get_timeout_count(void);
uint8_t protocol_get_crc_error_count(void);
uint8_t protocol_response_pending(void);
uint8_t protocol_get_response(protocol_frame_t *frame);
void protocol_response_sent(void);
uint8_t protocol_send_frame(const protocol_frame_t *frame);
uint8_t protocol_comm_status_requested(uint8_t *sequence);
uint8_t protocol_send_comm_status(
    uint8_t sequence,
    uint8_t uart_overflow,
    uint8_t timeout_count,
    uint8_t crc_error_count);
uint8_t protocol_timing_status_requested(uint8_t *sequence);
uint8_t protocol_send_timing_status(
    uint8_t sequence,
    uint16_t actuator_ticks,
    uint16_t control_ticks,
    uint16_t sensor_safety_ticks,
    uint16_t communication_ticks);
uint8_t protocol_jitter_status_requested(uint8_t *sequence);
uint8_t protocol_send_jitter_status(
    uint8_t sequence,
    uint16_t actuator_ms,
    uint16_t control_ms,
    uint16_t sensor_safety_ms,
    uint16_t communication_ms);
uint8_t protocol_runtime_memory_status_requested(uint8_t *sequence);
uint8_t protocol_send_runtime_memory_status(
    uint8_t sequence,
    uint16_t min_free_bytes,
    uint16_t painted_bytes,
    uint16_t used_painted_bytes);
uint8_t protocol_cpu_load_status_requested(uint8_t *sequence);
uint8_t protocol_send_cpu_load_status(
    uint8_t sequence,
    uint32_t busy_ticks,
    uint32_t elapsed_ms);
uint8_t protocol_overrun_status_requested(uint8_t *sequence);
uint8_t protocol_send_overrun_status(
    uint8_t sequence,
    uint16_t actuator,
    uint16_t control,
    uint16_t sensor_safety,
    uint16_t communication);
uint8_t protocol_reset_cause_requested(uint8_t *sequence);
uint8_t protocol_send_reset_cause(uint8_t sequence, uint8_t reset_cause);
uint8_t protocol_watchdog_status_requested(uint8_t *sequence);
uint8_t protocol_send_watchdog_status(
    uint8_t sequence, uint8_t timeout_detected);
uint8_t protocol_watchdog_block_requested(void);

#endif
