#ifndef THERMISTOR_H
#define THERMISTOR_H

#include <stdint.h>

#include "hal/adc.h"

static inline void thermistor_init(void)
{
}

static inline uint16_t thermistor_read_raw(void)
{
    return adc_read(0U);
}

#endif
