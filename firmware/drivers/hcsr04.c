#include "drivers/hcsr04.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <util/atomic.h>

#include "hal/gpio.h"

#define HCSR04_TRIGGER_PULSE_CYCLES 160UL

#define HCSR04_STATE_IDLE 0U
#define HCSR04_STATE_WAIT_RISING 1U
#define HCSR04_STATE_WAIT_FALLING 2U

static volatile uint16_t g_start_tick = 0U;
static volatile uint16_t g_pulse_ticks = 0U;
static volatile uint8_t g_capture_state = HCSR04_STATE_IDLE;
static volatile uint8_t g_result_ready = 0U;

ISR(TIMER1_CAPT_vect)
{
    const uint16_t capture_tick = ICR1;

    if (g_capture_state == HCSR04_STATE_WAIT_RISING) {
        g_start_tick = capture_tick;
        g_capture_state = HCSR04_STATE_WAIT_FALLING;
        TCCR1B &= (uint8_t)~(1U << ICES1);
    } else if (g_capture_state == HCSR04_STATE_WAIT_FALLING) {
        g_pulse_ticks = (uint16_t)(capture_tick - g_start_tick);
        g_result_ready = 1U;
        g_capture_state = HCSR04_STATE_IDLE;
        TIMSK1 &= (uint8_t)~(1U << ICIE1);
    } else {
        TIMSK1 &= (uint8_t)~(1U << ICIE1);
    }
}

void hcsr04_init(void)
{
    gpio_set_output(&DDRD, PD7);
    gpio_write_low(&PORTD, PD7);

    DDRB &= (uint8_t)~(1U << DDB0);
    PORTB &= (uint8_t)~(1U << PORTB0);

    TCCR1A = 0U;
    TCCR1B = 0U;
    TIMSK1 &= (uint8_t)~(1U << ICIE1);
    TIFR1 = (uint8_t)((1U << ICF1) | (1U << TOV1));

    g_start_tick = 0U;
    g_pulse_ticks = 0U;
    g_capture_state = HCSR04_STATE_IDLE;
    g_result_ready = 0U;

    TCCR1B = (uint8_t)((1U << ICES1) | (1U << CS11));
}

uint8_t hcsr04_start(void)
{
    uint8_t started = 0U;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        if (g_capture_state == HCSR04_STATE_IDLE) {
            g_pulse_ticks = 0U;
            g_result_ready = 0U;
            g_capture_state = HCSR04_STATE_WAIT_RISING;

            TCCR1B = (uint8_t)((1U << ICES1) | (1U << CS11));
            TIFR1 = (uint8_t)((1U << ICF1) | (1U << TOV1));
            TIMSK1 |= (uint8_t)(1U << ICIE1);
            started = 1U;
        }
    }

    if (started != 0U) {
        gpio_write_high(&PORTD, PD7);
        __builtin_avr_delay_cycles(HCSR04_TRIGGER_PULSE_CYCLES);
        gpio_write_low(&PORTD, PD7);
    }

    return started;
}

uint8_t hcsr04_result_ready(void)
{
    return g_result_ready;
}

uint16_t hcsr04_get_pulse_ticks(void)
{
    uint16_t pulse_ticks;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        pulse_ticks = g_pulse_ticks;
    }

    return pulse_ticks;
}

void hcsr04_abort(void)
{
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        TIMSK1 &= (uint8_t)~(1U << ICIE1);
        TCCR1B |= (uint8_t)(1U << ICES1);
        TIFR1 = (uint8_t)((1U << ICF1) | (1U << TOV1));
        g_capture_state = HCSR04_STATE_IDLE;
        g_result_ready = 0U;
    }

    gpio_write_low(&PORTD, PD7);
}
