#include "hal/timing.h"

#include <avr/io.h>

uint16_t timing_counter_ticks(void)
{
    return TCNT1;
}
