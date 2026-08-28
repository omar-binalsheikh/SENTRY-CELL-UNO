#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "diagnostics/diagnostics.h"

typedef uint8_t (*diagnostics_test_function_t)(void);

typedef struct {
    const char *name;
    diagnostics_test_function_t function;
} diagnostics_test_case_t;

static uint8_t test_initial_state(void)
{
    diagnostics_init();

    return ((diagnostics_get_last_fault() == DIAG_FAULT_NONE) &&
            (diagnostics_get_fault_count() == 0U))
               ? 1U
               : 0U;
}

static uint8_t test_none_is_ignored(void)
{
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_NONE);

    return ((diagnostics_get_last_fault() == DIAG_FAULT_NONE) &&
            (diagnostics_get_fault_count() == 0U))
               ? 1U
               : 0U;
}

static uint8_t test_fault_recording(void)
{
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);

    return ((diagnostics_get_last_fault() ==
             DIAG_FAULT_OBSTACLE_CRITICAL) &&
            (diagnostics_get_fault_count() == 1U))
               ? 1U
               : 0U;
}

static uint8_t test_last_fault_retention_across_reads(void)
{
    uint8_t index;

    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);

    for (index = 0U; index < 4U; ++index) {
        if (diagnostics_get_last_fault() !=
            DIAG_FAULT_OBSTACLE_CRITICAL) {
            return 0U;
        }
    }

    return (diagnostics_get_fault_count() == 1U) ? 1U : 0U;
}

static uint8_t test_fault_count_retention_across_reads(void)
{
    uint8_t index;

    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);

    for (index = 0U; index < 4U; ++index) {
        if (diagnostics_get_fault_count() != 1U) {
            return 0U;
        }
    }

    return (diagnostics_get_last_fault() ==
            DIAG_FAULT_OBSTACLE_CRITICAL)
               ? 1U
               : 0U;
}

static uint8_t test_duplicate_event_behavior(void)
{
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);

    return ((diagnostics_get_last_fault() ==
             DIAG_FAULT_OBSTACLE_CRITICAL) &&
            (diagnostics_get_fault_count() == 1U))
               ? 1U
               : 0U;
}

static uint8_t test_init_resets_state(void)
{
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);
    diagnostics_init();

    return ((diagnostics_get_last_fault() == DIAG_FAULT_NONE) &&
            (diagnostics_get_fault_count() == 0U))
               ? 1U
               : 0U;
}

static uint8_t test_new_event_after_reinit(void)
{
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);
    diagnostics_init();
    diagnostics_record_fault(DIAG_FAULT_OBSTACLE_CRITICAL);

    return ((diagnostics_get_last_fault() ==
             DIAG_FAULT_OBSTACLE_CRITICAL) &&
            (diagnostics_get_fault_count() == 1U))
               ? 1U
               : 0U;
}

int main(void)
{
    static const diagnostics_test_case_t cases[] = {
        {"initial state", test_initial_state},
        {"DIAG_FAULT_NONE ignored", test_none_is_ignored},
        {"fault recording", test_fault_recording},
        {"last-fault retention across reads",
         test_last_fault_retention_across_reads},
        {"fault-count retention across reads",
         test_fault_count_retention_across_reads},
        {"duplicate-event behavior", test_duplicate_event_behavior},
        {"init resets state", test_init_resets_state},
        {"new event after reinit", test_new_event_after_reinit},
    };
    size_t failure_count = 0U;
    size_t index;

    for (index = 0U; index < (sizeof(cases) / sizeof(cases[0])); ++index) {
        const uint8_t passed = cases[index].function();

        printf(
            "%s: %s\n",
            cases[index].name,
            (passed != 0U) ? "PASS" : "FAIL");

        if (passed == 0U) {
            ++failure_count;
        }
    }

    printf(
        "Diagnostics retention unit test: %s (%u cases, %u failures)\n",
        (failure_count == 0U) ? "PASS" : "FAIL",
        (unsigned int)(sizeof(cases) / sizeof(cases[0])),
        (unsigned int)failure_count);

    return (failure_count == 0U) ? 0 : 1;
}
