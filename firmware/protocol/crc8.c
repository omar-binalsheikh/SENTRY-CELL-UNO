#include "protocol/crc8.h"

#include <stddef.h>

#define CRC8_POLYNOMIAL 0x07U

uint8_t crc8_compute(const uint8_t *data, uint8_t length)
{
    uint8_t crc = 0U;
    uint8_t byte_index;
    uint8_t bit_index;

    if ((data == NULL) && (length != 0U)) {
        return 0U;
    }

    for (byte_index = 0U; byte_index < length; byte_index++) {
        crc ^= data[byte_index];

        for (bit_index = 0U; bit_index < 8U; bit_index++) {
            if ((crc & 0x80U) != 0U) {
                crc = (uint8_t)((crc << 1U) ^ CRC8_POLYNOMIAL);
            } else {
                crc = (uint8_t)(crc << 1U);
            }
        }
    }

    return crc;
}
