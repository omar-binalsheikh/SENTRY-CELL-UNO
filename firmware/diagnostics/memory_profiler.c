#include "diagnostics/memory_profiler.h"

#include <avr/io.h>
#include <stdint.h>

#define MEMORY_CANARY 0xA5U
#define MEMORY_STACK_GUARD_BYTES 32U

extern uint8_t __heap_start;

static uint16_t g_painted_bytes;
static uint16_t g_min_free_bytes;

void memory_profiler_init(void)
{
    uint8_t *const paint_start = &__heap_start;
    const uint16_t paint_start_address = (uint16_t)(uintptr_t)paint_start;
    const uint16_t stack_pointer = (uint16_t)SP;
    uint16_t available_bytes;
    uint16_t offset;

    g_painted_bytes = 0U;
    g_min_free_bytes = 0U;

    if ((paint_start_address < RAMSTART) ||
        (stack_pointer > RAMEND) ||
        (stack_pointer <= paint_start_address)) {
        return;
    }

    available_bytes = (uint16_t)(stack_pointer - paint_start_address);

    if (available_bytes <= MEMORY_STACK_GUARD_BYTES) {
        return;
    }

    g_painted_bytes =
        (uint16_t)(available_bytes - MEMORY_STACK_GUARD_BYTES);
    g_min_free_bytes = g_painted_bytes;

    for (offset = 0U; offset < g_painted_bytes; offset++) {
        paint_start[offset] = MEMORY_CANARY;
    }
}

uint16_t memory_profiler_get_min_free_bytes(void)
{
    const volatile uint8_t *const paint_start = &__heap_start;
    uint16_t free_bytes = 0U;

    while ((free_bytes < g_painted_bytes) &&
           (paint_start[free_bytes] == MEMORY_CANARY)) {
        free_bytes++;
    }

    if (free_bytes < g_min_free_bytes) {
        g_min_free_bytes = free_bytes;
    }

    return g_min_free_bytes;
}

uint16_t memory_profiler_get_painted_bytes(void)
{
    return g_painted_bytes;
}

uint16_t memory_profiler_get_used_painted_bytes(void)
{
    return (uint16_t)(g_painted_bytes - g_min_free_bytes);
}
