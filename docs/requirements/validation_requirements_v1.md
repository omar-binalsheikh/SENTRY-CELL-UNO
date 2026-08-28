# SENTRY-CELL UNO — Validation Requirements Baseline v1

- Historical PHASE 0 requirement artifact: NOT PRESENT IN REPOSITORY.
- This file is a validation baseline created during PHASE 15.
- It does not claim verbatim equivalence with historical SYS-REQ-001..045.
- It is authoritative for PHASE 15 validation after user/ChatGPT approval recorded in PHASE 15 — ÉTAPE 1B.

Baseline approval status: **APPROVED FOR PHASE 15 VALIDATION**  
Created: 2026-08-27  
System context: experimental low-voltage mini industrial cell; local safety has priority; this is not a SIL/ASIL-certified system.

## Basis and interpretation

This approved baseline is derived only from:

1. behavior and architecture actually present in the repository;
2. the PHASE 15 readiness audit and repository measurement artifacts;
3. the mandatory final-system capabilities explicitly supplied for this step.

`MUST` requirements are blocking for final experimental-system validation. `SHOULD` requirements are desirable but non-blocking unless their priority is changed by a later approved baseline revision.

Acceptance criteria define observable pass/fail conditions. “Evidence expected” identifies the evidence that must be retained; it does not claim that the evidence already exists. Observed timing values are not guaranteed WCET, scheduled-task utilization is not total MCU CPU load, and a runtime SRAM watermark is not guaranteed minimum free SRAM.

## Platform and architecture

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-001 | The firmware shall target the ATmega328P used on an Arduino UNO R3 at 16 MHz and shall generate ELF and Intel HEX artifacts with the AVR toolchain. | MUST | `make clean`, `make`, and `make size` pass with `-mmcu=atmega328p` and `F_CPU=16000000UL`; the expected ELF and HEX exist. | Build log, Makefile review, `avr-size` output, artifact hashes. |
| VAL-REQ-002 | The firmware shall be bare-metal AVR C/C++, shall not depend on the Arduino framework, and shall not use dynamic allocation. | MUST | Source/build review finds no `Arduino.h`, Arduino GPIO/Serial API, `malloc`/`calloc`/`realloc`/`free`, or C++ `new`/`delete`; the project builds with the declared AVR compiler flags. | Static source scan and successful build log. |
| VAL-REQ-003 | Application work shall be dispatched by a cooperative scheduler and shall remain non-blocking as far as reasonably practical. | MUST | The integrated application registers the actuator, control, sensor/safety, and communication tasks; no task contains an unbounded wait or blocking delay. Any bounded peripheral wait is identified and justified. | Scheduler/main source review, task-period inventory, execution/overrun measurements. |
| VAL-REQ-004 | Interrupt service routines shall be short and shall not perform blocking I/O, dynamic allocation, or scheduler/application loops. | MUST | Review of every compiled ISR shows bounded register/buffer/state handling and no busy-wait loop; interrupt-driven behavior passes its hardware/protocol test. | ISR inventory, source review, UART/Timer hardware test evidence. |

## Acquire

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-005 | The system shall acquire the thermistor as an unconverted 10-bit raw ADC value on ADC0/A0 using AVcc reference. | MUST | Reads remain within 0–1023 and a physical thermistor stimulus produces a repeatable raw-value change; no Celsius claim is made. | ADC/thermistor source review and recorded raw samples from a physical test. |
| VAL-REQ-006 | The system shall obtain HC-SR04 echo pulse measurements and derive a distance value for local obstacle safety. | MUST | A physical near/far target campaign produces valid measurements, handles missing/invalid echo without hanging, and supplies the safety decision path. | Driver/source review, input-capture test log, near/far measurement results. |

## Control

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-007 | The system shall command the stepper through the ULN2003 and shall be able to run it in `ACTIVE` and remove all phase drive outside `ACTIVE`. | MUST | Physical testing shows sequenced rotation in `ACTIVE`; `IDLE`, boot-safe handling, and `SAFE_STATE` drive all four phases LOW. | Driver/main review and state-by-state physical test record. |
| VAL-REQ-008 | The system shall command the SG90 servo and shall provide distinct `ACTIVE` and safe commands without a blocking application delay. | MUST | Timer-driven pulse generation is observed; `ACTIVE` selects the active command and boot/IDLE/SAFE selects the approved safe command. | Servo timing evidence, source review, state-transition physical test. |
| VAL-REQ-009 | The system shall command the low-voltage relay through its transistor stage and shall force it OFF outside `ACTIVE`. | MUST | The relay is ON only in `ACTIVE` and OFF during boot, IDLE, SAFE_STATE, and scheduler-add failure handling. | Driver/main review and low-voltage relay state test; no mains load. |
| VAL-REQ-010 | The DC motor interface shall support forward, reverse, and stop commands, and the integrated system shall be able to force STOP in every safe or inactive state. | MUST | Driver-level forward/reverse/stop tests pass; integrated boot, IDLE, and SAFE_STATE tests show both L293D inputs LOW and no unintended motion. | Driver truth-table review, component smoke test, integrated safe-output test. |
| VAL-REQ-011 | The integrated application shall give the DC motor a real cooling function in `ACTIVE`, while commanding STOP in `IDLE` and mandatory STOP in `SAFE_STATE`. | MUST | Firmware commandability and an explicit non-blocking ACTIVE cooling behavior are documented; a physical test demonstrates that behavior in ACTIVE and STOP in IDLE/SAFE_STATE. No thermal threshold or detailed cooling strategy is required until defined in a later firmware step. | Application design, state/output trace, and real physical ACTIVE/IDLE/SAFE_STATE motor test. |

Priority rationale for VAL-REQ-011: experimental cooling is an approved real system function. The exact thermal threshold and cooling strategy remain intentionally undefined for a later firmware step, but ACTIVE functionality and safe STOP behavior are validation blockers.

## FSM

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-012 | The system FSM shall implement `BOOT`, `IDLE`, `ACTIVE`, and `SAFE_STATE`, with `BOOT -> IDLE` after initialization and one `IDLE <-> ACTIVE` transition per physical button press. | MUST | State inspection and physical testing demonstrate the four states, initialization transition, button toggle, and suppression of repeated events while the button is held. | FSM unit/state-table review and physical button/FSM test log. |
| VAL-REQ-013 | A critical fault while in `ACTIVE` shall transition the FSM to `SAFE_STATE`, which shall remain latched until MCU reset. | MUST | Injecting the approved critical fault in ACTIVE enters SAFE_STATE; button actions and undefined events do not leave it; reset returns through BOOT to IDLE. | FSM review and fault/reset transition test record. |

## Safety

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-014 | In `ACTIVE`, a valid HC-SR04 distance greater than 0 cm and less than or equal to 20 cm shall be treated as a critical obstacle fault. | MUST | Boundary tests cover invalid input, 0 cm, 20 cm, and a value above 20 cm; only a valid 1–20 cm value in ACTIVE raises the critical event. | Safety unit/boundary test and physical obstacle test. |
| VAL-REQ-015 | On entry to `SAFE_STATE`, the stepper shall stop, relay shall turn OFF, DC motor shall stop, and servo shall take the approved safe command on their next respective service execution. | MUST | A critical-obstacle test records each actuator output reaching its defined safe state and remaining there while the fault is latched. | Integrated fault-injection video/log or signed test record plus source trace. |
| VAL-REQ-016 | In `SAFE_STATE`, the start/stop button shall be ignored and a local fault indication shall remain available. | MUST | Repeated button presses do not change state or re-energize actuators; the defined LED fault pattern is observable. | FSM/control review and physical safe-state interaction test. |

## Diagnostics

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-017 | Diagnostics shall retain at least the last critical-obstacle fault and a fault counter, and getter/read operations shall not reset them. | MUST | Initialization yields no fault/count 0; recording a new obstacle fault updates last fault and count; repeated reads preserve both values. | Diagnostics unit test or debugger/protocol observation and source review. |
| VAL-REQ-018 | Communication diagnostics shall expose saturating UART RX overflow, parser timeout, and CRC error counters that are not reset by status reads. | MUST | Each fault is injected, its corresponding counter increments without wrap, repeated COMM_STATUS reads preserve it, and PING recovery succeeds. | Automated BAD_CRC/partial-frame/overflow evidence, COMM_STATUS captures, CSV result. |

## Communication

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-019 | USART0 shall operate at 9600 baud, 8N1, with interrupt-driven RX and TX ring buffers. | MUST | Register review confirms UBRR0=103 and 8N1; RX and UDRE ISRs service bounded buffers; bidirectional traffic succeeds without polling waits in the communication task. | UART source review, ISR inventory, real serial transaction log. |
| VAL-REQ-020 | The binary frame shall be `SOF` &#124; `VERSION` &#124; `TYPE` &#124; `SEQUENCE` &#124; `LENGTH` &#124; `PAYLOAD` &#124; `CRC` and shall use CRC-8/ATM over VERSION through PAYLOAD. | MUST | Host and firmware encode/decode a common known frame, the `123456789` CRC vector yields 0xF4, and a corrupted CRC is rejected. | Codec unit tests, frame hex capture, BAD_CRC injection record. |
| VAL-REQ-021 | The protocol shall support real PING/PONG and ECHO/ACK transactions and shall return NACK for defined invalid or unsupported requests. | MUST | At least two live PING/PONG and ECHO/ACK exchanges pass with matching sequence/payload; invalid length and unsupported type produce their defined NACK reason. | Supervisor serial transcript and protocol unit tests. |
| VAL-REQ-022 | The parser shall time out and resynchronize after an incomplete frame without requiring MCU reset. | MUST | A deliberately partial frame held beyond the configured inter-byte timeout increments the timeout counter, after which a valid PING/PONG succeeds. | PARTIAL_FRAME_TIMEOUT automated fault-injection result and parser test. |
| VAL-REQ-023 | The protocol shall provide communication-health, timing, jitter, runtime-memory, scheduled-task CPU-load, and task-overrun telemetry with sequence preservation. | MUST | A live request for each telemetry type returns the defined payload length/endianness and the same sequence; host decoding passes. | Firmware/host protocol tests and live regression transcript for all status types. |

## Python supervisor

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-024 | The supervisor shall use only the Python standard library for serial I/O and protocol encoding/decoding and shall perform real PING/PONG and ECHO/ACK checks. | MUST | Dependency/source review finds no third-party serial package; the CLI completes live PING and ECHO checks on an exact user-supplied port. | Python source review, unit-test output, live supervisor transcript. |
| VAL-REQ-025 | The supervisor shall provide finite communication-health monitoring with CSV logging and automated BAD_CRC and PARTIAL_FRAME_TIMEOUT fault injection with recovery checks. | MUST | A finite run writes the exact CSV schema and samples; both injections increment the expected counter and pass recovery PING. | CSV files, automated unit tests, live campaign output. |
| VAL-REQ-026 | The supervisor shall display timing, jitter, runtime-memory watermark, scheduled-task utilization, and overrun telemetry without changing firmware state. | MUST | Each read-only CLI mode decodes and prints the corresponding live response; utilization handles elapsed_ms=0 safely and includes the required scope disclaimers. | Python unit tests and live telemetry transcripts. |

## Real-time and memory measurements

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-027 | The final validation build shall provide observed task execution maxima, observed jitter maxima, observed scheduled-task CPU utilization, task execution overruns, Flash use, static SRAM use, and an observed runtime SRAM watermark. | MUST | All seven measurement classes are captured for the identified build and scenario; reports label them as observations and do not claim guaranteed WCET, total MCU CPU load, or guaranteed minimum free SRAM. | Build hash, `avr-size`, linker/map evidence, profiler transcripts, runtime scenario record, consolidated measurement report. |

## Electrical safety

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-028 | The prototype shall remain low-voltage only: no 230 V connection, controlled logic/actuator supplies, common grounds where required, and no power actuator driven directly from an MCU GPIO. | MUST | Pre-power inspection confirms no mains connection; supply voltages/polarities and common ground are recorded; relay, stepper, DC motor, and servo use their required transistor/driver/external-power paths. | Wiring diagram/photos, signed pre-power checklist, measured supply voltages, smoke-test record. |

## Approved architecture decisions and enhancements

The following requirements record the approved gap decisions. Watchdog recovery is mandatory. The other listed enhancements remain non-blocking because local obstacle safety is autonomous and the project is an experimental mini-cell rather than a certified safety system.

| ID | Requirement | Priority | Acceptance criterion | Evidence expected |
|---|---|---|---|---|
| VAL-REQ-029 | The thermistor should trigger a defined thermal warning or safety action only after its sensor model, divider topology, calibration method, threshold, and invalid-reading behavior are approved. | SHOULD | If enabled, approved raw/temperature boundaries are unit-tested and physically crossed, producing the documented action without float-related ambiguity; until then raw acquisition alone satisfies VAL-REQ-005. | Approved thermal decision, calibration data, boundary tests, physical heating test. |
| VAL-REQ-030 | The firmware shall explicitly configure the ATmega328P watchdog, service it only while the system is operating normally, and allow it to reset the MCU after a controlled stall or approved fault injection. | MUST | Watchdog configuration and normal-service location are reviewed; a controlled non-normal stall prevents service and causes a real watchdog reset; outputs return safely through BOOT/IDLE; reset cause is made observable or diagnosable where reasonably practical. | Watchdog configuration/service trace, real controlled-stall reset test, safe-restart evidence, and reset-cause diagnostic evidence or documented feasibility limit. |
| VAL-REQ-031 | The system should detect loss of an expected supervisor heartbeat or communication session as a diagnostic/warning while preserving autonomous local MCU safety. PC disconnection alone need not force `SAFE_STATE`. | SHOULD | If enabled, heartbeat loss beyond the approved timeout produces the documented warning/diagnostic; HC-SR04 local safety remains operational without the Python supervisor; link restoration follows the approved recovery policy. | Approved timeout/policy, disconnect/reconnect test, diagnostic capture, and local-safety-with-PC-disconnected test. |
| VAL-REQ-032 | The final experimental cell should provide additional local HMI through an LCD, RGB LED, and buzzer if those devices are selected for the final demonstrator. | SHOULD | For each selected device, initialization and state/fault indications are documented and physically tested; failure or absence of the HMI does not energize an actuator or defeat SAFE_STATE. | Approved HMI selection, driver tests, state/fault indication matrix, physical evidence. |
| VAL-REQ-033 | The final experimental cell should acquire DHT11 environmental data if ambient temperature/humidity is selected as part of the demonstrator mission. | SHOULD | If selected, valid checksum-protected readings and timeout/error handling are demonstrated without blocking scheduled safety work. | Approved sensor selection, driver review, valid/invalid physical test captures. |
| VAL-REQ-034 | Diagnostics should maintain a bounded fault/event history beyond the current last-fault value and counter, without dynamic allocation. | SHOULD | If enabled, a statically bounded log preserves ordered defined events, reports overflow policy, and is not cleared by read-only access. | Log design, unit tests for ordering/capacity/reads, telemetry transcript if exposed. |
| VAL-REQ-035 | The Python supervisor should provide actuator or fault-injection commands only if local validation needs them, and such commands shall never override latched SAFE_STATE or local safety. | SHOULD | If enabled, every command has explicit validation/range checks, ACK/NACK behavior, and tests proving rejection in SAFE_STATE and recovery only by the approved mechanism. | Approved command set, protocol specification, unit tests, live safe-state rejection test. |

Priority rationale:

- **DC motor ACTIVE logic (VAL-REQ-011):** `MUST`; the approved integrated role is experimental cooling, with STOP mandatory in IDLE and SAFE_STATE. No thermal threshold or detailed strategy is yet specified.
- **Thermistor safety (VAL-REQ-029):** `SHOULD`; only raw acquisition is mandatory and no defensible thermal threshold or sensor calibration was supplied.
- **Watchdog (VAL-REQ-030):** `MUST`; controlled stall recovery and a safe restart are approved final-validation obligations.
- **Communication-loss detection (VAL-REQ-031):** `SHOULD`; it is a warning/diagnostic, while local obstacle safety remains independent of the supervisor and PC disconnection alone does not require SAFE_STATE.
- **LCD, RGB LED, buzzer (VAL-REQ-032):** `SHOULD`; useful HMI, but not necessary to demonstrate the current local-safety behavior.
- **DHT11 (VAL-REQ-033):** `SHOULD`; no mandatory mission use is defined beyond the existing thermistor raw channel.
- **Fault/event log (VAL-REQ-034):** `SHOULD`; the mandatory last-fault and counter diagnostics remain sufficient for the proposed experimental validation.
- **Python actuator/fault commands (VAL-REQ-035):** `SHOULD`; read-only supervision is sufficient for current validation and command authority adds safety surface.

## Summary

Total requirements: **35**  
MUST count: **29**  
SHOULD count: **6**

## OPEN BASELINE DECISIONS

**NONE**
