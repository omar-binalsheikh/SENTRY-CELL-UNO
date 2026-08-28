#ifndef CRC8_H
#define CRC8_H

#include <stdint.h>

uint8_t crc8_compute(const uint8_t *data, uint8_t length);

#endif
