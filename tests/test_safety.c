#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "safety/safety.h"

/*
 * The software boundary is evaluated on the integer distance_cm value passed
 * to the Safety module. The observed physical switching boundary of
 * approximately 21.8--22.0 cm is a sensor/system measurement characteristic,
 * not evidence of centimetre-level calibration.
 *
 * Physical characterization supplied for traceability:
 *   25 cm: ACTIVE x3; 22 cm: ACTIVE x3;
 *   21 cm, 20 cm, 19 cm, 18 cm: SAFE x3 each;
 *   21.2--21.8 cm: SAFE; 22.0--22.1 cm: ACTIVE.
 */

typedef struct {
    const char *name;
    uint8_t valid;
    uint16_t distance_cm;
    uint8_t expected_critical;
} safety_test_case_t;

int main(void)
{
    static const safety_test_case_t cases[] = {
        {"invalid input at 0 cm", 0U, 0U, 0U},
        {"invalid input at 20 cm", 0U, 20U, 0U},
        {"valid input at 0 cm", 1U, 0U, 0U},
        {"valid input at 1 cm", 1U, 1U, 1U},
        {"valid input at 19 cm", 1U, 19U, 1U},
        {"valid input at 20 cm", 1U, 20U, 1U},
        {"valid input at 21 cm", 1U, 21U, 0U},
        {"valid input at 65535 cm", 1U, UINT16_MAX, 0U},
    };
    size_t failure_count = 0U;
    size_t index;

    for (index = 0U; index < (sizeof(cases) / sizeof(cases[0])); ++index) {
        const uint8_t actual = safety_obstacle_is_critical(
            cases[index].valid, cases[index].distance_cm);
        const uint8_t passed =
            (actual == cases[index].expected_critical) ? 1U : 0U;

        printf(
            "%s: %s (valid=%u, distance=%u, expected=%u, actual=%u)\n",
            cases[index].name,
            (passed != 0U) ? "PASS" : "FAIL",
            (unsigned int)cases[index].valid,
            (unsigned int)cases[index].distance_cm,
            (unsigned int)cases[index].expected_critical,
            (unsigned int)actual);

        if (passed == 0U) {
            ++failure_count;
        }
    }

    printf(
        "Safety boundary unit test: %s (%u cases, %u failures)\n",
        (failure_count == 0U) ? "PASS" : "FAIL",
        (unsigned int)(sizeof(cases) / sizeof(cases[0])),
        (unsigned int)failure_count);

    return (failure_count == 0U) ? 0 : 1;
}
