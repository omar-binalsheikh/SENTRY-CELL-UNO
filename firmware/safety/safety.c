#include "safety/safety.h"

#define SAFETY_OBSTACLE_THRESHOLD_CM 20U

uint8_t safety_obstacle_is_critical(uint8_t valid, uint16_t distance_cm)
{
    if ((valid != 0U) && (distance_cm > 0U) &&
        (distance_cm <= SAFETY_OBSTACLE_THRESHOLD_CM)) {
        return 1U;
    }

    return 0U;
}
