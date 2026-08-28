#ifndef SERVO_H
#define SERVO_H

#include <stdint.h>

void servo_init(void);
void servo_set_pulse_ms(uint8_t pulse_ms);
void servo_service_1ms(void);
void servo_stop(void);

#endif
