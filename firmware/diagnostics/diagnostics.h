#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include <stdint.h>

typedef enum {
    DIAG_FAULT_NONE = 0,
    DIAG_FAULT_OBSTACLE_CRITICAL = 1
} diag_fault_t;

void diagnostics_init(void);
void diagnostics_record_fault(diag_fault_t fault);
diag_fault_t diagnostics_get_last_fault(void);
uint16_t diagnostics_get_fault_count(void);

#endif
