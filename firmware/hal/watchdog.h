#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <stdbool.h>
#include <stdint.h>

uint8_t watchdog_get_reset_cause(void);
bool watchdog_previous_timeout_detected(void);
void watchdog_enable(void);
void watchdog_kick(void);

#endif
