#ifndef TIMING_PROFILER_H
#define TIMING_PROFILER_H

#include <stdint.h>

typedef enum {
    TIMING_TASK_ACTUATOR = 0,
    TIMING_TASK_CONTROL,
    TIMING_TASK_SENSOR_SAFETY,
    TIMING_TASK_COMMUNICATION,
    TIMING_TASK_COUNT
} timing_task_id_t;

void timing_profiler_init(void);
void timing_profiler_record(uint8_t task_id, uint16_t elapsed_ticks);
uint16_t timing_profiler_get_max_ticks(uint8_t task_id);
/* Maximum abs(start interval - nominal period), at 1 ms resolution. */
void timing_profiler_record_start(
    uint8_t task_id,
    uint32_t now_ms,
    uint16_t nominal_period_ms);
uint16_t timing_profiler_get_max_jitter_ms(uint8_t task_id);

#endif
