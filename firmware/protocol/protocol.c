#include "protocol/protocol.h"

#include <stddef.h>

#include "hal/uart.h"
#include "protocol/crc8.h"

typedef enum {
    PROTOCOL_STATE_WAIT_SOF = 0,
    PROTOCOL_STATE_READ_VERSION,
    PROTOCOL_STATE_READ_TYPE,
    PROTOCOL_STATE_READ_SEQUENCE,
    PROTOCOL_STATE_READ_LENGTH,
    PROTOCOL_STATE_READ_PAYLOAD,
    PROTOCOL_STATE_READ_CRC
} protocol_parser_state_t;

#define PROTOCOL_CRC_HEADER_SIZE 4U
#define PROTOCOL_CRC_DATA_SIZE (PROTOCOL_CRC_HEADER_SIZE + PROTOCOL_MAX_PAYLOAD)
#define PROTOCOL_FRAME_OVERHEAD_SIZE 6U
#define PROTOCOL_MAX_FRAME_SIZE \
    (PROTOCOL_FRAME_OVERHEAD_SIZE + PROTOCOL_MAX_PAYLOAD)

static protocol_parser_state_t parser_state;
static protocol_frame_t received_frame;
static protocol_frame_t pending_frame;
static uint8_t payload_index;
static uint8_t response_pending;
static uint32_t last_byte_ms;
static uint8_t parser_timeout_count;
static uint8_t crc_error_count;
static uint8_t comm_status_request_pending;
static uint8_t comm_status_sequence;
static uint8_t timing_status_request_pending;
static uint8_t timing_status_sequence;
static uint8_t jitter_status_request_pending;
static uint8_t jitter_status_sequence;
static uint8_t runtime_memory_status_request_pending;
static uint8_t runtime_memory_status_sequence;
static uint8_t cpu_load_status_request_pending;
static uint8_t cpu_load_status_sequence;
static uint8_t overrun_status_request_pending;
static uint8_t overrun_status_sequence;
static uint8_t reset_cause_request_pending;
static uint8_t reset_cause_sequence;
static uint8_t watchdog_status_request_pending;
static uint8_t watchdog_status_sequence;
static uint8_t watchdog_block_request_pending;

static void protocol_reset_parser(void)
{
    parser_state = PROTOCOL_STATE_WAIT_SOF;
    received_frame.type = 0U;
    received_frame.sequence = 0U;
    received_frame.length = 0U;
    payload_index = 0U;
    last_byte_ms = 0U;
}

static void protocol_increment_saturating(uint8_t *counter)
{
    if (*counter != UINT8_MAX) {
        (*counter)++;
    }
}

static uint8_t protocol_compute_crc(const protocol_frame_t *frame)
{
    uint8_t crc_data[PROTOCOL_CRC_DATA_SIZE];
    uint8_t index;

    if ((frame == NULL) || (frame->length > PROTOCOL_MAX_PAYLOAD)) {
        return 0U;
    }

    crc_data[0] = PROTOCOL_VERSION;
    crc_data[1] = frame->type;
    crc_data[2] = frame->sequence;
    crc_data[3] = frame->length;

    for (index = 0U; index < frame->length; index++) {
        crc_data[PROTOCOL_CRC_HEADER_SIZE + index] = frame->payload[index];
    }

    return crc8_compute(
        crc_data, (uint8_t)(PROTOCOL_CRC_HEADER_SIZE + frame->length));
}

static void protocol_prepare_nack(uint8_t sequence, uint8_t reason)
{
    pending_frame.type = PROTOCOL_TYPE_NACK;
    pending_frame.sequence = sequence;
    pending_frame.length = 1U;
    pending_frame.payload[0] = reason;
    response_pending = 1U;
}

static void protocol_handle_frame(const protocol_frame_t *frame)
{
    uint8_t index;

    if (frame->type == PROTOCOL_TYPE_GET_COMM_STATUS) {
        if (frame->length == 0U) {
            if (comm_status_request_pending == 0U) {
                comm_status_sequence = frame->sequence;
                comm_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_TIMING_STATUS) {
        if (frame->length == 0U) {
            if (timing_status_request_pending == 0U) {
                timing_status_sequence = frame->sequence;
                timing_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_JITTER_STATUS) {
        if (frame->length == 0U) {
            if (jitter_status_request_pending == 0U) {
                jitter_status_sequence = frame->sequence;
                jitter_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_RUNTIME_MEMORY_STATUS) {
        if (frame->length == 0U) {
            if (runtime_memory_status_request_pending == 0U) {
                runtime_memory_status_sequence = frame->sequence;
                runtime_memory_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_CPU_LOAD_STATUS) {
        if (frame->length == 0U) {
            if (cpu_load_status_request_pending == 0U) {
                cpu_load_status_sequence = frame->sequence;
                cpu_load_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_OVERRUN_STATUS) {
        if (frame->length == 0U) {
            if (overrun_status_request_pending == 0U) {
                overrun_status_sequence = frame->sequence;
                overrun_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_RESET_CAUSE) {
        if (frame->length == 0U) {
            if (reset_cause_request_pending == 0U) {
                reset_cause_sequence = frame->sequence;
                reset_cause_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_GET_WATCHDOG_STATUS) {
        if (frame->length == 0U) {
            if (watchdog_status_request_pending == 0U) {
                watchdog_status_sequence = frame->sequence;
                watchdog_status_request_pending = 1U;
            }
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (frame->type == PROTOCOL_TYPE_INJECT_WATCHDOG_BLOCK) {
        if (frame->length == 0U) {
            watchdog_block_request_pending = 1U;
        } else if (response_pending == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
        return;
    }

    if (response_pending != 0U) {
        return;
    }

    if (frame->type == PROTOCOL_TYPE_PING) {
        if (frame->length == 0U) {
            pending_frame.type = PROTOCOL_TYPE_PONG;
            pending_frame.sequence = frame->sequence;
            pending_frame.length = 0U;
            response_pending = 1U;
        } else {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        }
    } else if (frame->type == PROTOCOL_TYPE_ECHO) {
        if (frame->length == 0U) {
            protocol_prepare_nack(
                frame->sequence, PROTOCOL_NACK_INVALID_LENGTH);
        } else {
            pending_frame.type = PROTOCOL_TYPE_ACK;
            pending_frame.sequence = frame->sequence;
            pending_frame.length = frame->length;

            for (index = 0U; index < frame->length; index++) {
                pending_frame.payload[index] = frame->payload[index];
            }
            response_pending = 1U;
        }
    } else {
        protocol_prepare_nack(
            frame->sequence, PROTOCOL_NACK_UNSUPPORTED_TYPE);
    }
}

void protocol_init(void)
{
    protocol_reset_parser();
    pending_frame.type = 0U;
    pending_frame.sequence = 0U;
    pending_frame.length = 0U;
    response_pending = 0U;
    parser_timeout_count = 0U;
    crc_error_count = 0U;
    comm_status_request_pending = 0U;
    comm_status_sequence = 0U;
    timing_status_request_pending = 0U;
    timing_status_sequence = 0U;
    jitter_status_request_pending = 0U;
    jitter_status_sequence = 0U;
    runtime_memory_status_request_pending = 0U;
    runtime_memory_status_sequence = 0U;
    cpu_load_status_request_pending = 0U;
    cpu_load_status_sequence = 0U;
    overrun_status_request_pending = 0U;
    overrun_status_sequence = 0U;
    reset_cause_request_pending = 0U;
    reset_cause_sequence = 0U;
    watchdog_status_request_pending = 0U;
    watchdog_status_sequence = 0U;
    watchdog_block_request_pending = 0U;
}

void protocol_process_byte(uint8_t byte, uint32_t now_ms)
{
    if (parser_state != PROTOCOL_STATE_WAIT_SOF) {
        last_byte_ms = now_ms;
    }

    switch (parser_state) {
    case PROTOCOL_STATE_WAIT_SOF:
        if (byte == PROTOCOL_SOF) {
            protocol_reset_parser();
            parser_state = PROTOCOL_STATE_READ_VERSION;
            last_byte_ms = now_ms;
        }
        break;

    case PROTOCOL_STATE_READ_VERSION:
        if (byte == PROTOCOL_VERSION) {
            parser_state = PROTOCOL_STATE_READ_TYPE;
        } else {
            protocol_reset_parser();
        }
        break;

    case PROTOCOL_STATE_READ_TYPE:
        received_frame.type = byte;
        parser_state = PROTOCOL_STATE_READ_SEQUENCE;
        break;

    case PROTOCOL_STATE_READ_SEQUENCE:
        received_frame.sequence = byte;
        parser_state = PROTOCOL_STATE_READ_LENGTH;
        break;

    case PROTOCOL_STATE_READ_LENGTH:
        received_frame.length = byte;
        payload_index = 0U;

        if (byte > PROTOCOL_MAX_PAYLOAD) {
            protocol_reset_parser();
        } else if (byte == 0U) {
            parser_state = PROTOCOL_STATE_READ_CRC;
        } else {
            parser_state = PROTOCOL_STATE_READ_PAYLOAD;
        }
        break;

    case PROTOCOL_STATE_READ_PAYLOAD:
        if ((payload_index < received_frame.length) &&
            (payload_index < PROTOCOL_MAX_PAYLOAD)) {
            received_frame.payload[payload_index] = byte;
            payload_index++;

            if (payload_index == received_frame.length) {
                parser_state = PROTOCOL_STATE_READ_CRC;
            }
        } else {
            protocol_reset_parser();
        }
        break;

    case PROTOCOL_STATE_READ_CRC:
        if (byte == protocol_compute_crc(&received_frame)) {
            protocol_handle_frame(&received_frame);
        } else {
            protocol_increment_saturating(&crc_error_count);
        }
        protocol_reset_parser();
        break;

    default:
        protocol_reset_parser();
        break;
    }
}

void protocol_check_timeout(uint32_t now_ms)
{
    if ((parser_state != PROTOCOL_STATE_WAIT_SOF) &&
        ((uint32_t)(now_ms - last_byte_ms) >=
         PROTOCOL_INTERBYTE_TIMEOUT_MS)) {
        protocol_reset_parser();
        protocol_increment_saturating(&parser_timeout_count);
    }
}

uint8_t protocol_get_timeout_count(void)
{
    return parser_timeout_count;
}

uint8_t protocol_get_crc_error_count(void)
{
    return crc_error_count;
}

uint8_t protocol_response_pending(void)
{
    return response_pending;
}

uint8_t protocol_get_response(protocol_frame_t *frame)
{
    uint8_t index;

    if ((frame == NULL) || (response_pending == 0U)) {
        return 0U;
    }

    frame->type = pending_frame.type;
    frame->sequence = pending_frame.sequence;
    frame->length = pending_frame.length;

    for (index = 0U; index < pending_frame.length; index++) {
        frame->payload[index] = pending_frame.payload[index];
    }

    return 1U;
}

void protocol_response_sent(void)
{
    response_pending = 0U;
}

uint8_t protocol_send_frame(const protocol_frame_t *frame)
{
    uint8_t encoded_frame[PROTOCOL_MAX_FRAME_SIZE];
    uint8_t encoded_length;
    uint8_t crc;
    uint8_t index;

    if ((frame == NULL) || (frame->length > PROTOCOL_MAX_PAYLOAD)) {
        return 0U;
    }

    crc = protocol_compute_crc(frame);
    encoded_frame[0] = PROTOCOL_SOF;
    encoded_frame[1] = PROTOCOL_VERSION;
    encoded_frame[2] = frame->type;
    encoded_frame[3] = frame->sequence;
    encoded_frame[4] = frame->length;

    for (index = 0U; index < frame->length; index++) {
        encoded_frame[5U + index] = frame->payload[index];
    }

    encoded_frame[5U + frame->length] = crc;
    encoded_length =
        (uint8_t)(PROTOCOL_FRAME_OVERHEAD_SIZE + frame->length);
    return uart_tx_write(encoded_frame, encoded_length);
}

uint8_t protocol_comm_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) || (comm_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = comm_status_sequence;
    return 1U;
}

uint8_t protocol_send_comm_status(
    uint8_t sequence,
    uint8_t uart_overflow,
    uint8_t timeout_count,
    uint8_t crc_error_count)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_COMM_STATUS;
    frame.sequence = sequence;
    frame.length = 3U;
    frame.payload[0] = uart_overflow;
    frame.payload[1] = timeout_count;
    frame.payload[2] = crc_error_count;

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    comm_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_timing_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) || (timing_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = timing_status_sequence;
    return 1U;
}

uint8_t protocol_send_timing_status(
    uint8_t sequence,
    uint16_t actuator_ticks,
    uint16_t control_ticks,
    uint16_t sensor_safety_ticks,
    uint16_t communication_ticks)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_TIMING_STATUS;
    frame.sequence = sequence;
    frame.length = 8U;
    frame.payload[0] = (uint8_t)actuator_ticks;
    frame.payload[1] = (uint8_t)(actuator_ticks >> 8U);
    frame.payload[2] = (uint8_t)control_ticks;
    frame.payload[3] = (uint8_t)(control_ticks >> 8U);
    frame.payload[4] = (uint8_t)sensor_safety_ticks;
    frame.payload[5] = (uint8_t)(sensor_safety_ticks >> 8U);
    frame.payload[6] = (uint8_t)communication_ticks;
    frame.payload[7] = (uint8_t)(communication_ticks >> 8U);

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    timing_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_jitter_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) || (jitter_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = jitter_status_sequence;
    return 1U;
}

uint8_t protocol_send_jitter_status(
    uint8_t sequence,
    uint16_t actuator_ms,
    uint16_t control_ms,
    uint16_t sensor_safety_ms,
    uint16_t communication_ms)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_JITTER_STATUS;
    frame.sequence = sequence;
    frame.length = 8U;
    frame.payload[0] = (uint8_t)actuator_ms;
    frame.payload[1] = (uint8_t)(actuator_ms >> 8U);
    frame.payload[2] = (uint8_t)control_ms;
    frame.payload[3] = (uint8_t)(control_ms >> 8U);
    frame.payload[4] = (uint8_t)sensor_safety_ms;
    frame.payload[5] = (uint8_t)(sensor_safety_ms >> 8U);
    frame.payload[6] = (uint8_t)communication_ms;
    frame.payload[7] = (uint8_t)(communication_ms >> 8U);

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    jitter_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_runtime_memory_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) ||
        (runtime_memory_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = runtime_memory_status_sequence;
    return 1U;
}

uint8_t protocol_send_runtime_memory_status(
    uint8_t sequence,
    uint16_t min_free_bytes,
    uint16_t painted_bytes,
    uint16_t used_painted_bytes)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_RUNTIME_MEMORY_STATUS;
    frame.sequence = sequence;
    frame.length = 6U;
    frame.payload[0] = (uint8_t)min_free_bytes;
    frame.payload[1] = (uint8_t)(min_free_bytes >> 8U);
    frame.payload[2] = (uint8_t)painted_bytes;
    frame.payload[3] = (uint8_t)(painted_bytes >> 8U);
    frame.payload[4] = (uint8_t)used_painted_bytes;
    frame.payload[5] = (uint8_t)(used_painted_bytes >> 8U);

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    runtime_memory_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_cpu_load_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) ||
        (cpu_load_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = cpu_load_status_sequence;
    return 1U;
}

uint8_t protocol_send_cpu_load_status(
    uint8_t sequence,
    uint32_t busy_ticks,
    uint32_t elapsed_ms)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_CPU_LOAD_STATUS;
    frame.sequence = sequence;
    frame.length = 8U;
    frame.payload[0] = (uint8_t)busy_ticks;
    frame.payload[1] = (uint8_t)(busy_ticks >> 8U);
    frame.payload[2] = (uint8_t)(busy_ticks >> 16U);
    frame.payload[3] = (uint8_t)(busy_ticks >> 24U);
    frame.payload[4] = (uint8_t)elapsed_ms;
    frame.payload[5] = (uint8_t)(elapsed_ms >> 8U);
    frame.payload[6] = (uint8_t)(elapsed_ms >> 16U);
    frame.payload[7] = (uint8_t)(elapsed_ms >> 24U);

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    cpu_load_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_overrun_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) ||
        (overrun_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = overrun_status_sequence;
    return 1U;
}

uint8_t protocol_send_overrun_status(
    uint8_t sequence,
    uint16_t actuator,
    uint16_t control,
    uint16_t sensor_safety,
    uint16_t communication)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_OVERRUN_STATUS;
    frame.sequence = sequence;
    frame.length = 8U;
    frame.payload[0] = (uint8_t)actuator;
    frame.payload[1] = (uint8_t)(actuator >> 8U);
    frame.payload[2] = (uint8_t)control;
    frame.payload[3] = (uint8_t)(control >> 8U);
    frame.payload[4] = (uint8_t)sensor_safety;
    frame.payload[5] = (uint8_t)(sensor_safety >> 8U);
    frame.payload[6] = (uint8_t)communication;
    frame.payload[7] = (uint8_t)(communication >> 8U);

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    overrun_status_request_pending = 0U;
    return 1U;
}

uint8_t protocol_reset_cause_requested(uint8_t *sequence)
{
    if ((sequence == NULL) || (reset_cause_request_pending == 0U)) {
        return 0U;
    }

    *sequence = reset_cause_sequence;
    return 1U;
}

uint8_t protocol_send_reset_cause(uint8_t sequence, uint8_t cause)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_RESET_CAUSE;
    frame.sequence = sequence;
    frame.length = 1U;
    frame.payload[0] = cause;

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    reset_cause_request_pending = 0U;
    return 1U;
}

uint8_t protocol_watchdog_block_requested(void)
{
    return watchdog_block_request_pending;
}

uint8_t protocol_watchdog_status_requested(uint8_t *sequence)
{
    if ((sequence == NULL) ||
        (watchdog_status_request_pending == 0U)) {
        return 0U;
    }

    *sequence = watchdog_status_sequence;
    return 1U;
}

uint8_t protocol_send_watchdog_status(
    uint8_t sequence, uint8_t timeout_detected)
{
    protocol_frame_t frame;

    frame.type = PROTOCOL_TYPE_WATCHDOG_STATUS;
    frame.sequence = sequence;
    frame.length = 1U;
    frame.payload[0] = (timeout_detected != 0U) ? 1U : 0U;

    if (protocol_send_frame(&frame) == 0U) {
        return 0U;
    }

    watchdog_status_request_pending = 0U;
    return 1U;
}
