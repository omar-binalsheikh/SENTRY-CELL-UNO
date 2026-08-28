#include "drivers/relay.h"

#include <avr/io.h>

#include "hal/gpio.h"

#define RELAY_CONTROL_BIT PB3

void relay_init(void)
{
    gpio_set_output(&DDRB, RELAY_CONTROL_BIT);
    relay_off();
}

void relay_on(void)
{
    gpio_write_high(&PORTB, RELAY_CONTROL_BIT);
}

void relay_off(void)
{
    gpio_write_low(&PORTB, RELAY_CONTROL_BIT);
}
