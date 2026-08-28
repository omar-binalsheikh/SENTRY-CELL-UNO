#ifndef RUNTIME_PROFILER_H
#define RUNTIME_PROFILER_H

#include <stdint.h>

#include "diagnostics/timing_profiler.h"

/* Task IDs are the existing TIMING_TASK_* identifiers. */
void runtime_profiler_init(uint32_t now_ms);
void runtime_profiler_record_execution(
    uint8_t task_id,
    uint16_t elapsed_ticks,
    uint16_t nominal_period_ms);
uint32_t runtime_profiler_get_busy_ticks(void);
uint32_t runtime_profiler_get_elapsed_ms(uint32_t now_ms);
uint16_t runtime_profiler_get_overrun_count(uint8_t task_id);

#endif
