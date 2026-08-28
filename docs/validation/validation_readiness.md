# SENTRY-CELL UNO — Validation Readiness Audit

## Baseline

- Authoritative requirements baseline: `docs/requirements/validation_requirements_v1.md`
- Approval status: APPROVED FOR PHASE 15 VALIDATION
- Total requirements: 35
- MUST: 29
- SHOULD: 6
- Open baseline decisions: NONE
- Historical note: this VAL-REQ v1 baseline does not retroactively replace the absent historical SYS-REQ-001..045 set.
- Audit scope: repository evidence, persisted measurements, and the explicit physical-validation evidence supplied by the user for this audit.
- Audit actions: documentation review only; no firmware change, build, upload, or new physical test was performed.

Evidence-state vocabulary used below:

- `PLANNED`: required or intentionally deferred, with no implementation evidence.
- `IMPLEMENTED`: present in source, without sufficient build/test evidence for the full acceptance criterion.
- `COMPILED`: present in a successfully built firmware baseline.
- `TESTED`: exercised by a defined software or hardware test.
- `MEASURED`: supported by recorded quantitative results.
- `VALIDATED`: acceptance behavior is supported by explicit successful real-system evidence.

## Evidence Sources

1. Approved baseline: `docs/requirements/validation_requirements_v1.md`.
2. Current firmware and host implementation under `firmware/`, `supervisor/`, and `Makefile`, reviewed without modification.
3. Persisted communication evidence:
   - `measurements/comm_health.csv`
   - `measurements/fault_injection_comm.csv`
4. Persisted static-memory report: `measurements/memory_static.txt`. This report describes an earlier 5082/10/245 build and is retained as historical evidence, not as the current-build static-memory result.
5. Existing build artifacts inspected without rebuilding:
   - `build/sentry-cell-uno.elf`, SHA-256 `3f32ace4f15895fd14b350d09de855f17ae7fb69e71fd79983825056bb163d59`
   - `build/sentry-cell-uno.hex`, SHA-256 `3c18c0c317c7738c0dfd4104fdda4411734061da2c08ef3a4d29a1bfb46f4f4d`
   - `build/sentry-cell-uno.map`, SHA-256 `3a03c351d26b18f73e72a1c34378d52ffe5df907251f9b52024892a363ed8d10`
6. Current-build VAL-REQ-027 campaign records:
   - `measurements/val_req_027_campaign_2026-08-27_202840.txt`: canonical PHASE 15 campaign; identifies the ELF, HEX, and map hashes, records `text=6886`, `data=10`, `bss=280`, `dec=7176`, and contains all seven required measurement classes for the recorded IDLE/ACTIVE/SAFE scenario.
   - `measurements/val_req_027_campaign_2026-08-27_213529.txt`: later secondary repeatability campaign on the same build.
   - `measurements/val_req_027_current_build.txt`: traceability index identifying the canonical and secondary roles.
7. Real host-side production-module tests:
   - `tests/test_safety.c`: actual `firmware/safety/safety.c`, 8/8 boundary cases PASS.
   - `tests/test_diagnostics.c`: actual `firmware/diagnostics/diagnostics.c`, 8/8 retention cases PASS.
8. Final electrical-safety evidence:
   - `docs/hardware/electrical_safety_evidence.md`
   - `docs/validation/pre_power_checklist.md` (10/10 PASS, validation-session user sign-off confirmed, 2026-08-27)
   - four reviewed files under `docs/hardware/photos/`
   - user measurements: logic rail approximately 4.8 V; actuator rail approximately 4.9 V.
9. User-supplied real hardware validation evidence: GPIO/button/LED, Timer2 time base, scheduler, ADC/thermistor raw acquisition, HC-SR04 behavior and physical switching-boundary characterization, all actuators, integrated smoke test, FSM, final BOOT/IDLE/ACTIVE/SAFE_STATE end-to-end sequence, obstacle SAFE_STATE behavior and latching, diagnostics LED indication, UART/protocol/supervisor checks, DC-motor integrated behavior, and controlled watchdog recovery.
10. Final evidence freeze: `docs/validation/final_system_validation_report.md`.
11. No prompt, planned procedure, source-code presence, or compilation result is treated by itself as physical validation.

## Requirement Traceability

| Requirement | Priority | Requirement summary | Implementation evidence | Test/measurement evidence | Current status | Gap |
|---|---|---|---|---|---|---|
| VAL-REQ-001 | MUST | ATmega328P reproducible build and artifacts | `Makefile`; AVR ELF/HEX flow | Existing ELF/HEX inspected and hashed; current build figures supplied: 6886/10/280 | COMPILED | None identified |
| VAL-REQ-002 | MUST | Bare-metal C, fixed memory, no dynamic allocation | AVR register HALs; static scheduler/protocol/UART storage | Code review and successful integrated builds | COMPILED | None identified |
| VAL-REQ-003 | MUST | Cooperative, bounded, non-blocking scheduling | `firmware/scheduler/scheduler.*`; bounded ADC/ultrasonic/UART services | Scheduler physical PASS; profiling campaign recorded | MEASURED | None identified |
| VAL-REQ-004 | MUST | Short deterministic ISRs | Timer1, Timer2, UART and watchdog ISR implementations | Timing campaign and integrated behavior PASS | TESTED | None identified |
| VAL-REQ-005 | MUST | Raw thermistor ADC acquisition | `firmware/hal/adc.*`; `firmware/drivers/thermistor.h` | Potentiometer/thermistor raw physical PASS | VALIDATED | None identified |
| VAL-REQ-006 | MUST | HC-SR04 distance and safety input | `firmware/drivers/hcsr04.*` | Physical distance/safety behavior PASS | VALIDATED | None identified |
| VAL-REQ-007 | MUST | Stepper ACTIVE and de-energized otherwise | `firmware/drivers/stepper.*`; integrated output policy | Stepper and integrated smoke-test physical PASS | VALIDATED | None identified |
| VAL-REQ-008 | MUST | Servo ACTIVE and safe command otherwise | `firmware/drivers/servo.*`; integrated output policy | Servo and integrated smoke-test physical PASS | VALIDATED | None identified |
| VAL-REQ-009 | MUST | Relay ACTIVE only; OFF otherwise | `firmware/drivers/relay.*`; integrated output policy | Relay and integrated smoke-test physical PASS | VALIDATED | None identified |
| VAL-REQ-010 | MUST | DC motor driver commands and safe states | `firmware/drivers/dc_motor.*`; integrated output policy | Driver bring-up and integrated motor test PASS | VALIDATED | None identified |
| VAL-REQ-011 | MUST | Real cooling role: ACTIVE forward, IDLE/SAFE stop | `firmware/main.c` output policy | User observed IDLE stop, ACTIVE rotation, SAFE and latched-SAFE stop | VALIDATED | None identified |
| VAL-REQ-012 | MUST | BOOT/IDLE/ACTIVE/SAFE FSM and button transition | `firmware/app/system_fsm.*`; button task | Physical IDLE/ACTIVE FSM test PASS | VALIDATED | None identified |
| VAL-REQ-013 | MUST | Critical fault enters latched SAFE until reset | Safety/FSM integration in `firmware/main.c` | Obstacle-to-SAFE and latched-until-reset physical PASS | VALIDATED | None identified |
| VAL-REQ-014 | MUST | Obstacle boundary semantics, including invalid/0/20/>20 | `firmware/safety/safety.c`; HC-SR04 validity handling | Real `safety.c` unit test 8/8 PASS; physical boundary evidence retained (observed system characteristic approximately 21.8–22.0 cm) | VALIDATED | None identified; the physical switching point is not represented as centimetre-level sensor calibration |
| VAL-REQ-015 | MUST | All actuators safe in SAFE_STATE | Centralized output policy invokes stop/off/safe commands | Integrated SAFE behavior and smoke test PASS | VALIDATED | None identified |
| VAL-REQ-016 | MUST | Button cannot exit SAFE; visible fault indication | FSM event policy and diagnostics LED output | SAFE latching and diagnostics LED physical PASS | VALIDATED | None identified |
| VAL-REQ-017 | MUST | Retained last fault/count; getters are non-destructive | `firmware/diagnostics/diagnostics.*` and its public getters | Real diagnostics-module unit test 8/8 PASS; initialization, recording, repeated-read retention, duplicate/new-event and reinitialization behavior covered | TESTED | None identified |
| VAL-REQ-018 | MUST | Saturating UART overflow/timeout/CRC counters | UART/protocol diagnostics and counter telemetry | Burst, CRC/partial fault injection, recovery and CSV counter evidence PASS | VALIDATED | None identified |
| VAL-REQ-019 | MUST | USART0 9600 8N1 with RX/TX rings and ISR service | `firmware/hal/uart.*` | TX/RX and ring-buffer burst physical PASS | VALIDATED | None identified |
| VAL-REQ-020 | MUST | Binary framing and CRC-8 | `firmware/protocol/protocol.*` | CRC rejection and fault injection PASS | VALIDATED | None identified |
| VAL-REQ-021 | MUST | PING, ECHO, ACK/NACK | Protocol handlers and supervisor transactions | PING/PONG and ECHO/ACK/NACK physical PASS | VALIDATED | None identified |
| VAL-REQ-022 | MUST | Parser timeout and resynchronization | Protocol parser timeout/resync state | Timeout/resync and partial-frame injection PASS | VALIDATED | None identified |
| VAL-REQ-023 | MUST | Communication-health, timing, jitter, runtime-memory, scheduled-task CPU-load and task-overrun telemetry | Protocol telemetry handlers and runtime instrumentation | Live supervisor/monitoring evidence supplied | MEASURED | None identified |
| VAL-REQ-024 | MUST | Python standard-library supervisor | `supervisor/main.py` | Real serial supervisor PASS | VALIDATED | None identified |
| VAL-REQ-025 | MUST | Live monitoring, CSV, CRC/partial fault modes and recovery | Supervisor monitoring/fault-injection paths | CSV monitoring and comm fault-injection PASS | VALIDATED | None identified |
| VAL-REQ-026 | MUST | Human-readable read-only telemetry display | Supervisor output paths | Live telemetry display/monitoring PASS | TESTED | None identified |
| VAL-REQ-027 | MUST | Final-build timing, jitter, CPU, overruns, Flash, SRAM and watermark evidence | Profiling instrumentation and static-size flow | Canonical `measurements/val_req_027_campaign_2026-08-27_202840.txt`: identified build/scenario and all seven required measurement classes with scope limitations; later same-build repeatability record retained separately | MEASURED | None identified |
| VAL-REQ-028 | MUST | Low-voltage integration safety evidence | Separate logic/actuator rails, common ground, ULN2003/L293D/PN2222 paths, external servo power, no direct GPIO actuator power, no mains switching | Logic approximately 4.8 V and actuator approximately 4.9 V measured; 10/10 checklist PASS with user session sign-off; four photos; actuator/integrated smoke tests PASS | VALIDATED | None identified; photographs are complementary and do not prove hidden electrical nodes |
| VAL-REQ-029 | SHOULD | Calibrated thermal action only | Raw ADC only, as intended | No calibrated Celsius model or threshold claimed | PLANNED | Calibration/model/threshold intentionally deferred; non-blocking |
| VAL-REQ-030 | MUST | Hardware watchdog with controlled-stall recovery | `firmware/hal/watchdog.*`; safe-output fault injection; reset marker telemetry | Controlled block: MCU recovery, post-reset PING and watchdog marker PASS | VALIDATED | Raw MCUSR value 0xF7 is informational only and is not used as WDRF proof |
| VAL-REQ-031 | SHOULD | Supervisor communication-loss diagnostics without PC-dependent safety | Local MCU safety remains independent | No explicit communication-loss warning campaign | PLANNED | Diagnostic/warning feature not demonstrated; non-blocking |
| VAL-REQ-032 | SHOULD | Optional local HMI | Not required by current architecture | No HMI validation evidence | PLANNED | Not selected for mandatory baseline; non-blocking |
| VAL-REQ-033 | SHOULD | Optional DHT11 | Not required by current architecture | No DHT11 validation evidence | PLANNED | Not selected for mandatory baseline; non-blocking |
| VAL-REQ-034 | SHOULD | Optional bounded historical event log | Current diagnostics expose current fault/counters | No bounded multi-event history demonstrated | PLANNED | Advanced event history absent; non-blocking |
| VAL-REQ-035 | SHOULD | Safe supervisor actuator/fault-injection commands when needed | Controlled watchdog fault-injection command exists | Physical watchdog injection PASS | TESTED | No consolidated validation of the general live-system rejection/range/ACK-NACK policy; non-blocking |

## MUST Gap Analysis

MUST disposition counts:

- SATISFIED: 29
- PARTIALLY SATISFIED: 0
- NOT SATISFIED: 0
- UNKNOWN: 0

SATISFIED requirements (29): VAL-REQ-001, VAL-REQ-002, VAL-REQ-003, VAL-REQ-004, VAL-REQ-005, VAL-REQ-006, VAL-REQ-007, VAL-REQ-008, VAL-REQ-009, VAL-REQ-010, VAL-REQ-011, VAL-REQ-012, VAL-REQ-013, VAL-REQ-014, VAL-REQ-015, VAL-REQ-016, VAL-REQ-017, VAL-REQ-018, VAL-REQ-019, VAL-REQ-020, VAL-REQ-021, VAL-REQ-022, VAL-REQ-023, VAL-REQ-024, VAL-REQ-025, VAL-REQ-026, VAL-REQ-027, VAL-REQ-028, VAL-REQ-030.

Blocking MUST gaps: **NONE**.

The former evidence blockers are closed by the real `safety.c` 8/8 boundary test, real diagnostics 8/8 retention test, identified seven-class current-build measurement campaign, and consolidated electrical evidence package. This readiness classification does not replace the separate final end-to-end validation campaign.

## SHOULD Gap Analysis

SHOULD requirements remain non-blocking and are not promoted to MUST.

| Requirement | Current assessment | Remaining optional work |
|---|---|---|
| VAL-REQ-029 | PLANNED | Calibrate the actual thermistor/divider and define a defensible thermal threshold before claiming physical temperature or thermal safety. |
| VAL-REQ-031 | PLANNED | Add and validate supervisor communication-loss diagnostic/warning behavior while retaining autonomous local safety. |
| VAL-REQ-032 | PLANNED | Add an HMI only if selected for a later product objective. |
| VAL-REQ-033 | PLANNED | Add DHT11 support only if selected for a later product objective. |
| VAL-REQ-034 | PLANNED | Add a bounded historical event log only if later diagnostics require it. |
| VAL-REQ-035 | TESTED | If more live commands are added, document and validate range checks, ACK/NACK behavior, SAFE_STATE rejection and reset-only recovery. |

SHOULD remaining: 6.

## Current Measurements

### Identified current validation build

| Item | Value |
|---|---:|
| `.text` | 6886 bytes |
| `.data` | 10 bytes |
| `.bss` | 280 bytes |
| `dec` | 7176 bytes |
| Flash used (`text + data`) | 6896 / 32768 bytes |
| Flash remaining | 25872 bytes |
| Flash usage | 21.04% |
| Static SRAM used (`data + bss`) | 290 / 2048 bytes |
| SRAM remaining before runtime stack/heap | 1758 bytes |
| Static SRAM usage | 14.16% |

These static figures and artifact hashes are recorded in the canonical
`measurements/val_req_027_campaign_2026-08-27_202840.txt`; the
`measurements/val_req_027_current_build.txt` file is the campaign index. This
documentation-only reconciliation did not rebuild the firmware.

### Canonical current-build runtime and timing campaign

| Measurement | Observed value | Scope/limitation |
|---|---:|---|
| Actuator task maximum | 22 us (44 Timer1 ticks) | Observed campaign maximum, not a WCET proof |
| Control task maximum | 51.5 us (103 Timer1 ticks) | Observed campaign maximum, not a WCET proof |
| Sensor/safety task maximum | 217.5 us (435 Timer1 ticks) | Observed campaign maximum, not a WCET proof |
| Communication task maximum | 78 us (156 Timer1 ticks) | Observed campaign maximum, not a WCET proof |
| Scheduler jitter | 0 ms for all reported tasks | No non-zero jitter was observed at 1 ms resolution; this is not a mathematical zero-jitter guarantee |
| Scheduled-task utilization | 1.6% | Scheduled tasks only; excludes ISR execution and scheduler/framework overhead, so it is not total CPU utilization |
| Task overruns | 0 | No overrun observed during the campaign; not a proof for all executions |
| SRAM painted region | 1721 bytes | Runtime watermark campaign |
| Maximum painted SRAM consumed | 62 bytes | Observed campaign value |
| Minimum free SRAM observed | 1659 bytes | Observed watermark only; not a guaranteed minimum |

The report identifies the current ELF, HEX, and map hashes and records an approximately 5 s IDLE, 10 s ACTIVE, and 5 s SAFE scenario. Scenario transitions were directed and timed by the host; the report does not claim automatic FSM-state detection. Scheduled-task utilization excludes ISR execution and scheduler overhead. The measurements are campaign observations, not all-execution timing or memory bounds and not whole-MCU utilization.

These values belong to the canonical campaign at
`2026-08-27T20:28:40.473505+02:00`. The secondary campaign at
`2026-08-27T21:35:29.587814+02:00` used the same build hashes and is preserved
in `measurements/val_req_027_campaign_2026-08-27_213529.txt`. Its different
observed maxima are retained as empirical repeatability evidence and do not
replace the canonical PHASE 15 values.

### Communication and recovery evidence

- `measurements/comm_health.csv`: five healthy recorded samples with zero CRC, timeout and overflow counter increments.
- `measurements/fault_injection_comm.csv`: bad-CRC and partial-frame timeout injections each produced the expected counter delta and communication recovery.
- Controlled watchdog test supplied by the user: initial marker 0, controlled stall, MCU recovered, PING recovered, watchdog marker asserted; PASS. The reported raw reset-cause value `0xF7` is informational and is not treated as WDRF proof.
- Integrated DC motor test supplied by the user: IDLE stop, ACTIVE forward rotation, SAFE_STATE stop, and latched SAFE_STATE remains stopped; PASS.

### Electrical safety evidence

- Arduino logic rail: nominal 5 V; measured approximately 4.8 V.
- External actuator rail: nominal 5 V; measured approximately 4.9 V.
- Adapter photo marking: nominal 5.0 V DC / 2.4 A; this is not a measured prototype value.
- User-confirmed pre-power checklist: 10/10 PASS, dated 2026-08-27, validation-session sign-off confirmed.
- Common ground, correct polarities, external/driver actuator power paths, no direct GPIO actuator power, and no mains connection/switching: PASS by the supplied inspection record.
- Four final photographs are present and reviewed as complementary evidence; they do not prove hidden electrical nodes.
- Complete actuator smoke test, integrated operation, SAFE_STATE behavior, and watchdog safe/recovery test: PASS by supplied physical evidence.

## Final Validation Decision

**FINAL SYSTEM VALIDATION COMPLETED — PASS (2026-08-27)**

All 29 MUST requirements are classified SATISFIED, there are no blocking MUST evidence gaps, and the user-supplied real final end-to-end campaign passed. The identified final build, seven-class measurement report, and electrical evidence package are persisted and indexed in `docs/validation/final_system_validation_report.md`.

This result applies to the approved PHASE 15 experimental validation scope. It
does not claim product certification, SIL/ASIL compliance, EMC compliance,
mains suitability, or guaranteed real-time/memory bounds.

## Remaining Actions

1. Preserve the final report, build hashes, measurement record, physical evidence, and stated limitations as one traceable evidence set.
2. Preserve the observed HC-SR04 physical switching-boundary characterization without claiming centimetre-level calibration.
3. Treat later firmware, wiring, or hardware changes as a new validation baseline requiring impact review and proportionate regression.

No MUST validation action remains open. SHOULD work remains optional and non-blocking.
