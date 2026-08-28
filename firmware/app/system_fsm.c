#include "app/system_fsm.h"

static system_state_t g_system_state = SYSTEM_STATE_BOOT;

void system_fsm_init(void)
{
    g_system_state = SYSTEM_STATE_BOOT;
}

void system_fsm_handle_event(system_event_t event)
{
    switch (g_system_state) {
    case SYSTEM_STATE_BOOT:
        if (event == SYSTEM_EVENT_INIT_DONE) {
            g_system_state = SYSTEM_STATE_IDLE;
        }
        break;

    case SYSTEM_STATE_IDLE:
        if (event == SYSTEM_EVENT_START_STOP) {
            g_system_state = SYSTEM_STATE_ACTIVE;
        }
        break;

    case SYSTEM_STATE_ACTIVE:
        if (event == SYSTEM_EVENT_START_STOP) {
            g_system_state = SYSTEM_STATE_IDLE;
        } else if (event == SYSTEM_EVENT_CRITICAL_FAULT) {
            g_system_state = SYSTEM_STATE_SAFE_STATE;
        }
        break;

    case SYSTEM_STATE_SAFE_STATE:
    default:
        break;
    }
}

system_state_t system_fsm_get_state(void)
{
    return g_system_state;
}
