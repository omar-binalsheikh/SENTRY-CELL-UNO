MCU := atmega328p
F_CPU := 16000000UL
CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size
AVRDUDE := avrdude
PROGRAMMER := arduino
BAUD := 115200

CPPFLAGS := -Ifirmware
CFLAGS := -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Os -std=c11 -Wall -Wextra -Werror
LDFLAGS := -mmcu=$(MCU)

BUILD_DIR := build
MAP := $(BUILD_DIR)/sentry-cell-uno.map
LDFLAGS += -Wl,-Map=$(MAP)
MAIN_SOURCE := firmware/main.c
SYSTEM_TIME_SOURCE := firmware/hal/system_time.c
TIMING_SOURCE := firmware/hal/timing.c
SCHEDULER_SOURCE := firmware/scheduler/scheduler.c
ADC_SOURCE := firmware/hal/adc.c
HCSR04_SOURCE := firmware/drivers/hcsr04.c
STEPPER_SOURCE := firmware/drivers/stepper.c
SERVO_SOURCE := firmware/drivers/servo.c
DC_MOTOR_SOURCE := firmware/drivers/dc_motor.c
RELAY_SOURCE := firmware/drivers/relay.c
SYSTEM_FSM_SOURCE := firmware/app/system_fsm.c
SAFETY_SOURCE := firmware/safety/safety.c
DIAGNOSTICS_SOURCE := firmware/diagnostics/diagnostics.c
TIMING_PROFILER_SOURCE := firmware/diagnostics/timing_profiler.c
MEMORY_PROFILER_SOURCE := firmware/diagnostics/memory_profiler.c
RUNTIME_PROFILER_SOURCE := firmware/diagnostics/runtime_profiler.c
UART_SOURCE := firmware/hal/uart.c
WATCHDOG_SOURCE := firmware/hal/watchdog.c
CRC8_SOURCE := firmware/protocol/crc8.c
PROTOCOL_SOURCE := firmware/protocol/protocol.c
MAIN_OBJECT := $(BUILD_DIR)/main.o
SYSTEM_TIME_OBJECT := $(BUILD_DIR)/system_time.o
TIMING_OBJECT := $(BUILD_DIR)/timing.o
SCHEDULER_OBJECT := $(BUILD_DIR)/scheduler.o
ADC_OBJECT := $(BUILD_DIR)/adc.o
HCSR04_OBJECT := $(BUILD_DIR)/hcsr04.o
STEPPER_OBJECT := $(BUILD_DIR)/stepper.o
SERVO_OBJECT := $(BUILD_DIR)/servo.o
DC_MOTOR_OBJECT := $(BUILD_DIR)/dc_motor.o
RELAY_OBJECT := $(BUILD_DIR)/relay.o
SYSTEM_FSM_OBJECT := $(BUILD_DIR)/system_fsm.o
SAFETY_OBJECT := $(BUILD_DIR)/safety.o
DIAGNOSTICS_OBJECT := $(BUILD_DIR)/diagnostics.o
TIMING_PROFILER_OBJECT := $(BUILD_DIR)/timing_profiler.o
MEMORY_PROFILER_OBJECT := $(BUILD_DIR)/memory_profiler.o
RUNTIME_PROFILER_OBJECT := $(BUILD_DIR)/runtime_profiler.o
UART_OBJECT := $(BUILD_DIR)/uart.o
WATCHDOG_OBJECT := $(BUILD_DIR)/watchdog.o
CRC8_OBJECT := $(BUILD_DIR)/crc8.o
PROTOCOL_OBJECT := $(BUILD_DIR)/protocol.o
OBJECTS := $(MAIN_OBJECT) $(SYSTEM_TIME_OBJECT) $(TIMING_OBJECT) \
	$(SCHEDULER_OBJECT) \
	$(ADC_OBJECT) $(HCSR04_OBJECT) $(STEPPER_OBJECT) $(SERVO_OBJECT) \
	$(DC_MOTOR_OBJECT) $(RELAY_OBJECT) $(SYSTEM_FSM_OBJECT) $(SAFETY_OBJECT) \
	$(DIAGNOSTICS_OBJECT) $(TIMING_PROFILER_OBJECT) \
	$(MEMORY_PROFILER_OBJECT) $(RUNTIME_PROFILER_OBJECT) $(UART_OBJECT) \
	$(WATCHDOG_OBJECT) $(CRC8_OBJECT) $(PROTOCOL_OBJECT)
ELF := $(BUILD_DIR)/sentry-cell-uno.elf
HEX := $(BUILD_DIR)/sentry-cell-uno.hex

MAIN_HEADERS := firmware/app/system_fsm.h \
	firmware/diagnostics/diagnostics.h \
	firmware/diagnostics/memory_profiler.h \
	firmware/diagnostics/runtime_profiler.h \
	firmware/diagnostics/timing_profiler.h \
	firmware/drivers/button.h firmware/drivers/dc_motor.h \
	firmware/drivers/hcsr04.h firmware/drivers/led.h \
	firmware/drivers/relay.h firmware/drivers/servo.h \
	firmware/drivers/stepper.h firmware/drivers/thermistor.h \
	firmware/hal/adc.h firmware/hal/system_time.h \
	firmware/hal/timing.h firmware/hal/uart.h \
	firmware/hal/watchdog.h \
	firmware/protocol/protocol.h \
	firmware/safety/safety.h \
	firmware/scheduler/scheduler.h

.PHONY: all size upload clean

all: $(ELF) $(HEX)

$(BUILD_DIR):
	mkdir -p $@

$(MAIN_OBJECT): $(MAIN_SOURCE) $(MAIN_HEADERS) | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(SYSTEM_TIME_OBJECT): $(SYSTEM_TIME_SOURCE) firmware/hal/system_time.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(TIMING_OBJECT): $(TIMING_SOURCE) firmware/hal/timing.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(SCHEDULER_OBJECT): $(SCHEDULER_SOURCE) firmware/scheduler/scheduler.h firmware/hal/system_time.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(ADC_OBJECT): $(ADC_SOURCE) firmware/hal/adc.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(HCSR04_OBJECT): $(HCSR04_SOURCE) firmware/drivers/hcsr04.h firmware/hal/gpio.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(STEPPER_OBJECT): $(STEPPER_SOURCE) firmware/drivers/stepper.h firmware/hal/gpio.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(SERVO_OBJECT): $(SERVO_SOURCE) firmware/drivers/servo.h firmware/hal/gpio.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(DC_MOTOR_OBJECT): $(DC_MOTOR_SOURCE) firmware/drivers/dc_motor.h firmware/hal/gpio.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(RELAY_OBJECT): $(RELAY_SOURCE) firmware/drivers/relay.h firmware/hal/gpio.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(SYSTEM_FSM_OBJECT): $(SYSTEM_FSM_SOURCE) firmware/app/system_fsm.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(SAFETY_OBJECT): $(SAFETY_SOURCE) firmware/safety/safety.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(DIAGNOSTICS_OBJECT): $(DIAGNOSTICS_SOURCE) firmware/diagnostics/diagnostics.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(TIMING_PROFILER_OBJECT): $(TIMING_PROFILER_SOURCE) firmware/diagnostics/timing_profiler.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(MEMORY_PROFILER_OBJECT): $(MEMORY_PROFILER_SOURCE) firmware/diagnostics/memory_profiler.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(RUNTIME_PROFILER_OBJECT): $(RUNTIME_PROFILER_SOURCE) firmware/diagnostics/runtime_profiler.h firmware/diagnostics/timing_profiler.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(UART_OBJECT): $(UART_SOURCE) firmware/hal/uart.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(WATCHDOG_OBJECT): $(WATCHDOG_SOURCE) firmware/hal/watchdog.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(CRC8_OBJECT): $(CRC8_SOURCE) firmware/protocol/crc8.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(PROTOCOL_OBJECT): $(PROTOCOL_SOURCE) firmware/protocol/protocol.h \
		firmware/protocol/crc8.h firmware/hal/uart.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

$(HEX): $(ELF)
	$(OBJCOPY) -O ihex -R .eeprom $< $@

size: $(ELF)
	$(SIZE) $<

upload: $(HEX)
	@if [ -z "$(strip $(PORT))" ]; then \
		printf '%s\n' 'ERROR: PORT is required. Usage: make upload PORT=/dev/cu.<device>'; \
		exit 1; \
	fi
	$(AVRDUDE) -p $(MCU) -c $(PROGRAMMER) -P $(PORT) -b $(BAUD) -D -U flash:w:$(HEX):i

clean:
	if [ -d "$(BUILD_DIR)" ]; then rm -r "$(BUILD_DIR)"; fi
