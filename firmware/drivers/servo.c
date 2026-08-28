#include "drivers/servo.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>

#include "hal/gpio.h"

#define SERVO_SIGNAL_BIT PB1
#define SERVO_MIN_PULSE_MS 1U
#define SERVO_MAX_PULSE_MS 2U
#define SERVO_ONE_MS_TICKS 2000U
#define SERVO_TWO_MS_TICKS 4000U
#define SERVO_FRAME_TICKS 40000U
#define SERVO_INITIAL_COMPARE_DELAY_TICKS 2000U

static volatile uint8_t g_servo_pulse_ms = SERVO_MIN_PULSE_MS;
static volatile uint8_t g_servo_signal_high = 0U;
static volatile uint8_t g_servo_active_pulse_ms = SERVO_MIN_PULSE_MS;

ISR(TIMER1_COMPA_vect)
{
    uint16_t interval_ticks;

    if (g_servo_signal_high == 0U) {
        g_servo_active_pulse_ms = g_servo_pulse_ms;
        gpio_write_high(&PORTB, SERVO_SIGNAL_BIT);
        g_servo_signal_high = 1U;

        interval_ticks =
            (g_servo_active_pulse_ms == SERVO_MAX_PULSE_MS)
                ? SERVO_TWO_MS_TICKS
                : SERVO_ONE_MS_TICKS;
    } else {
        gpio_write_low(&PORTB, SERVO_SIGNAL_BIT);
        g_servo_signal_high = 0U;

        interval_ticks =
            (g_servo_active_pulse_ms == SERVO_MAX_PULSE_MS)
                ? (SERVO_FRAME_TICKS - SERVO_TWO_MS_TICKS)
                : (SERVO_FRAME_TICKS - SERVO_ONE_MS_TICKS);
    }

    OCR1A = (uint16_t)(OCR1A + interval_ticks);
}

void servo_init(void)
{
    gpio_set_output(&DDRB, SERVO_SIGNAL_BIT);
    gpio_write_low(&PORTB, SERVO_SIGNAL_BIT);

    g_servo_pulse_ms = SERVO_MIN_PULSE_MS;
    g_servo_signal_high = 0U;
    g_servo_active_pulse_ms = SERVO_MIN_PULSE_MS;

    OCR1A = (uint16_t)(TCNT1 + SERVO_INITIAL_COMPARE_DELAY_TICKS);
    TIFR1 = (uint8_t)(1U << OCF1A);
    TIMSK1 |= (uint8_t)(1U << OCIE1A);
}

void servo_set_pulse_ms(uint8_t pulse_ms)
{
    if ((pulse_ms == SERVO_MIN_PULSE_MS) ||
        (pulse_ms == SERVO_MAX_PULSE_MS)) {
        g_servo_pulse_ms = pulse_ms;
    }
}

void servo_service_1ms(void)
{
}

void servo_stop(void)
{
    TIMSK1 &= (uint8_t)~(1U << OCIE1A);
    gpio_write_low(&PORTB, SERVO_SIGNAL_BIT);
    g_servo_signal_high = 0U;
}
