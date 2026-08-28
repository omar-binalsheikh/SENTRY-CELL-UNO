# SENTRY-CELL UNO — Binary UART Protocol

## 1. Scope

This document describes the binary serial protocol implemented by the current
ATmega328P firmware and Python Supervisor. The authoritative implementation is
in `firmware/protocol/`, `firmware/hal/uart.c`, and `supervisor/protocol.py`.
Only behavior present in those sources is documented here.

## 2. Physical and serial layer

| Parameter | Implemented value |
|---|---|
| MCU peripheral | USART0 |
| MCU clock | 16 MHz |
| UART mode | Asynchronous normal mode |
| Baud rate | 9600 baud (`UBRR0 = 103`) |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |
| Receiver | Enabled; `USART_RX_vect` interrupt |
| Transmitter | Enabled; `USART_UDRE_vect` interrupt used for queued protocol TX |
| RX storage | 32 bytes, 31 usable bytes |
| TX storage | 64 bytes, 63 usable bytes |

Each ring reserves one slot to distinguish full from empty. The RX ISR reads one
byte from `UDR0` and attempts to enqueue it. The TX Data Register Empty ISR sends
one queued byte and disables its interrupt when the ring is empty.

The HAL retains polling `uart_write_byte()` and `uart_write_string()` APIs, but
the integrated binary protocol uses `uart_tx_write()` and the interrupt-driven
TX ring. RX consumption by `communication_task` is non-blocking.

## 3. Frame format

```text
SOF | VERSION | TYPE | SEQUENCE | LENGTH | PAYLOAD | CRC
```

| Offset | Field | Size | Implemented meaning |
|---:|---|---:|---|
| 0 | `SOF` | 1 byte | Start delimiter, always `0xA5` |
| 1 | `VERSION` | 1 byte | Protocol version, always `0x01` |
| 2 | `TYPE` | 1 byte | Request or response type identifier |
| 3 | `SEQUENCE` | 1 byte | Host-selected transaction identifier |
| 4 | `LENGTH` | 1 byte | Number of payload bytes, from 0 through 8 |
| 5… | `PAYLOAD` | 0–8 bytes | Type-specific data |
| last | `CRC` | 1 byte | CRC of `VERSION` through the final payload byte |

The minimum encoded frame is 6 bytes and the maximum is 14 bytes. `LENGTH`
counts payload bytes only.

The host selects the one-byte `SEQUENCE`. PONG, ACK, NACK, and all implemented
status responses copy the associated request sequence. The sequence field
provides correlation only: the protocol does not implement automatic retries,
retransmission, duplicate suppression, or delivery ordering guarantees.

## 4. CRC-8

The implementation uses the following CRC-8/ATM parameters:

| Parameter | Value |
|---|---|
| Polynomial | `0x07` |
| Initial value | `0x00` |
| Input reflection | No |
| Output reflection | No |
| XOR-out | `0x00` |
| Coverage | `VERSION | TYPE | SEQUENCE | LENGTH | PAYLOAD` |
| Excluded field | `SOF` |

The algorithm processes each input byte most-significant bit first. For an
empty payload, the CRC still covers the four bytes `VERSION`, `TYPE`,
`SEQUENCE`, and `LENGTH`.

The standard test vector is confirmed by both the current algorithm and the
Supervisor unit test:

```text
ASCII "123456789" → 0xF4
```

## 5. Firmware parser behavior

The parser advances through `WAIT_SOF`, version, type, sequence, length,
payload, and CRC states. Its inter-byte timeout is **100 ms**.

- Bytes received while waiting for `SOF` are ignored until `0xA5` is seen.
- A valid `SOF` starts a new candidate frame.
- A version other than `0x01` resets the parser silently.
- A payload length greater than 8 resets the parser silently.
- A CRC-valid complete frame is passed to request handling.
- A bad CRC increments the CRC-error counter and resets the parser without a
  response.
- If at least 100 ms elapses between bytes of an incomplete frame, the parser
  increments the timeout counter and resets without a response.
- After any reset, the next `0xA5` observed in `WAIT_SOF` starts a new frame.

`0xA5` has delimiter meaning only in `WAIT_SOF`; it is treated as ordinary
field or payload data while a frame is already being collected. Therefore
resynchronization occurs after the parser returns to `WAIT_SOF`, not
immediately on every embedded `0xA5` byte.

### Error disposition

| Condition | Response | Counter effect | Parser effect |
|---|---|---|---|
| Noise before `SOF` | Silence | None | Remain in `WAIT_SOF` |
| Unsupported version | Silence | None | Reset to `WAIT_SOF` |
| `LENGTH > 8` | Silence | None | Reset to `WAIT_SOF` |
| Bad CRC | Silence | Saturating CRC-error increment | Reset to `WAIT_SOF` |
| Partial frame idle for at least 100 ms | Silence | Saturating timeout increment | Reset to `WAIT_SOF` |
| CRC-valid supported request with wrong semantic length | NACK `0x02` | None | Frame completed, then reset |
| CRC-valid unsupported type | NACK `0x01` | None | Frame completed, then reset |

Framing errors do not produce a NACK because the request has not been accepted
as a valid complete protocol frame.

## 6. Message type registry

All payload lengths below are exact. A supported request with a different
semantic length produces NACK reason `0x02` when the complete frame is valid and
the single immediate-response slot is available.

| Symbolic name | Hex | Direction | Request payload | Response | Response payload | Purpose |
|---|---:|---|---|---|---|---|
| `PING` | `0x01` | Host → MCU | 0 bytes | `PONG` | 0 bytes | Link/liveness transaction |
| `ECHO` | `0x02` | Host → MCU | 1–8 arbitrary bytes | `ACK` | Exact copy of request payload | Payload and bidirectional-link check |
| `GET_COMM_STATUS` | `0x03` | Host → MCU | 0 bytes | `COMM_STATUS` | 3 bytes | Read UART/parser health counters |
| `GET_TIMING_STATUS` | `0x04` | Host → MCU | 0 bytes | `TIMING_STATUS` | 8 bytes | Read four task execution-time maxima |
| `GET_JITTER_STATUS` | `0x05` | Host → MCU | 0 bytes | `JITTER_STATUS` | 8 bytes | Read four task jitter maxima |
| `GET_RUNTIME_MEMORY_STATUS` | `0x06` | Host → MCU | 0 bytes | `RUNTIME_MEMORY_STATUS` | 6 bytes | Read empirical SRAM watermark data |
| `GET_CPU_LOAD_STATUS` | `0x07` | Host → MCU | 0 bytes | `CPU_LOAD_STATUS` | 8 bytes | Read scheduled-task busy ticks and elapsed time |
| `GET_OVERRUN_STATUS` | `0x08` | Host → MCU | 0 bytes | `OVERRUN_STATUS` | 8 bytes | Read four task overrun counters |
| `GET_RESET_CAUSE` | `0x09` | Host → MCU | 0 bytes | `RESET_CAUSE` | 1 byte | Read raw boot reset-cause value |
| `INJECT_WATCHDOG_BLOCK` | `0x0A` | Host → MCU | 0 bytes | None for a valid request | None | Apply safe outputs, deliberately block foreground progress, and allow watchdog reset |
| `GET_WATCHDOG_STATUS` | `0x0B` | Host → MCU | 0 bytes | `WATCHDOG_STATUS` | 1 byte | Read persistent previous-watchdog-timeout marker |
| `PONG` | `0x81` | MCU → Host | — | — | 0 bytes | Response to `PING` |
| `COMM_STATUS` | `0x83` | MCU → Host | — | — | 3 bytes | UART overflow, parser timeout, and CRC counters |
| `TIMING_STATUS` | `0x84` | MCU → Host | — | — | 8 bytes | Four little-endian 16-bit execution maxima |
| `JITTER_STATUS` | `0x85` | MCU → Host | — | — | 8 bytes | Four little-endian 16-bit jitter maxima |
| `RUNTIME_MEMORY_STATUS` | `0x86` | MCU → Host | — | — | 6 bytes | Three little-endian 16-bit SRAM observations |
| `CPU_LOAD_STATUS` | `0x87` | MCU → Host | — | — | 8 bytes | Two little-endian 32-bit runtime values |
| `OVERRUN_STATUS` | `0x88` | MCU → Host | — | — | 8 bytes | Four little-endian 16-bit overrun counters |
| `RESET_CAUSE` | `0x89` | MCU → Host | — | — | 1 byte | Raw boot reset-cause value |
| `WATCHDOG_STATUS` | `0x8B` | MCU → Host | — | — | 1 byte, `0` or `1` | Previous watchdog-timeout marker |
| `ACK` | `0x90` | MCU → Host | — | — | 1–8 echoed bytes | Successful `ECHO` response only |
| `NACK` | `0x91` | MCU → Host | — | — | 1-byte reason | Rejection of a CRC-valid complete request |

There is no `0x82` response type for ECHO and no `0x8A` response for a valid
watchdog-block injection.

## 7. ACK and NACK semantics

### ACK

ACK is not a generic success response. It is generated only for a valid ECHO
request whose payload contains 1 through 8 bytes. ACK copies both the request
sequence and the payload exactly. A zero-length ECHO is rejected with NACK
reason `0x02`.

### NACK

NACK copies the request sequence and contains exactly one reason byte:

| Symbolic reason | Value | Meaning |
|---|---:|---|
| `UNSUPPORTED_TYPE` | `0x01` | No request handler exists for the received type |
| `INVALID_LENGTH` | `0x02` | A supported request has the wrong semantic payload length |

NACK is generated only after a complete frame passes version, maximum-length,
and CRC validation. It is not sent for noise, unsupported version, a length
greater than 8, bad CRC, or an inter-byte timeout.

PONG, ACK, and NACK share one pending-frame slot. If that slot is occupied, an
additional immediate-response request is not queued. Each status request type
has one bounded pending flag and stored sequence; another request of the same
type is not queued while that flag remains set. The Supervisor avoids these
conditions by using sequential request/response transactions.

A valid `INJECT_WATCHDOG_BLOCK` intentionally has no ACK. The foreground
communication task observes the request, applies safe outputs, and blocks so
the hardware watchdog can reset the MCU. Recovery is assessed after reboot by
new PING, WATCHDOG_STATUS, and informational RESET_CAUSE transactions.

## 8. Status payload layouts

All multi-byte integers in status payloads are **unsigned little-endian**. The
header contains only single-byte fields.

| Response | Payload bytes | Type | Field |
|---|---:|---|---|
| `COMM_STATUS` | 0 | `uint8` | UART RX ring overflow counter |
| `COMM_STATUS` | 1 | `uint8` | Parser inter-byte timeout counter |
| `COMM_STATUS` | 2 | `uint8` | Parser CRC-error counter |
| `TIMING_STATUS` | 0–1 | `uint16 LE` | Actuator task maximum, Timer1 ticks |
| `TIMING_STATUS` | 2–3 | `uint16 LE` | Control task maximum, Timer1 ticks |
| `TIMING_STATUS` | 4–5 | `uint16 LE` | Sensor/Safety task maximum, Timer1 ticks |
| `TIMING_STATUS` | 6–7 | `uint16 LE` | Communication task maximum, Timer1 ticks |
| `JITTER_STATUS` | 0–1 | `uint16 LE` | Actuator task maximum jitter, ms |
| `JITTER_STATUS` | 2–3 | `uint16 LE` | Control task maximum jitter, ms |
| `JITTER_STATUS` | 4–5 | `uint16 LE` | Sensor/Safety task maximum jitter, ms |
| `JITTER_STATUS` | 6–7 | `uint16 LE` | Communication task maximum jitter, ms |
| `RUNTIME_MEMORY_STATUS` | 0–1 | `uint16 LE` | Observed minimum free painted SRAM bytes |
| `RUNTIME_MEMORY_STATUS` | 2–3 | `uint16 LE` | Total painted SRAM region bytes |
| `RUNTIME_MEMORY_STATUS` | 4–5 | `uint16 LE` | Used bytes within the painted region |
| `CPU_LOAD_STATUS` | 0–3 | `uint32 LE` | Accumulated scheduled-task busy ticks |
| `CPU_LOAD_STATUS` | 4–7 | `uint32 LE` | Elapsed firmware time, ms |
| `OVERRUN_STATUS` | 0–1 | `uint16 LE` | Actuator task overrun count |
| `OVERRUN_STATUS` | 2–3 | `uint16 LE` | Control task overrun count |
| `OVERRUN_STATUS` | 4–5 | `uint16 LE` | Sensor/Safety task overrun count |
| `OVERRUN_STATUS` | 6–7 | `uint16 LE` | Communication task overrun count |
| `RESET_CAUSE` | 0 | `uint8` | Raw boot reset-cause value |
| `WATCHDOG_STATUS` | 0 | `uint8` | Previous watchdog timeout marker: `0` or `1` |

### Measurement interpretation

- Timer1 runs at 2 MHz, so one TIMING_STATUS or CPU busy tick is **0.5 µs**.
- TIMING_STATUS contains observed maxima since profiler initialization, not
  guaranteed WCET.
- JITTER_STATUS has **1 ms measurement resolution** and reports observed
  maximum absolute start-interval deviation for each task.
- RUNTIME_MEMORY_STATUS reports an empirical stack/SRAM canary watermark. It is
  not a guaranteed minimum-free-SRAM bound for all executions.
- CPU_LOAD_STATUS covers scheduled-task body execution only. The host computes
  `100 × busy_ticks / (elapsed_ms × 2000)`; ISR and scheduler overhead are
  excluded.
- OVERRUN_STATUS counts observed task bodies whose measured execution exceeds
  the task's nominal period. Its per-task counters saturate at `65535`.
- RESET_CAUSE is the raw boot value captured from the bootloader handoff and is
  informational. The observed value `0xF7` must not be interpreted as proof of
  WDRF.
- WATCHDOG_STATUS is separate from RESET_CAUSE. Value `1` means the previous
  boot was preceded by the watchdog ISR writing both persistent `.noinit`
  markers; value `0` means that marker condition was not detected.

## 9. Communication counter semantics

| Counter | Width | Increment condition | Saturation | Cleared by read |
|---|---:|---|---|---|
| UART RX overflow | 8-bit | RX ISR finds the ring full | At `255` | No |
| Parser timeout | 8-bit | Incomplete frame remains idle for at least 100 ms | At `255` | No |
| CRC error | 8-bit | Complete candidate frame has a bad CRC | At `255` | No |

COMM_STATUS reads are non-destructive. The counters are initialized to zero by
UART/protocol initialization after boot; requesting status does not clear them.
No counter is incremented for noise before SOF, unsupported version, or a
payload length greater than 8.

## 10. Verified frame examples

The following bytes were produced with the current Supervisor `encode_frame()`
implementation, which uses the same CRC parameters as the firmware:

| Frame | Encoded bytes |
|---|---|
| PING request, sequence `0x10` | `A5 01 01 10 00 2A` |
| PONG response, sequence `0x10` | `A5 01 81 10 00 21` |
| ECHO request, sequence `0x20`, payload `11 22 33 44` | `A5 01 02 20 04 11 22 33 44 E7` |
| ACK response, sequence `0x20`, echoed payload `11 22 33 44` | `A5 01 90 20 04 11 22 33 44 07` |

In each row the final byte is the CRC and the first byte, `A5`, is excluded from
its calculation.

## 11. Python Supervisor interaction

The Supervisor uses Python standard-library `os`, `termios`, and `select`
facilities; it does not require pyserial. It opens the exact user-provided port
at 9600 baud, waits for the UNO's possible serial-open reset, sends encoded
frames, reads the declared response length, validates CRC, and checks the
response type and sequence.

```bash
# PING/PONG and ECHO/ACK
python3 supervisor/main.py --port /dev/cu.usbmodem1101

# Communication counters
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --status

# Controlled watchdog reset campaign
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --watchdog-test
```

`/dev/cu.usbmodem1101` is an example only. The actual serial device must be
discovered and passed explicitly. The watchdog mode is destructive to the
current MCU session by design: it intentionally causes a hardware reset.

The Supervisor performs monitoring, evidence collection, profiling requests,
and controlled fault injection. It does not directly control actuator GPIO and
is not the local Safety authority.

## 12. Design rationale

- A fixed 8-byte maximum payload bounds parser, frame, and response memory.
- Explicit SOF, version, type, sequence, and length fields make framing and
  transaction correlation deterministic.
- CRC-8 detects corrupted frame content within the implemented model.
- Timeout and return to `WAIT_SOF` allow recovery from incomplete or malformed
  streams.
- ACK/NACK make ECHO success and supported-request rejection explicit.
- Saturating, non-destructive communication counters support repeatable health
  monitoring and fault-injection evidence.
- Fixed RX/TX rings and no dynamic allocation suit the ATmega328P's 2 KB SRAM.

## 13. Known limitations

- Payloads are limited to 8 bytes.
- The link runs at 9600 baud.
- There is no encryption, authentication, authorization, or replay protection.
- There is no guaranteed-delivery, retry, retransmission, or transport-level
  acknowledgement layer.
- The host implementation uses sequential request/response transactions; the
  firmware uses bounded pending state rather than an unbounded response queue.
- A SOF byte embedded in a candidate frame does not force immediate
  resynchronization.
- Protocol CRC provides error detection, not security.
- Host supervision cannot override or replace local MCU Safety.
- The protocol is experimental and is not safety-certified.

## 14. Related documentation

- [Project README](../../README.md)
- [System Architecture](../architecture/system_architecture.md)
- [Final System Validation Report](../validation/final_system_validation_report.md)
