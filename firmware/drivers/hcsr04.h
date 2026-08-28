#ifndef HCSR04_H
#define HCSR04_H

#include <stdint.h>

void hcsr04_init(void);
uint8_t hcsr04_start(void);
uint8_t hcsr04_result_ready(void);
uint16_t hcsr04_get_pulse_ticks(void);
void hcsr04_abort(void);

#endif
