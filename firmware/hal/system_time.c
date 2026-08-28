#include "hal/system_time.h"

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>

static volatile uint32_t g_system_ms = 0U;

ISR(TIMER2_COMPA_vect)
{
    g_system_ms++;
}

void system_time_init(void)
{
    g_system_ms = 0U;

    TCCR2A = 0U;
    TCCR2B = 0U;
    TIMSK2 = 0U;
    TCNT2 = 0U;

    OCR2A = 249U;
    TCCR2A = (uint8_t)(1U << WGM21);
    TIFR2 = (uint8_t)(1U << OCF2A);
    TIMSK2 = (uint8_t)(1U << OCIE2A);
    TCCR2B = (uint8_t)(1U << CS22);
}

uint32_t system_time_ms(void)
{
    uint32_t system_ms;

    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        system_ms = g_system_ms;
    }

    return system_ms;
}
