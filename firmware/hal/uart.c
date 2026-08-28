#include "hal/uart.h"

#include <avr/interrupt.h>
#include <avr/io.h>
#include <stddef.h>

#define UART_UBRR_VALUE 103U
#define UART_RX_BUFFER_SIZE 32U
#define UART_RX_BUFFER_MASK (UART_RX_BUFFER_SIZE - 1U)
#define UART_TX_BUFFER_SIZE 64U
#define UART_TX_BUFFER_MASK 63U

#if ((UART_RX_BUFFER_SIZE & UART_RX_BUFFER_MASK) != 0U)
#error "UART_RX_BUFFER_SIZE must be a power of two"
#endif

#if ((UART_TX_BUFFER_SIZE & UART_TX_BUFFER_MASK) != 0U)
#error "UART_TX_BUFFER_SIZE must be a power of two"
#endif

static volatile uint8_t rx_buffer[UART_RX_BUFFER_SIZE];
static volatile uint8_t rx_head;
static volatile uint8_t rx_tail;
static volatile uint8_t rx_overflow_count;
/* Main produces tx_head; USART_UDRE_vect consumes tx_tail. */
/* Volatile uint8_t index accesses are atomic on ATmega328P. */
static volatile uint8_t tx_buffer[UART_TX_BUFFER_SIZE];
static volatile uint8_t tx_head;
static volatile uint8_t tx_tail;

ISR(USART_RX_vect)
{
    uint8_t byte;
    uint8_t head;
    uint8_t next_head;

    byte = UDR0;
    head = rx_head;
    next_head = (uint8_t)((head + 1U) & UART_RX_BUFFER_MASK);

    if (next_head != rx_tail) {
        rx_buffer[head] = byte;
        rx_head = next_head;
    } else if (rx_overflow_count != UINT8_MAX) {
        rx_overflow_count++;
    }
}

ISR(USART_UDRE_vect)
{
    uint8_t tail;

    tail = tx_tail;

    if (tx_head != tail) {
        UDR0 = tx_buffer[tail];
        tx_tail = (uint8_t)((tail + 1U) & UART_TX_BUFFER_MASK);
    } else {
        UCSR0B &= (uint8_t)~(1U << UDRIE0);
    }
}

void uart_init(void)
{
    rx_head = 0U;
    rx_tail = 0U;
    rx_overflow_count = 0U;
    tx_head = 0U;
    tx_tail = 0U;

    UBRR0H = (uint8_t)(UART_UBRR_VALUE >> 8U);
    UBRR0L = (uint8_t)UART_UBRR_VALUE;

    UCSR0A = 0U;
    UCSR0B = (uint8_t)((1U << TXEN0) | (1U << RXEN0) | (1U << RXCIE0));
    UCSR0C = (uint8_t)((1U << UCSZ01) | (1U << UCSZ00));
}

void uart_write_byte(uint8_t byte)
{
    while ((UCSR0A & (uint8_t)(1U << UDRE0)) == 0U) {
    }

    UDR0 = byte;
}

void uart_write_string(const char *text)
{
    while (*text != '\0') {
        uart_write_byte((uint8_t)*text);
        text++;
    }
}

uint8_t uart_tx_write(const uint8_t *data, uint8_t length)
{
    uint8_t head;
    uint8_t tail;
    uint8_t used;
    uint8_t free_space;
    uint8_t index;

    if (length == 0U) {
        return 1U;
    }

    if (data == NULL) {
        return 0U;
    }

    head = tx_head;
    tail = tx_tail;
    used = (uint8_t)((head - tail) & UART_TX_BUFFER_MASK);
    free_space = (uint8_t)(UART_TX_BUFFER_MASK - used);

    if (length > free_space) {
        return 0U;
    }

    for (index = 0U; index < length; index++) {
        tx_buffer[head] = data[index];
        head = (uint8_t)((head + 1U) & UART_TX_BUFFER_MASK);
    }

    tx_head = head;
    UCSR0B |= (uint8_t)(1U << UDRIE0);
    return 1U;
}

uint8_t uart_read_byte(uint8_t *byte)
{
    uint8_t tail;

    if (byte == NULL) {
        return 0U;
    }

    if (rx_head == rx_tail) {
        return 0U;
    }

    tail = rx_tail;
    *byte = rx_buffer[tail];
    rx_tail = (uint8_t)((tail + 1U) & UART_RX_BUFFER_MASK);
    return 1U;
}

uint8_t uart_rx_overflow_count(void)
{
    return rx_overflow_count;
}
