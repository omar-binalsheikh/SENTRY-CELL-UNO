#ifndef SAFETY_H
#define SAFETY_H

#include <stdint.h>

uint8_t safety_obstacle_is_critical(uint8_t valid, uint16_t distance_cm);

#endif
