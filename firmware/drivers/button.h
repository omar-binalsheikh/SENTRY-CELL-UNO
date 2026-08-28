#ifndef SENTRY_CELL_BUTTON_H
#define SENTRY_CELL_BUTTON_H

#include <stdint.h>
#include <avr/io.h>

#include "hal/gpio.h"

static inline void button_init(void)
{
    gpio_set_input_pullup(&DDRD, &PORTD, PD2);
}

static inline uint8_t button_is_pressed(void)
{
    return (gpio_read(&PIND, PD2) == 0U) ? 1U : 0U;
}

#endif
