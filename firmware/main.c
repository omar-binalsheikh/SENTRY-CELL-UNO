#include <avr/interrupt.h>
#include <stdint.h>

#include "app/system_fsm.h"
#include "diagnostics/diagnostics.h"
#include "diagnostics/memory_profiler.h"
#include "diagnostics/runtime_profiler.h"
#include "diagnostics/timing_profiler.h"
#include "drivers/button.h"
#include "drivers/dc_motor.h"
#include "drivers/hcsr04.h"
#include "drivers/led.h"
#include "drivers/relay.h"
#include "drivers/servo.h"
#include "drivers/stepper.h"
#include "drivers/thermistor.h"
#include "hal/adc.h"
#include "hal/system_time.h"
#include "hal/timing.h"
#include "hal/uart.h"
#include "hal/watchdog.h"
#include "protocol/protocol.h"
#include "safety/safety.h"
#include "scheduler/scheduler.h"

#define ACTUATOR_SERVICE_TASK_PERIOD_MS 1U
#define CONTROL_TASK_PERIOD_MS 10U
#define SENSOR_SAFETY_TASK_PERIOD_MS 30U
#define COMMUNICATION_TASK_PERIOD_MS 10U

#define STEPPER_STEP_PERIOD_MS 5U
#define HCSR04_TICKS_PER_CENTIMETER 116U
#define DIAGNOSTIC_PATTERN_PERIOD_MS 1000U
#define DIAGNOSTIC_FIRST_BLINK_END_MS 150U
#define DIAGNOSTIC_FIRST_GAP_END_MS 300U
#define DIAGNOSTIC_SECOND_BLINK_END_MS 450U
#define DIAGNOSTIC_FALLBACK_ON_MS 500U

static volatile uint16_t g_last_thermistor_raw = 0U;

static void set_safe_outputs(void)
{
    stepper_stop();
    dc_motor_stop();
    relay_off();
    servo_set_pulse_ms(1U);
    led_off();
}

static void apply_safe_state_led(uint32_t now_ms)
{
    const uint16_t phase_ms =
        (uint16_t)(now_ms % DIAGNOSTIC_PATTERN_PERIOD_MS);

    if (diagnostics_get_last_fault() ==
        DIAG_FAULT_OBSTACLE_CRITICAL) {
        if ((phase_ms < DIAGNOSTIC_FIRST_BLINK_END_MS) ||
            ((phase_ms >= DIAGNOSTIC_FIRST_GAP_END_MS) &&
             (phase_ms < DIAGNOSTIC_SECOND_BLINK_END_MS))) {
            led_on();
        } else {
            led_off();
        }
    } else if (phase_ms < DIAGNOSTIC_FALLBACK_ON_MS) {
        led_on();
    } else {
        led_off();
    }
}

static void actuator_service_task(void)
{
    static uint32_t last_step_ms = 0U;
    timing_profiler_record_start(
        TIMING_TASK_ACTUATOR,
        system_time_ms(),
        ACTUATOR_SERVICE_TASK_PERIOD_MS);
    const uint16_t start_ticks = timing_counter_ticks();
    const uint32_t now_ms = system_time_ms();
    uint16_t elapsed_ticks;
    uint16_t end_ticks;

    if (system_fsm_get_state() == SYSTEM_STATE_ACTIVE) {
        if ((uint32_t)(now_ms - last_step_ms) >=
            STEPPER_STEP_PERIOD_MS) {
            last_step_ms = now_ms;
            stepper_step_forward();
        }
    } else {
        stepper_stop();
        last_step_ms = now_ms;
    }

    end_ticks = timing_counter_ticks();
    elapsed_ticks = (uint16_t)(end_ticks - start_ticks);
    timing_profiler_record(TIMING_TASK_ACTUATOR, elapsed_ticks);
    runtime_profiler_record_execution(
        TIMING_TASK_ACTUATOR,
        elapsed_ticks,
        ACTUATOR_SERVICE_TASK_PERIOD_MS);
}

static void control_task(void)
{
    static uint8_t button_armed = 0U;
    timing_profiler_record_start(
        TIMING_TASK_CONTROL,
        system_time_ms(),
        CONTROL_TASK_PERIOD_MS);
    const uint16_t start_ticks = timing_counter_ticks();
    const uint8_t button_pressed = button_is_pressed();
    const uint32_t now_ms = system_time_ms();
    system_state_t state = system_fsm_get_state();
    uint16_t elapsed_ticks;
    uint16_t end_ticks;

    if (state == SYSTEM_STATE_SAFE_STATE) {
        button_armed = 0U;
    } else if (button_pressed == 0U) {
        button_armed = 1U;
    } else if (button_armed != 0U) {
        button_armed = 0U;

        if ((state == SYSTEM_STATE_IDLE) ||
            (state == SYSTEM_STATE_ACTIVE)) {
            system_fsm_handle_event(SYSTEM_EVENT_START_STOP);
            state = system_fsm_get_state();
        }
    }

    switch (state) {
    case SYSTEM_STATE_IDLE:
        relay_off();
        dc_motor_stop();
        servo_set_pulse_ms(1U);
        led_off();
        break;

    case SYSTEM_STATE_ACTIVE:
        relay_on();
        dc_motor_forward();
        servo_set_pulse_ms(2U);
        led_on();
        break;

    case SYSTEM_STATE_SAFE_STATE:
        relay_off();
        dc_motor_stop();
        servo_set_pulse_ms(1U);
        apply_safe_state_led(now_ms);
        break;

    case SYSTEM_STATE_BOOT:
    default:
        set_safe_outputs();
        break;
    }

    end_ticks = timing_counter_ticks();
    elapsed_ticks = (uint16_t)(end_ticks - start_ticks);
    timing_profiler_record(TIMING_TASK_CONTROL, elapsed_ticks);
    runtime_profiler_record_execution(
        TIMING_TASK_CONTROL, elapsed_ticks, CONTROL_TASK_PERIOD_MS);
}

static void sensor_safety_task(void)
{
    static uint8_t measurement_active = 0U;
    timing_profiler_record_start(
        TIMING_TASK_SENSOR_SAFETY,
        system_time_ms(),
        SENSOR_SAFETY_TASK_PERIOD_MS);
    const uint16_t start_ticks = timing_counter_ticks();
    uint16_t pulse_ticks;
    uint16_t distance_cm;
    uint16_t elapsed_ticks;
    uint16_t end_ticks;
    uint8_t valid;

    g_last_thermistor_raw = thermistor_read_raw();

    if (measurement_active == 0U) {
        measurement_active = hcsr04_start();
        end_ticks = timing_counter_ticks();
        elapsed_ticks = (uint16_t)(end_ticks - start_ticks);
        timing_profiler_record(TIMING_TASK_SENSOR_SAFETY, elapsed_ticks);
        runtime_profiler_record_execution(
            TIMING_TASK_SENSOR_SAFETY,
            elapsed_ticks,
            SENSOR_SAFETY_TASK_PERIOD_MS);
        return;
    }

    if (hcsr04_result_ready() != 0U) {
        pulse_ticks = hcsr04_get_pulse_ticks();
        distance_cm =
            (uint16_t)(pulse_ticks / HCSR04_TICKS_PER_CENTIMETER);
        valid = (distance_cm > 0U) ? 1U : 0U;

        if ((system_fsm_get_state() == SYSTEM_STATE_ACTIVE) &&
            (safety_obstacle_is_critical(valid, distance_cm) != 0U)) {
            diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);
            system_fsm_handle_event(SYSTEM_EVENT_CRITICAL_FAULT);
        }
    } else {
        hcsr04_abort();
    }

    measurement_active = 0U;
    end_ticks = timing_counter_ticks();
    elapsed_ticks = (uint16_t)(end_ticks - start_ticks);
    timing_profiler_record(TIMING_TASK_SENSOR_SAFETY, elapsed_ticks);
    runtime_profiler_record_execution(
        TIMING_TASK_SENSOR_SAFETY,
        elapsed_ticks,
        SENSOR_SAFETY_TASK_PERIOD_MS);
}

static void communication_task(void)
{
    timing_profiler_record_start(
        TIMING_TASK_COMMUNICATION,
        system_time_ms(),
        COMMUNICATION_TASK_PERIOD_MS);
    const uint16_t start_ticks = timing_counter_ticks();
    uint8_t byte;
    uint8_t status_sequence;
    uint8_t timing_sequence;
    uint8_t jitter_sequence;
    uint8_t runtime_memory_sequence;
    uint8_t cpu_load_sequence;
    uint8_t overrun_sequence;
    uint8_t reset_cause_sequence;
    uint8_t watchdog_status_sequence;
    uint8_t uart_overflow;
    uint8_t timeout_count;
    uint8_t crc_error_count;
    uint16_t actuator_ticks;
    uint16_t control_ticks;
    uint16_t sensor_safety_ticks;
    uint16_t communication_ticks;
    uint16_t actuator_jitter_ms;
    uint16_t control_jitter_ms;
    uint16_t sensor_safety_jitter_ms;
    uint16_t communication_jitter_ms;
    uint16_t min_free_bytes;
    uint16_t painted_bytes;
    uint16_t used_painted_bytes;
    uint16_t elapsed_ticks;
    uint16_t end_ticks;
    uint32_t now_ms;
    protocol_frame_t response;

    now_ms = system_time_ms();
    protocol_check_timeout(now_ms);

    while (uart_read_byte(&byte) != 0U) {
        now_ms = system_time_ms();
        protocol_process_byte(byte, now_ms);
    }

    if (protocol_watchdog_block_requested() != 0U) {
        set_safe_outputs();

        for (;;) {
        }
    }

    if ((protocol_response_pending() != 0U) &&
        (protocol_get_response(&response) != 0U)) {
        if (protocol_send_frame(&response) != 0U) {
            protocol_response_sent();
        }
    }

    if (protocol_comm_status_requested(&status_sequence) != 0U) {
        uart_overflow = uart_rx_overflow_count();
        timeout_count = protocol_get_timeout_count();
        crc_error_count = protocol_get_crc_error_count();
        protocol_send_comm_status(
            status_sequence, uart_overflow, timeout_count, crc_error_count);
    }

    if (protocol_timing_status_requested(&timing_sequence) != 0U) {
        actuator_ticks =
            timing_profiler_get_max_ticks(TIMING_TASK_ACTUATOR);
        control_ticks =
            timing_profiler_get_max_ticks(TIMING_TASK_CONTROL);
        sensor_safety_ticks =
            timing_profiler_get_max_ticks(TIMING_TASK_SENSOR_SAFETY);
        communication_ticks =
            timing_profiler_get_max_ticks(TIMING_TASK_COMMUNICATION);
        protocol_send_timing_status(
            timing_sequence,
            actuator_ticks,
            control_ticks,
            sensor_safety_ticks,
            communication_ticks);
    }

    if (protocol_jitter_status_requested(&jitter_sequence) != 0U) {
        actuator_jitter_ms =
            timing_profiler_get_max_jitter_ms(TIMING_TASK_ACTUATOR);
        control_jitter_ms =
            timing_profiler_get_max_jitter_ms(TIMING_TASK_CONTROL);
        sensor_safety_jitter_ms =
            timing_profiler_get_max_jitter_ms(TIMING_TASK_SENSOR_SAFETY);
        communication_jitter_ms =
            timing_profiler_get_max_jitter_ms(TIMING_TASK_COMMUNICATION);
        protocol_send_jitter_status(
            jitter_sequence,
            actuator_jitter_ms,
            control_jitter_ms,
            sensor_safety_jitter_ms,
            communication_jitter_ms);
    }

    if (protocol_runtime_memory_status_requested(
            &runtime_memory_sequence) != 0U) {
        min_free_bytes = memory_profiler_get_min_free_bytes();
        painted_bytes = memory_profiler_get_painted_bytes();
        used_painted_bytes =
            memory_profiler_get_used_painted_bytes();
        protocol_send_runtime_memory_status(
            runtime_memory_sequence,
            min_free_bytes,
            painted_bytes,
            used_painted_bytes);
    }

    if (protocol_cpu_load_status_requested(&cpu_load_sequence) != 0U) {
        protocol_send_cpu_load_status(
            cpu_load_sequence,
            runtime_profiler_get_busy_ticks(),
            runtime_profiler_get_elapsed_ms(system_time_ms()));
    }

    if (protocol_overrun_status_requested(&overrun_sequence) != 0U) {
        protocol_send_overrun_status(
            overrun_sequence,
            runtime_profiler_get_overrun_count(TIMING_TASK_ACTUATOR),
            runtime_profiler_get_overrun_count(TIMING_TASK_CONTROL),
            runtime_profiler_get_overrun_count(TIMING_TASK_SENSOR_SAFETY),
            runtime_profiler_get_overrun_count(TIMING_TASK_COMMUNICATION));
    }

    if (protocol_reset_cause_requested(&reset_cause_sequence) != 0U) {
        protocol_send_reset_cause(
            reset_cause_sequence, watchdog_get_reset_cause());
    }

    if (protocol_watchdog_status_requested(
            &watchdog_status_sequence) != 0U) {
        protocol_send_watchdog_status(
            watchdog_status_sequence,
            watchdog_previous_timeout_detected() ? 1U : 0U);
    }

    end_ticks = timing_counter_ticks();
    elapsed_ticks = (uint16_t)(end_ticks - start_ticks);
    timing_profiler_record(TIMING_TASK_COMMUNICATION, elapsed_ticks);
    runtime_profiler_record_execution(
        TIMING_TASK_COMMUNICATION,
        elapsed_ticks,
        COMMUNICATION_TASK_PERIOD_MS);
}

int main(void)
{
    uint8_t actuator_service_task_added;
    uint8_t control_task_added;
    uint8_t sensor_safety_task_added;
    uint8_t communication_task_added;

    led_init();
    button_init();
    stepper_init();
    dc_motor_init();
    relay_init();
    adc_init();
    thermistor_init();
    hcsr04_init();
    servo_init();
    uart_init();
    system_time_init();
    scheduler_init();

    stepper_stop();
    dc_motor_stop();
    relay_off();
    servo_set_pulse_ms(1U);
    led_off();

    system_fsm_init();
    diagnostics_init();
    timing_profiler_init();
    protocol_init();
    system_fsm_handle_event(SYSTEM_EVENT_INIT_DONE);

    actuator_service_task_added = scheduler_add_task(
        actuator_service_task, ACTUATOR_SERVICE_TASK_PERIOD_MS);
    control_task_added = scheduler_add_task(
        control_task, CONTROL_TASK_PERIOD_MS);
    sensor_safety_task_added = scheduler_add_task(
        sensor_safety_task, SENSOR_SAFETY_TASK_PERIOD_MS);
    communication_task_added = scheduler_add_task(
        communication_task, COMMUNICATION_TASK_PERIOD_MS);

    if ((actuator_service_task_added == 0U) ||
        (control_task_added == 0U) ||
        (sensor_safety_task_added == 0U) ||
        (communication_task_added == 0U)) {
        set_safe_outputs();

        for (;;) {
        }
    }

    memory_profiler_init();
    runtime_profiler_init(system_time_ms());
    watchdog_enable();

    sei();

    for (;;) {
        scheduler_run();
        watchdog_kick();
    }
}
