#ifndef SENTRY_CELL_GPIO_H
#define SENTRY_CELL_GPIO_H

#include <stdint.h>

static inline void gpio_set_output(volatile uint8_t *ddr, uint8_t bit)
{
    *ddr |= (uint8_t)(1U << bit);
}

static inline void gpio_set_input_pullup(volatile uint8_t *ddr,
                                         volatile uint8_t *port,
                                         uint8_t bit)
{
    *ddr &= (uint8_t)~(1U << bit);
    *port |= (uint8_t)(1U << bit);
}

static inline void gpio_write_high(volatile uint8_t *port, uint8_t bit)
{
    *port |= (uint8_t)(1U << bit);
}

static inline void gpio_write_low(volatile uint8_t *port, uint8_t bit)
{
    *port &= (uint8_t)~(1U << bit);
}

static inline uint8_t gpio_read(volatile uint8_t *pin, uint8_t bit)
{
    return ((*pin & (uint8_t)(1U << bit)) != 0U) ? 1U : 0U;
}

#endif
