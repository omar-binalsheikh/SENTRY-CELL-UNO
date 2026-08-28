#include "scheduler/scheduler.h"

#include <stddef.h>

#include "hal/system_time.h"

typedef struct {
    scheduler_task_fn_t task;
    uint32_t period_ms;
    uint32_t last_run_ms;
    uint8_t active;
} scheduler_task_t;

static scheduler_task_t g_tasks[SCHEDULER_MAX_TASKS];

void scheduler_init(void)
{
    uint8_t index;

    for (index = 0U; index < SCHEDULER_MAX_TASKS; index++) {
        g_tasks[index].task = NULL;
        g_tasks[index].period_ms = 0U;
        g_tasks[index].last_run_ms = 0U;
        g_tasks[index].active = 0U;
    }
}

uint8_t scheduler_add_task(scheduler_task_fn_t task, uint32_t period_ms)
{
    uint8_t index;

    if ((task == NULL) || (period_ms == 0U)) {
        return 0U;
    }

    for (index = 0U; index < SCHEDULER_MAX_TASKS; index++) {
        if (g_tasks[index].active == 0U) {
            g_tasks[index].task = task;
            g_tasks[index].period_ms = period_ms;
            g_tasks[index].last_run_ms = system_time_ms();
            g_tasks[index].active = 1U;
            return 1U;
        }
    }

    return 0U;
}

void scheduler_run(void)
{
    const uint32_t now = system_time_ms();
    uint8_t index;

    for (index = 0U; index < SCHEDULER_MAX_TASKS; index++) {
        scheduler_task_t *const task = &g_tasks[index];

        if ((task->active != 0U) &&
            ((uint32_t)(now - task->last_run_ms) >= task->period_ms)) {
            task->last_run_ms = now;
            task->task();
        }
    }
}
