#include "diagnostics/timing_profiler.h"

static uint16_t g_max_ticks[TIMING_TASK_COUNT];
static uint32_t g_last_start_ms[TIMING_TASK_COUNT];
static uint16_t g_max_jitter_ms[TIMING_TASK_COUNT];
static uint8_t g_has_start_sample[TIMING_TASK_COUNT];

void timing_profiler_init(void)
{
    uint8_t task_id;

    for (task_id = 0U; task_id < TIMING_TASK_COUNT; task_id++) {
        g_max_ticks[task_id] = 0U;
        g_last_start_ms[task_id] = 0U;
        g_max_jitter_ms[task_id] = 0U;
        g_has_start_sample[task_id] = 0U;
    }
}

void timing_profiler_record(uint8_t task_id, uint16_t elapsed_ticks)
{
    if ((task_id < TIMING_TASK_COUNT) &&
        (elapsed_ticks > g_max_ticks[task_id])) {
        g_max_ticks[task_id] = elapsed_ticks;
    }
}

uint16_t timing_profiler_get_max_ticks(uint8_t task_id)
{
    if (task_id >= TIMING_TASK_COUNT) {
        return 0U;
    }

    return g_max_ticks[task_id];
}

void timing_profiler_record_start(
    uint8_t task_id,
    uint32_t now_ms,
    uint16_t nominal_period_ms)
{
    uint32_t actual_interval_ms;
    uint32_t jitter_ms;
    uint16_t bounded_jitter_ms;

    if (task_id >= TIMING_TASK_COUNT) {
        return;
    }

    if (g_has_start_sample[task_id] == 0U) {
        g_last_start_ms[task_id] = now_ms;
        g_has_start_sample[task_id] = 1U;
        return;
    }

    actual_interval_ms =
        (uint32_t)(now_ms - g_last_start_ms[task_id]);

    if (actual_interval_ms >= nominal_period_ms) {
        jitter_ms = actual_interval_ms - nominal_period_ms;
    } else {
        jitter_ms = nominal_period_ms - actual_interval_ms;
    }

    if (jitter_ms > UINT16_MAX) {
        bounded_jitter_ms = UINT16_MAX;
    } else {
        bounded_jitter_ms = (uint16_t)jitter_ms;
    }

    if (bounded_jitter_ms > g_max_jitter_ms[task_id]) {
        g_max_jitter_ms[task_id] = bounded_jitter_ms;
    }

    g_last_start_ms[task_id] = now_ms;
}

uint16_t timing_profiler_get_max_jitter_ms(uint8_t task_id)
{
    if (task_id >= TIMING_TASK_COUNT) {
        return 0U;
    }

    return g_max_jitter_ms[task_id];
}
