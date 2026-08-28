#include "drivers/stepper.h"

#include <avr/io.h>
#include <stdint.h>

#include "hal/gpio.h"

#define STEPPER_IN1_BIT PD3
#define STEPPER_IN2_BIT PD4
#define STEPPER_IN3_BIT PD5
#define STEPPER_IN4_BIT PD6

#define STEPPER_IN1_MASK (1U << 0)
#define STEPPER_IN2_MASK (1U << 1)
#define STEPPER_IN3_MASK (1U << 2)
#define STEPPER_IN4_MASK (1U << 3)

#define STEPPER_SEQUENCE_STATES 8U

static uint8_t g_step_index = 0U;

static void stepper_write_phase(uint8_t bit, uint8_t enabled)
{
    if (enabled != 0U) {
        gpio_write_high(&PORTD, bit);
    } else {
        gpio_write_low(&PORTD, bit);
    }
}

static void stepper_apply_state(uint8_t state)
{
    stepper_write_phase(STEPPER_IN1_BIT, state & STEPPER_IN1_MASK);
    stepper_write_phase(STEPPER_IN2_BIT, state & STEPPER_IN2_MASK);
    stepper_write_phase(STEPPER_IN3_BIT, state & STEPPER_IN3_MASK);
    stepper_write_phase(STEPPER_IN4_BIT, state & STEPPER_IN4_MASK);
}

void stepper_init(void)
{
    gpio_set_output(&DDRD, STEPPER_IN1_BIT);
    gpio_set_output(&DDRD, STEPPER_IN2_BIT);
    gpio_set_output(&DDRD, STEPPER_IN3_BIT);
    gpio_set_output(&DDRD, STEPPER_IN4_BIT);

    g_step_index = 0U;
    stepper_stop();
}

void stepper_step_forward(void)
{
    uint8_t state;

    switch (g_step_index) {
    case 0U:
        state = STEPPER_IN1_MASK;
        break;
    case 1U:
        state = STEPPER_IN1_MASK | STEPPER_IN2_MASK;
        break;
    case 2U:
        state = STEPPER_IN2_MASK;
        break;
    case 3U:
        state = STEPPER_IN2_MASK | STEPPER_IN3_MASK;
        break;
    case 4U:
        state = STEPPER_IN3_MASK;
        break;
    case 5U:
        state = STEPPER_IN3_MASK | STEPPER_IN4_MASK;
        break;
    case 6U:
        state = STEPPER_IN4_MASK;
        break;
    default:
        state = STEPPER_IN4_MASK | STEPPER_IN1_MASK;
        break;
    }

    stepper_apply_state(state);

    g_step_index++;
    if (g_step_index >= STEPPER_SEQUENCE_STATES) {
        g_step_index = 0U;
    }
}

void stepper_stop(void)
{
    gpio_write_low(&PORTD, STEPPER_IN1_BIT);
    gpio_write_low(&PORTD, STEPPER_IN2_BIT);
    gpio_write_low(&PORTD, STEPPER_IN3_BIT);
    gpio_write_low(&PORTD, STEPPER_IN4_BIT);
}
