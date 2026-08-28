#ifndef SCHEDULER_H
#define SCHEDULER_H

#include <stdint.h>

#define SCHEDULER_MAX_TASKS 4U

typedef void (*scheduler_task_fn_t)(void);

void scheduler_init(void);
uint8_t scheduler_add_task(scheduler_task_fn_t task, uint32_t period_ms);
void scheduler_run(void);

#endif
