#include "diagnostics/runtime_profiler.h"

#define TIMER1_TICKS_PER_MS 2000UL

static uint32_t g_busy_ticks;
static uint32_t g_start_ms;
static uint16_t g_overrun_count[TIMING_TASK_COUNT];

void runtime_profiler_init(uint32_t now_ms)
{
    uint8_t task_id;

    g_busy_ticks = 0U;
    g_start_ms = now_ms;

    for (task_id = 0U; task_id < TIMING_TASK_COUNT; task_id++) {
        g_overrun_count[task_id] = 0U;
    }
}

void runtime_profiler_record_execution(
    uint8_t task_id,
    uint16_t elapsed_ticks,
    uint16_t nominal_period_ms)
{
    const uint32_t period_ticks =
        (uint32_t)nominal_period_ms * TIMER1_TICKS_PER_MS;

    if (task_id >= TIMING_TASK_COUNT) {
        return;
    }

    if ((UINT32_MAX - g_busy_ticks) < elapsed_ticks) {
        g_busy_ticks = UINT32_MAX;
    } else {
        g_busy_ticks += elapsed_ticks;
    }

    if (((uint32_t)elapsed_ticks > period_ticks) &&
        (g_overrun_count[task_id] != UINT16_MAX)) {
        g_overrun_count[task_id]++;
    }
}

uint32_t runtime_profiler_get_busy_ticks(void)
{
    return g_busy_ticks;
}

uint32_t runtime_profiler_get_elapsed_ms(uint32_t now_ms)
{
    return (uint32_t)(now_ms - g_start_ms);
}

uint16_t runtime_profiler_get_overrun_count(uint8_t task_id)
{
    if (task_id >= TIMING_TASK_COUNT) {
        return 0U;
    }

    return g_overrun_count[task_id];
}
