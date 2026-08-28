#ifndef SYSTEM_FSM_H
#define SYSTEM_FSM_H

typedef enum {
    SYSTEM_STATE_BOOT = 0,
    SYSTEM_STATE_IDLE,
    SYSTEM_STATE_ACTIVE,
    SYSTEM_STATE_SAFE_STATE
} system_state_t;

typedef enum {
    SYSTEM_EVENT_INIT_DONE = 0,
    SYSTEM_EVENT_START_STOP,
    SYSTEM_EVENT_CRITICAL_FAULT
} system_event_t;

void system_fsm_init(void);
void system_fsm_handle_event(system_event_t event);
system_state_t system_fsm_get_state(void);

#endif
