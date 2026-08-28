#include "hal/watchdog.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <avr/wdt.h>

#define WATCHDOG_EVENT_MAGIC_A 0xA5U
#define WATCHDOG_EVENT_MAGIC_B 0x5AU

static uint8_t reset_cause __attribute__((section(".noinit")));
static uint8_t watchdog_event_magic_a __attribute__((section(".noinit")));
static uint8_t watchdog_event_magic_b __attribute__((section(".noinit")));
static uint8_t previous_timeout_detected
    __attribute__((section(".noinit")));

static void watchdog_capture_optiboot_reset_cause(void)
    __attribute__((naked, used, section(".init0")));

static void watchdog_capture_optiboot_reset_cause(void)
{
    __asm__ __volatile__(
        "sts %0, r2\n\t"
        "lds r24, %1\n\t"
        "cpi r24, %4\n\t"
        "brne 1f\n\t"
        "lds r24, %2\n\t"
        "cpi r24, %5\n\t"
        "brne 1f\n\t"
        "ldi r24, 1\n\t"
        "rjmp 2f\n"
        "1:\n\t"
        "clr r24\n"
        "2:\n\t"
        "sts %3, r24\n\t"
        "clr r24\n\t"
        "sts %1, r24\n\t"
        "sts %2, r24\n"
        : "=m"(reset_cause),
          "+m"(watchdog_event_magic_a),
          "+m"(watchdog_event_magic_b),
          "=m"(previous_timeout_detected)
        : "M"(WATCHDOG_EVENT_MAGIC_A),
          "M"(WATCHDOG_EVENT_MAGIC_B)
        : "r24");
}

static void watchdog_disable_early(void)
    __attribute__((naked, used, section(".init3")));

static void watchdog_disable_early(void)
{
    MCUSR = 0U;
    wdt_disable();
}

uint8_t watchdog_get_reset_cause(void)
{
    return reset_cause;
}

bool watchdog_previous_timeout_detected(void)
{
    return previous_timeout_detected != 0U;
}

void watchdog_enable(void)
{
    const uint8_t saved_sreg = SREG;

    cli();
    wdt_reset();
    MCUSR &= (uint8_t)~(1U << WDRF);
    WDTCSR = (uint8_t)((1U << WDCE) | (1U << WDE));
    WDTCSR =
        (uint8_t)((1U << WDIE) | (1U << WDE) |
                  (1U << WDP2) | (1U << WDP1));
    SREG = saved_sreg;
}

void watchdog_kick(void)
{
    wdt_reset();
}

ISR(WDT_vect)
{
    watchdog_event_magic_a = WATCHDOG_EVENT_MAGIC_A;
    watchdog_event_magic_b = WATCHDOG_EVENT_MAGIC_B;
}
