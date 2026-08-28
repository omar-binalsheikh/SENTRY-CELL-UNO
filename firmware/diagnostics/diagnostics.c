#include "diagnostics/diagnostics.h"

static diag_fault_t g_last_fault = DIAG_FAULT_NONE;
static uint16_t g_fault_count = 0U;

void diagnostics_init(void)
{
    g_last_fault = DIAG_FAULT_NONE;
    g_fault_count = 0U;
}

void diagnostics_record_fault(diag_fault_t fault)
{
    if ((fault == DIAG_FAULT_NONE) || (fault == g_last_fault)) {
        return;
    }

    g_last_fault = fault;
    g_fault_count++;
}

diag_fault_t diagnostics_get_last_fault(void)
{
    return g_last_fault;
}

uint16_t diagnostics_get_fault_count(void)
{
    return g_fault_count;
}
