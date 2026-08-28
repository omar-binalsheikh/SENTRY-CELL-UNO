#ifndef UART_H
#define UART_H

#include <stdint.h>

void uart_init(void);
void uart_write_byte(uint8_t byte);
void uart_write_string(const char *text);
uint8_t uart_tx_write(const uint8_t *data, uint8_t length);
uint8_t uart_read_byte(uint8_t *byte);
uint8_t uart_rx_overflow_count(void);

#endif
