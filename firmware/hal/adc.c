#include "hal/adc.h"

#include <avr/io.h>

#define ADC_CHANNEL_MASK 0x07U
#define ADC_ADMUX_CONTROL_MASK 0xF0U

void adc_init(void)
{
    ADMUX = (uint8_t)(1U << REFS0);
    ADCSRA = (uint8_t)((1U << ADEN) |
                       (1U << ADPS2) |
                       (1U << ADPS1) |
                       (1U << ADPS0));
}

uint16_t adc_read(uint8_t channel)
{
    ADMUX = (uint8_t)((ADMUX & ADC_ADMUX_CONTROL_MASK) |
                      (channel & ADC_CHANNEL_MASK));

    ADCSRA |= (uint8_t)(1U << ADSC);

    while ((ADCSRA & (uint8_t)(1U << ADSC)) != 0U) {
    }

    return ADC;
}
