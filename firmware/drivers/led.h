#ifndef SENTRY_CELL_LED_H
#define SENTRY_CELL_LED_H

#include <avr/io.h>

#include "hal/gpio.h"

static inline void led_init(void)
{
    gpio_set_output(&DDRB, PB5);
    gpio_write_low(&PORTB, PB5);
}

static inline void led_on(void)
{
    gpio_write_high(&PORTB, PB5);
}

static inline void led_off(void)
{
    gpio_write_low(&PORTB, PB5);
}

#endif
