# SENTRY-CELL UNO — Final System Validation Report

## 1. Validation Scope

This report freezes the traceability of the real PHASE 15 validation evidence
available on 2026-08-27 for the integrated SENTRY-CELL UNO prototype. It covers
the authoritative MUST requirements, the identified final firmware build, the
user-performed end-to-end hardware campaign, communication, local safety,
watchdog recovery, diagnostics, performance/memory observations, and
low-voltage electrical evidence.

No firmware or supervisor code was changed, and no build or upload was
performed while creating this report. Results identified as physical are the
explicit real observations supplied by the user; repository artifacts are
identified separately. No missing test or measurement is inferred.

## 2. Authoritative Requirements Baseline

The authoritative baseline is
[`docs/requirements/validation_requirements_v1.md`](../requirements/validation_requirements_v1.md).
Repository parsing confirms:

- Total VAL-REQ: **35**
- MUST: **29**
- SHOULD: **6**
- Open baseline decisions: **NONE**

This baseline does not retroactively replace the absent historical
SYS-REQ-001..045 set.

## 3. Final Build Identification

The files currently present in `build/` were read and hashed without rebuilding.
Their SHA-256 values match the canonical campaign, secondary repeatability
campaign, and campaign index records.

| Artifact | SHA-256 |
|---|---|
| `build/sentry-cell-uno.elf` | `3f32ace4f15895fd14b350d09de855f17ae7fb69e71fd79983825056bb163d59` |
| `build/sentry-cell-uno.hex` | `3c18c0c317c7738c0dfd4104fdda4411734061da2c08ef3a4d29a1bfb46f4f4d` |
| `build/sentry-cell-uno.map` | `3a03c351d26b18f73e72a1c34378d52ffe5df907251f9b52024892a363ed8d10` |

Current `avr-size` evidence persisted for this build:

| `.text` | `.data` | `.bss` | `dec` |
|---:|---:|---:|---:|
| 6886 bytes | 10 bytes | 280 bytes | 7176 bytes |

The canonical PHASE 15 measurement artifact is
[`measurements/val_req_027_campaign_2026-08-27_202840.txt`](../../measurements/val_req_027_campaign_2026-08-27_202840.txt).
The later same-build repeatability artifact is
[`measurements/val_req_027_campaign_2026-08-27_213529.txt`](../../measurements/val_req_027_campaign_2026-08-27_213529.txt).
[`measurements/val_req_027_current_build.txt`](../../measurements/val_req_027_current_build.txt)
is the traceability index for these two immutable records.

## 4. Validation Environment

- Target: ATmega328P-based SENTRY-CELL UNO experimental prototype.
- Logic rail: nominal 5 V, measured approximately 4.8 V.
- External actuator rail: nominal 5 V, measured approximately 4.9 V.
- Logic and actuator grounds: common, user inspection PASS.
- Communication: Arduino USB serial link to the Python standard-library
  supervisor.
- Integrated devices in scope: button, LED, HC-SR04, thermistor raw channel,
  stepper/ULN2003, servo, DC motor/L293D, and relay/PN2222 stage.
- Evidence-freeze date: 2026-08-27.

The adapter photograph shows a nominal 5.0 V DC / 2.4 A marking. That label is
not a measurement of either prototype rail or of prototype current.

## 5. Requirement Status Summary

MUST disposition after evidence review:

| Disposition | Count |
|---|---:|
| SATISFIED | 29 |
| PARTIAL | 0 |
| NOT SATISFIED | 0 |
| UNKNOWN | 0 |

Blocking MUST gaps: **NONE**.

Satisfied MUST requirements (29): VAL-REQ-001, VAL-REQ-002, VAL-REQ-003,
VAL-REQ-004, VAL-REQ-005, VAL-REQ-006, VAL-REQ-007, VAL-REQ-008,
VAL-REQ-009, VAL-REQ-010, VAL-REQ-011, VAL-REQ-012, VAL-REQ-013,
VAL-REQ-014, VAL-REQ-015, VAL-REQ-016, VAL-REQ-017, VAL-REQ-018,
VAL-REQ-019, VAL-REQ-020, VAL-REQ-021, VAL-REQ-022, VAL-REQ-023,
VAL-REQ-024, VAL-REQ-025, VAL-REQ-026, VAL-REQ-027, VAL-REQ-028, and
VAL-REQ-030.

The six SHOULD requirements remain separate and non-blocking:

| Requirement | Current evidence state | Scope |
|---|---|---|
| VAL-REQ-029 | PLANNED | Calibrated thermal action remains deferred; raw ADC acquisition is retained without a Celsius claim. |
| VAL-REQ-031 | PLANNED | Supervisor communication-loss warning remains optional; local MCU safety is autonomous. |
| VAL-REQ-032 | PLANNED | Additional LCD/RGB/buzzer HMI was not selected as mandatory. |
| VAL-REQ-033 | PLANNED | DHT11 acquisition was not selected as mandatory. |
| VAL-REQ-034 | PLANNED | A bounded multi-event history remains optional. |
| VAL-REQ-035 | TESTED | The existing controlled watchdog fault injection is tested; a broader command set is optional. |

The per-requirement source and evidence matrix remains in
[`docs/validation/validation_readiness.md`](validation_readiness.md).

## 6. Final End-to-End Validation Scenario

The user reported the following real final integrated campaign:

| Step | Expected integrated behavior | Observed result |
|---|---|---|
| BOOT/RESET | Transition to IDLE | PASS |
| IDLE | Stepper STOP, DC motor STOP, relay OFF, servo SAFE | PASS |
| ACTIVE | Stepper RUN, DC motor RUN, relay ON, servo ACTIVE | PASS |
| Critical obstacle at approximately 10–15 cm | Enter SAFE_STATE | PASS |
| SAFE_STATE outputs | Stepper STOP, DC motor STOP, relay OFF, servo SAFE | PASS |
| SAFE_STATE diagnostics | Diagnostic indication available | PASS |
| Obstacle removed and D2 pressed | SAFE_STATE remains latched; no actuator restart | PASS |
| Reset after SAFE_STATE | Return to IDLE with safe outputs after reboot | PASS |

All end-to-end steps supplied for this final campaign passed.

## 7. Safety Validation

### Logical boundary

The real production function in `firmware/safety/safety.c` was exercised by
`tests/test_safety.c`: **8/8 PASS**. The test covers invalid input, 0 cm, 1 cm,
19 cm, 20 cm, 21 cm, and a large value as required by the boundary criterion.
The software decision operates on the integer distance value supplied to the
Safety module: only a valid value in the logical 1–20 cm range raises the
critical obstacle event while ACTIVE.

### Physical characterization

The supplied physical observations were:

| Mechanical reference | Observed system state |
|---:|---|
| 25 cm | ACTIVE ×3 |
| 22 cm | ACTIVE ×3 |
| 21 cm | SAFE ×3 |
| 20 cm | SAFE ×3 |
| 19 cm | SAFE ×3 |
| 18 cm | SAFE ×3 |

Fine characterization found SAFE from 21.2 to 21.8 cm and ACTIVE from 22.0 to
22.1 cm. The observed physical switching boundary is therefore approximately
21.8–22.0 cm. This is retained as a sensor/system measurement characteristic;
it is not represented as centimetre-level sensor calibration and does not
change the logical `distance_cm <= 20` safety threshold.

### Latched safe behavior

The final end-to-end campaign confirmed that the critical obstacle enters
SAFE_STATE, stops or safes all actuators, retains diagnostic indication, ignores
the D2 start/stop request while latched, and returns to IDLE with safe outputs
only after reset.

### Diagnostic retention

The real production diagnostics module was exercised by
`tests/test_diagnostics.c`: **8/8 PASS**. Initial state, fault recording, last-
fault retention across repeated reads, and fault-count retention across
repeated reads passed. Read operations are non-destructive.

## 8. Watchdog / Recovery Validation

The real controlled watchdog campaign supplied by the user recorded:

| Check | Result |
|---|---|
| Controlled firmware block | PASS |
| MCU recovered | PASS |
| PING after watchdog reset | PASS |
| Persistent watchdog-timeout marker | PASS |

The raw boot reset-cause value was `0xF7`. It is retained as informational only
and is not interpreted as WDRF proof. The persistent timeout marker and the
observed controlled-stall recovery provide the recorded watchdog validation
evidence.

## 9. Communication Validation

The final real communication campaign supplied by the user recorded:

| Check | Result |
|---|---|
| PING/PONG | PASS |
| ECHO/ACK | PASS |
| Protocol checks | PASS |
| Serial link | PASS |
| Supervisor bring-up | PASS |

Persisted communication-health and fault-injection records are available in
`measurements/comm_health.csv` and
`measurements/fault_injection_comm.csv`. The supervisor test suite sources are
listed in the evidence index.

## 10. Timing and CPU Measurements

The identified final-build single-session measurement scenario was IDLE for
approximately 5 s, ACTIVE for approximately 10 s, and SAFE_STATE for
approximately 5 s. The host timed the scenario instructions; the measurement
record does not claim automatic FSM-state detection.

The values below are from the canonical campaign at
`2026-08-27T20:28:40.473505+02:00`. A later repeatability run at
`2026-08-27T21:35:29.587814+02:00` used the same ELF, HEX, and map identities
and produced different observed maxima. This is expected empirical run-to-run
variation and does not invalidate or replace the canonical PHASE 15 campaign.

### observed execution-time maxima

| Scheduled task | Maximum Timer1 ticks | Observed maximum |
|---|---:|---:|
| Actuator | 44 | 22 us |
| Control | 103 | 51.5 us |
| Sensor/Safety | 435 | 217.5 us |
| Communication | 156 | 78 us |

These are observed execution-time maxima from the recorded campaign, not WCET
guarantees.

### observed maximum jitter at 1 ms measurement resolution

| Scheduled task | Observed maximum |
|---|---:|
| Actuator | 0 ms |
| Control | 0 ms |
| Sensor/Safety | 0 ms |
| Communication | 0 ms |

No jitter of 1 ms or greater was observed. Sub-millisecond timing variation is
unresolved because measurement resolution is limited to 1 ms.

### observed scheduled-task CPU utilization

- Busy ticks: **645926**
- Elapsed firmware time: **20700 ms**
- Observed scheduled-task CPU utilization: **1.6%**

The 1.6% result covers scheduled-task execution only; ISR execution and
scheduler overhead are excluded.

### observed execution overruns

| Scheduled task | Observed overruns |
|---|---:|
| Actuator | 0 |
| Control | 0 |
| Sensor/Safety | 0 |
| Communication | 0 |

No execution overrun was observed during the campaign; this is not a guarantee
for all possible executions.

## 11. Memory Measurements

### Flash and static SRAM

| Measurement | Result |
|---|---:|
| Flash used (`text + data`) | 6896 / 32768 bytes (21.04%) |
| Static SRAM (`data + bss`) | 290 / 2048 bytes (14.16%) |

Static SRAM excludes runtime stack and heap use.

### observed minimum free SRAM watermark

| Measurement | Result |
|---|---:|
| Painted region | 1721 bytes |
| Used painted region | 62 bytes |
| Observed minimum free SRAM watermark | 1659 bytes |

This watermark is empirical for the recorded campaign and is not a lower bound
for all possible executions.

## 12. Electrical Safety Evidence

The final low-voltage evidence package records:

- Arduino logic rail: nominal 5 V, measured approximately 4.8 V.
- External actuator rail: nominal 5 V, measured approximately 4.9 V.
- Common Arduino/actuator ground: inspection PASS.
- Pre-power checklist: 10/10 PASS, dated 2026-08-27, with explicit
  validation-session user sign-off.
- Servo powered externally with D9 as signal only.
- Stepper powered through ULN2003 with D3–D6 as command signals.
- DC motor powered through L293D with D10/D12 as command signals.
- Relay coil driven through resistor, PN2222, and flyback diode with D11 as the
  command signal.
- No power actuator driven directly from GPIO: PASS.
- Complete actuator smoke test and integrated operation: PASS.
- Low-voltage only and no mains switching: PASS.

Four final photographs are present: overall system, breadboard/driver wiring,
actuators, and the adapter nominal marking. The photographs are complementary
evidence and cannot establish the state of every hidden electrical node.

Detailed traceability is in
[`docs/hardware/electrical_safety_evidence.md`](../hardware/electrical_safety_evidence.md)
and [`docs/validation/pre_power_checklist.md`](pre_power_checklist.md).

## 13. Known Limitations

- Experimental prototype only; not SIL or ASIL certified.
- The HC-SR04 physical switching boundary was observed around 21.8–22.0 cm
  despite the logical threshold `distance_cm <= 20`, due to sensor/system
  measurement characteristics.
- No centimetre-level sensor calibration is claimed.
- Observed scheduled-task CPU utilization excludes ISR and scheduler overhead.
- Jitter observations are limited to 1 ms measurement resolution.
- The runtime SRAM watermark is empirical and is not a guaranteed minimum.
- No detailed current-consumption profiling was performed.
- No guaranteed brownout or electrical-noise margin is claimed.
- No EMC/EMI certification exists.
- No mains switching is present, permitted, or validated.
- Photo review cannot verify hidden electrical nodes.
- Raw boot reset cause `0xF7` is informational and is not interpreted as WDRF.
- Observed execution-time maxima and overruns are campaign results, not proofs
  for all possible executions.

## 14. Final Validation Decision

The repository evidence confirms:

- 29/29 MUST requirements SATISFIED;
- no blocking MUST gap;
- the supplied real final end-to-end campaign PASS;
- exact identification of the current final ELF, HEX, and map artifacts;
- persistence of all seven required current-build measurement classes; and
- persistence of the complete VAL-REQ-028 electrical evidence package.

**FINAL SYSTEM VALIDATION: PASS**

The six SHOULD requirements are non-blocking under the approved baseline. This
decision validates the defined PHASE 15 experimental scope and does not claim
product certification, SIL/ASIL compliance, EMC compliance, mains suitability,
or guaranteed real-time/memory bounds.

## 15. Evidence Index

All paths below were confirmed present when this report was created.

### Requirements and validation records

- `docs/requirements/validation_requirements_v1.md`
- `docs/validation/validation_readiness.md`
- `docs/validation/final_system_validation_report.md`
- `docs/validation/pre_power_checklist.md`
- `docs/hardware/electrical_safety_evidence.md`

### Electrical photographs

- `docs/hardware/photos/final_system_overview.png`
- `docs/hardware/photos/final_breadboard_wiring.png`
- `docs/hardware/photos/final_actuators.png`
- `docs/hardware/photos/final_power_supply.png`

### Measurements and communication records

- `measurements/val_req_027_current_build.txt` (campaign index)
- `measurements/val_req_027_campaign_2026-08-27_202840.txt` (canonical PHASE 15 campaign)
- `measurements/val_req_027_campaign_2026-08-27_213529.txt` (secondary repeatability campaign)
- `measurements/comm_health.csv`
- `measurements/fault_injection_comm.csv`

### Production-module and supervisor tests

- `tests/test_safety.c`
- `tests/test_diagnostics.c`
- `supervisor/tests/test_protocol.py`
- `supervisor/tests/test_monitoring.py`
- `supervisor/tests/test_fault_injection.py`
- `supervisor/tests/test_validation_campaign.py`

### Identified build artifacts

- `build/sentry-cell-uno.elf`
- `build/sentry-cell-uno.hex`
- `build/sentry-cell-uno.map`
