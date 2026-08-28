#ifndef MEMORY_PROFILER_H
#define MEMORY_PROFILER_H

#include <stdint.h>

/* Empirical observed minimum free SRAM watermark; not a worst-case bound. */
void memory_profiler_init(void);
uint16_t memory_profiler_get_min_free_bytes(void);
uint16_t memory_profiler_get_painted_bytes(void);
uint16_t memory_profiler_get_used_painted_bytes(void);

#endif
