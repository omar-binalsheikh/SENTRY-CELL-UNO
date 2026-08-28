#include "drivers/dc_motor.h"

#include <avr/io.h>

#include "hal/gpio.h"

#define DC_MOTOR_IN1_BIT PB2
#define DC_MOTOR_IN2_BIT PB4

void dc_motor_init(void)
{
    gpio_set_output(&DDRB, DC_MOTOR_IN1_BIT);
    gpio_set_output(&DDRB, DC_MOTOR_IN2_BIT);
    dc_motor_stop();
}

void dc_motor_forward(void)
{
    gpio_write_high(&PORTB, DC_MOTOR_IN1_BIT);
    gpio_write_low(&PORTB, DC_MOTOR_IN2_BIT);
}

void dc_motor_reverse(void)
{
    gpio_write_low(&PORTB, DC_MOTOR_IN1_BIT);
    gpio_write_high(&PORTB, DC_MOTOR_IN2_BIT);
}

void dc_motor_stop(void)
{
    gpio_write_low(&PORTB, DC_MOTOR_IN1_BIT);
    gpio_write_low(&PORTB, DC_MOTOR_IN2_BIT);
}
