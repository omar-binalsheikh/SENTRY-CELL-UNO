# SENTRY-CELL UNO — Testing and Validation

## 1. Purpose

This document describes the test, measurement, fault-injection, and physical
validation strategy actually used for SENTRY-CELL UNO. It consolidates existing
repository evidence without replacing the authoritative requirement matrix or
the final validation report.

The approved PHASE 15 baseline contains 35 VAL-REQ requirements: 29 MUST and 6
SHOULD. The recorded final disposition is **29/29 MUST SATISFIED** with no
blocking MUST gap.

## 2. Test philosophy and evidence states

The project uses this traceability chain:

```text
Requirement → Implementation → Test → Measurement → Result → PASS / FAIL
```

The chain is evidence-based: source presence alone is not treated as proof of
physical behavior, and a measurement is reported only within the scope of the
campaign that produced it.

| State | Meaning in this project |
|---|---|
| `PLANNED` | Required or intentionally deferred work has no implementation evidence yet |
| `IMPLEMENTED` | The behavior is present in source, without sufficient build/test evidence for the acceptance criterion |
| `COMPILED` | The implementation is present in a successfully built identified firmware baseline |
| `TESTED` | A defined software or hardware test exercised the behavior |
| `MEASURED` | Persisted quantitative results exist with a stated scope |
| `VALIDATED` | Explicit successful real-system evidence supports the acceptance behavior |

These labels are not interchangeable. In particular, `COMPILED` does not imply
physical validation, and empirical `MEASURED` data does not imply a guaranteed
bound.

## 3. Verification levels used

| Level used | Actual scope |
|---|---|
| Host-side C production-module tests | Real Safety and diagnostics C modules compiled into small host test programs |
| Python Supervisor unit tests | Frame codec, payload decoders, monitoring/fault helpers, serial abstraction, and validation-campaign tooling |
| Firmware module bring-up | GPIO, time base, scheduler, ADC/thermistor, HC-SR04, actuator, UART, protocol, and watchdog steps |
| Communication protocol tests | Real UART TX/RX, framed request/response, parser errors, recovery, rings, and counters |
| Integration and physical hardware tests | Individual actuators, integrated outputs, state transitions, and low-voltage system behavior |
| Safety tests | Deterministic logical boundary test plus physical obstacle-to-SAFE characterization |
| Fault injection | Bad CRC, partial-frame timeout, and controlled watchdog stall/reset |
| Timing and performance profiling | Task execution maxima, jitter, scheduled-task utilization, and overrun observations |
| Memory profiling | Final-build Flash/static SRAM plus runtime painted-SRAM watermark |
| Final end-to-end validation | BOOT/IDLE/ACTIVE/SAFE_STATE behavior, latching, reset recovery, and communication regression |

No additional test level, certification activity, or unrecorded campaign is
implied.

## 4. Host-side C production-module tests

### Safety boundary test

[`tests/test_safety.c`](../../tests/test_safety.c) calls the real production
function `safety_obstacle_is_critical()` from `firmware/safety/safety.c`. It
does not duplicate the decision logic.

| Case | Expected critical result |
|---|---:|
| `valid=0`, distance 0 cm | No |
| `valid=0`, distance 20 cm | No |
| `valid=1`, distance 0 cm | No |
| `valid=1`, distance 1 cm | Yes |
| `valid=1`, distance 19 cm | Yes |
| `valid=1`, distance 20 cm | Yes |
| `valid=1`, distance 21 cm | No |
| `valid=1`, distance 65535 cm | No |

Recorded result: **8/8 PASS**. The verified software rule is that a valid
integer distance from 1 through 20 cm is critical.

### Diagnostics retention test

[`tests/test_diagnostics.c`](../../tests/test_diagnostics.c) calls the real
production diagnostics module. Its eight cases cover:

- initialized no-fault state and zero count;
- ignoring `DIAG_FAULT_NONE`;
- recording the critical obstacle fault;
- retaining last fault through repeated reads;
- retaining fault count through repeated reads;
- ignoring a duplicate of the already retained fault, so the count remains 1;
- resetting state through `diagnostics_init()`; and
- recording a new first event after reinitialization.

Recorded result: **8/8 PASS**. Getter reads are non-destructive.

The two production-module tests can be reproduced with a C11 host compiler;
the executables are kept outside the repository:

```bash
cc -std=c11 -Wall -Wextra -Werror -Ifirmware \
  tests/test_safety.c firmware/safety/safety.c \
  -o /tmp/sentry-cell-test-safety
/tmp/sentry-cell-test-safety

cc -std=c11 -Wall -Wextra -Werror -Ifirmware \
  tests/test_diagnostics.c firmware/diagnostics/diagnostics.c \
  -o /tmp/sentry-cell-test-diagnostics
/tmp/sentry-cell-test-diagnostics

rm -f /tmp/sentry-cell-test-safety /tmp/sentry-cell-test-diagnostics
```

## 5. Python Supervisor tests

The current `unittest` discovery count is **82 tests** in five files. The full
suite was most recently re-run during PHASE 16 — ÉTAPE 12A with **82/82 PASS**.

| File | Current test count | Confirmed coverage |
|---|---:|---|
| [`test_protocol.py`](../../supervisor/tests/test_protocol.py) | 43 | CRC vector, frame encode/decode, payload limits, status lengths and little-endian decoding, timing/CPU calculations, reset/watchdog helpers, malformed frames, and `SerialLink.read_exact()` behavior using host pipes |
| [`test_monitoring.py`](../../supervisor/tests/test_monitoring.py) | 4 | Monitoring argument validation, sequence wrap, and exact CSV output |
| [`test_fault_injection.py`](../../supervisor/tests/test_fault_injection.py) | 7 | Counter-delta/recovery verdicts, saturation guard, and exact fault-injection CSV output |
| [`test_validation_campaign.py`](../../supervisor/tests/test_validation_campaign.py) | 13 | Artifact hashing, missing-artifact failure, required observational wording, exclusive timestamped evidence creation, deterministic collision handling, preservation of existing evidence, one-connection five-query collection, CLI exposure, and fail-before-serial behavior |
| [`test_dashboard.py`](../../supervisor/tests/test_dashboard.py) | 15 | Snapshot serialization, cached HTTP API and static UI serving, path-traversal rejection, bounded history/event log, one persistent serial session, RX-timeout settling and stale-data purge without reopen/DTR changes, header and partial-payload timeouts, late-tail contamination removal, full-interval scheduling after failure, visible timeout state, and later connection recovery |

These are host tests and do not substitute for real serial or hardware tests.
The serial-recovery cases are deterministic host simulations; they verify the
Supervisor recovery behavior but do not claim that a physical USB transport
timeout has been eliminated.

## 6. Communication testing

The validation record contains the following real communication evidence:

- USART0 TX and RX physical bring-up: PASS.
- RX interrupt ring-buffer burst test: PASS.
- PING/PONG: PASS.
- ECHO/ACK: PASS.
- ACK/NACK protocol behavior: PASS.
- Bad-CRC rejection and subsequent communication recovery: PASS.
- Partial-frame timeout and parser recovery/resynchronization: PASS.
- Communication counter telemetry: PASS.
- Supervisor serial bring-up and human-readable telemetry: PASS.

[`measurements/comm_health.csv`](../../measurements/comm_health.csv) contains
five samples with sequences 64 through 68. All five recorded zero UART RX
overflow, zero parser timeout, and zero CRC-error counts during that monitoring
window.

[`measurements/fault_injection_comm.csv`](../../measurements/fault_injection_comm.csv)
contains two real fault injections:

| Fault ID | Injection | Expected evidence | Persisted result |
|---|---|---|---|
| `FI-COM-001` | Corrupted CRC | CRC counter 0 → 1 and recovery PING | PASS |
| `FI-COM-002` | Partial frame followed by timeout | Timeout counter 0 → 1 and recovery PING | PASS |

Bad CRC and timeout cases intentionally produce no protocol response to the bad
candidate frame; recovery is demonstrated with a subsequent valid PING/PONG.

## 7. Safety testing

### Logical boundary

The production Safety unit test establishes the logical rule:

```text
valid != 0 and 1 <= integer distance_cm <= 20 → critical obstacle fault
```

Result: **8/8 PASS**.

### Physical obstacle characterization

The user-supplied repeated physical observations are:

| Mechanical reference | Observed state |
|---:|---|
| 25 cm | ACTIVE ×3 |
| 22 cm | ACTIVE ×3 |
| 21 cm | SAFE ×3 |
| 20 cm | SAFE ×3 |
| 19 cm | SAFE ×3 |
| 18 cm | SAFE ×3 |

Fine characterization recorded SAFE from 21.2 through 21.8 cm and ACTIVE from
22.0 through 22.1 cm. The observed switching boundary is therefore about
21.8–22.0 cm.

This is an observed **sensor/system switching characteristic**, not evidence of
centimetre-level HC-SR04 calibration. It does not change the logical integer
Safety threshold.

### Latched safe behavior

The integrated physical campaign confirmed that a critical obstacle in ACTIVE
enters `SAFE_STATE`, safes/stops all actuators, provides diagnostic indication,
ignores D2 and obstacle removal while latched, and returns to safe IDLE only
after reset.

## 8. Fault injection

### Communication faults

The two persisted communication injections exercise integrity rejection,
timeout recovery, the expected counter increments, and post-fault PING/PONG.
Their recorded results are summarized in Section 6.

### Controlled watchdog reset

The real watchdog campaign follows this path:

```text
controlled firmware block
    → safe outputs applied
    → watchdog interrupt
    → persistent .noinit markers written
    → hardware watchdog reset
    → reboot to safe IDLE
    → PING communication recovery
    → persistent watchdog marker detected
```

Recorded results: controlled block PASS, MCU recovery PASS, post-reset PING
PASS, and persistent watchdog-timeout marker PASS.

The raw reset-cause value observed after the test was `0xF7`. It is retained as
informational data only and is **not** interpreted as WDRF proof. The validated
evidence is the controlled recovery together with the bootloader-independent
persistent watchdog marker.

## 9. Timing and real-time measurements

The canonical record is
[`measurements/val_req_027_campaign_2026-08-27_202840.txt`](../../measurements/val_req_027_campaign_2026-08-27_202840.txt).
It identifies the final ELF, HEX, and map and records this host-timed scenario:

```text
IDLE        approximately 5 s
ACTIVE      approximately 10 s
SAFE_STATE  approximately 5 s
```

The host issued timing instructions; the campaign did not automatically detect
FSM states.

| Metric | Canonical observed result | Qualification |
|---|---:|---|
| Actuator task maximum | 44 Timer1 ticks = 22 µs | Observed execution-time maximum |
| Control task maximum | 103 ticks = 51.5 µs | Observed execution-time maximum |
| Sensor/Safety task maximum | 435 ticks = 217.5 µs | Observed execution-time maximum |
| Communication task maximum | 156 ticks = 78 µs | Observed execution-time maximum |
| Scheduler start jitter | No jitter ≥1 ms observed for any task | Resolution is 1 ms; sub-millisecond variation is unresolved |
| Scheduled-task CPU utilization | 1.6% | Excludes ISR execution and scheduler overhead |
| Execution overruns | None observed for all four tasks | Campaign observation, not an all-execution guarantee |

These execution maxima are empirical and do not constitute a WCET proof. The secondary
same-build repeatability campaign is preserved separately in
[`measurements/val_req_027_campaign_2026-08-27_213529.txt`](../../measurements/val_req_027_campaign_2026-08-27_213529.txt);
its different observed maxima do not replace the canonical campaign.

## 10. Memory measurements

The identified final build has:

| Metric | Result | Scope |
|---|---:|---|
| Flash | 6896 / 32768 bytes = 21.04% | `text + data` |
| Static SRAM | 290 / 2048 bytes = 14.16% | `data + bss`; excludes runtime stack/heap use |
| Painted runtime SRAM region | 1721 bytes | Canary-painted campaign region |
| Used painted region | 62 bytes | Maximum observed consumption within the painted region |
| Minimum free SRAM observed | 1659 bytes | Empirical runtime watermark |

The 1659-byte value is an observed watermark from the canonical campaign, not
a guaranteed worst-case free-SRAM bound.

`measurements/memory_static.txt` is retained as historical evidence for an
earlier 5082/10/245 build and is not used as the final-build static-memory
result.

## 11. Electrical and hardware validation

The low-voltage validation package records:

- complete actuator smoke test: PASS;
- complete integrated system operation: PASS;
- pre-power checklist: **10/10 PASS**, dated 2026-08-27, with validation-session
  user sign-off confirmed;
- Arduino logic rail measured at approximately 4.8 V;
- external actuator rail measured at approximately 4.9 V;
- common Arduino and actuator-supply ground: inspection PASS;
- servo powered externally with D9 as signal only;
- stepper driven through ULN2003;
- DC motor driven through L293D;
- relay coil driven through resistor, PN2222, and flyback diode;
- no power actuator supplied directly by GPIO; and
- low-voltage-only operation with no mains switching.

Four final photographs are present under `docs/hardware/photos/`: overall
system, breadboard/driver wiring, actuators, and the nominal adapter marking.
They are complementary evidence and do not prove hidden electrical nodes.

No prototype current consumption was measured. The adapter's 2.4 A marking is
a nominal label, not a current measurement.

See the [Electrical Safety Evidence](../hardware/electrical_safety_evidence.md)
and [Pre-Power Checklist](../validation/pre_power_checklist.md).

## 12. Final end-to-end campaign

The user-reported integrated campaign produced:

| Step | Observed result |
|---|---|
| BOOT / reset → IDLE | PASS |
| IDLE safe outputs: stepper STOP, DC motor STOP, relay OFF, servo SAFE | PASS |
| D2 request → ACTIVE | PASS |
| ACTIVE outputs: stepper RUN, DC motor RUN, relay ON, servo ACTIVE | PASS |
| Critical obstacle at approximately 10–15 cm → SAFE_STATE | PASS |
| SAFE_STATE: stepper STOP, DC motor STOP, relay OFF, servo SAFE | PASS |
| Diagnostic indication available in SAFE_STATE | PASS |
| Obstacle removed and D2 pressed: no actuator restart | PASS |
| Hardware reset → IDLE with safe outputs | PASS |
| PING/PONG regression | PASS |
| ECHO/ACK regression | PASS |

This campaign supports the final experimental validation decision. It is not a
product safety certification.

## 13. Compact evidence traceability

| Verification area | Primary evidence | Recorded result |
|---|---|---|
| Safety logic | `tests/test_safety.c` and final report | 8/8 PASS |
| Diagnostics retention | `tests/test_diagnostics.c` and final report | 8/8 PASS |
| Python Supervisor unit sources | Five files under `supervisor/tests/` | 82 tests discovered and 82/82 PASS in PHASE 16 — ÉTAPE 12A |
| UART and binary protocol | Validation readiness, Supervisor tests, communication CSV records | Physical TX/RX, burst, PING/PONG, ECHO/ACK/NACK, CRC and timeout/recovery PASS |
| Watchdog | Final report and controlled physical campaign | Recovery, PING, and persistent marker PASS |
| Execution timing | Canonical VAL-REQ-027 campaign | Four observed maxima recorded |
| Scheduler jitter | Canonical VAL-REQ-027 campaign | No jitter ≥1 ms observed |
| Scheduled-task CPU | Canonical VAL-REQ-027 campaign | 1.6%, excluding ISR/scheduler overhead |
| Execution overruns | Canonical VAL-REQ-027 campaign | None observed for all four tasks |
| Flash and SRAM | Canonical VAL-REQ-027 campaign | 6896-byte Flash, 290-byte static SRAM, 1659-byte observed runtime watermark |
| Electrical safety | Electrical evidence, checklist, measurements, and photos | 10/10 inspection PASS; low-voltage integrated evidence complete |
| End-to-end system | Final physical campaign and final report | BOOT → IDLE → ACTIVE → SAFE_STATE → reset/IDLE PASS |

The complete 35-row requirement/evidence matrix remains in
`docs/validation/validation_readiness.md`; it is intentionally not duplicated
here.

## 14. Reproducible commands

### Python unit suite

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s supervisor/tests -v
```

### Supervisor protocol and evidence modes

```bash
# PING/PONG and ECHO/ACK
python3 supervisor/main.py --port /dev/cu.usbmodem1101

# Communication status
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --status

# Finite communication monitoring with CSV
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --monitor

# Bad-CRC and partial-frame fault injection
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --fault-injection-comm

# Controlled watchdog reset test
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --watchdog-test

# Single-session IDLE/ACTIVE/SAFE profiling campaign
python3 supervisor/main.py --port /dev/cu.usbmodem1101 --validation-profile
```

The serial path is an example only and must be replaced by the exact discovered
port. Opening the port may reset the UNO. Fault-injection and validation-profile
modes alter runtime state and/or evidence files and must be run only as planned
validation actions. `--validation-profile` creates a new exclusive, timestamped
`measurements/val_req_027_campaign_YYYY-MM-DD_HHMMSS.txt` file, adding a numeric
suffix on collision. Existing campaign evidence is never overwritten. The
canonical PHASE 15 campaign is immutable, and
`measurements/val_req_027_current_build.txt` remains its curated traceability
index rather than a runtime output path.

The host-side C commands are documented in Section 4 and create executables in
`/tmp` only.

## 15. Known test limitations

- Timing and task-overrun results are empirical campaign observations.
- Jitter measurement resolution is 1 ms; sub-millisecond variation is unknown.
- The reported 1.6% utilization excludes ISR and scheduler overhead and is not
  total MCU utilization.
- The runtime SRAM watermark is empirical and not a guaranteed minimum.
- HC-SR04 physical distance is not calibrated to centimetre-level accuracy.
- No formal WCET proof exists.
- No detailed current-consumption campaign exists.
- No long-duration endurance campaign is recorded.
- No EMC/EMI test or certification exists.
- No guaranteed brownout or electrical-noise margin is claimed.
- Photographs cannot verify every hidden connection, polarity, or electrical
  node.
- Host-side tests do not replace physical hardware validation.
- The prototype and its process are not SIL- or ASIL-certified.
- No mains switching is present, permitted, or validated.

## 16. Related documentation

- [Project README](../../README.md)
- [System Architecture](../architecture/system_architecture.md)
- [Binary UART Protocol](../protocol/uart_binary_protocol.md)
- [Final System Validation Report](../validation/final_system_validation_report.md)
