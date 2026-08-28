# SENTRY-CELL UNO — Electrical Safety Evidence

## Scope

SENTRY-CELL UNO is an experimental low-voltage prototype. It is not SIL- or
ASIL-certified safety hardware. The validated installation has no connection
to 230 V or any other mains circuit, including through the relay contacts.

A commercial adapter may itself connect to mains. Only its low-voltage DC
output powers the prototype; the prototype does not expose, route, or switch
mains voltage.

This document records only evidence explicitly supplied by the user and files
actually present in the repository. A photograph is complementary evidence and
does not prove the state of electrical nodes or connections hidden from view.

## Power Architecture and Measurements

| Rail or source | Nominal value | Measured value | Evidence scope |
|---|---:|---:|---|
| Arduino logic rail | 5 V | approximately 4.8 V | User multimeter measurement from the validation session |
| External actuator rail | 5 V | approximately 4.9 V | User multimeter measurement from the validation session |
| Commercial adapter output rating | 5.0 V DC / 2.4 A | NOT MEASURED by the label | Nominal marking visible in `photos/final_power_supply.png` |

The measured rail values are approximately 4.8 V and approximately 4.9 V. The
5 V descriptions are nominal supply ratings, and 2.4 A is the adapter's nominal
output-current marking, not a current measurement of the prototype.

The final validated power architecture is:

- Arduino and logic operate from the nominal 5 V logic supply measured at
  approximately 4.8 V.
- Actuators use a separate nominal 5 V external supply measured at
  approximately 4.9 V.
- Arduino ground and external actuator-supply ground are connected together;
  user pre-power inspection: PASS.
- USB provides the serial connection to the Python supervisor.
- MCU GPIO pins carry control signals only; they do not supply actuator power.

No measured current, detailed current-consumption result, or power-consumption
value is claimed.

```text
Arduino/logic nominal 5 V (measured approximately 4.8 V)
        |
        +-- ATmega328P logic and GPIO control signals

External actuator nominal 5 V (measured approximately 4.9 V)
        |
        +-- SG90 servo power
        +-- ULN2003 + stepper power
        +-- L293D + DC motor power
        +-- PN2222 transistor stage + relay coil power

Arduino GND ---------------- common ground ---------------- actuator-supply GND
USB serial ----------------- Python supervisor
```

## Actuator Power Paths

The separation described here is between MCU control signals and actuator
power paths; it is not a claim of galvanic isolation.

### Servo

- D9 is the control signal only.
- Servo power comes from the external nominal 5 V actuator rail.
- Servo and Arduino share the common ground.
- The GPIO does not power the servo.

### Stepper

- D3–D6 drive the ULN2003 command inputs IN1–IN4 only.
- The ULN2003 driver switches the stepper phases.
- Motor power comes from the external nominal 5 V actuator rail.
- The stepper phases are not powered directly by MCU GPIO pins.

### DC Motor

- D10 and D12 drive the L293D command inputs only.
- The L293D driver switches the motor.
- Motor power comes from the external nominal 5 V actuator rail.
- The DC motor is not powered directly by MCU GPIO pins.

### Relay

- D11 drives a resistor connected to the PN2222 transistor base.
- The PN2222 switches the low-voltage relay coil.
- A flyback diode is installed across the relay coil.
- The GPIO does not directly drive or power the relay coil.
- Relay use is low voltage only; no relay contact is connected to mains and no
  mains switching is permitted or validated.

## Safety Rules

- Never connect relay contacts to 230 V mains.
- Low-voltage prototype only.
- Power OFF before rewiring.
- Common ground required between logic and actuator supply.
- Do not power an actuator from an Arduino GPIO.
- External actuator power should be OFF during firmware upload when practical.
- Check polarity before power-on.
- Keep signal and power wiring organized to reduce accidental shorts and noise.

## Final Signal Map

| Arduino signal | Final function |
|---|---|
| D2 | Button |
| D3 | Stepper IN1 |
| D4 | Stepper IN2 |
| D5 | Stepper IN3 |
| D6 | Stepper IN4 |
| D7 | HC-SR04 TRIG |
| D8 | HC-SR04 ECHO / ICP1 |
| D9 | Servo signal |
| D10 | DC motor L293D input |
| D11 | Relay transistor drive |
| D12 | DC motor L293D input |
| D13 | Built-in LED |
| A0 | Thermistor |
| USB serial | Python supervisor |

No additional connector, supply pin, or unconfirmed driver pinout is implied by
this signal map.

## Pre-Power Inspection Record

Inspection date: **2026-08-27**  
Validation-session user sign-off: **CONFIRMED**  
Result: **10 / 10 PASS**

| # | Inspection item | Result |
|---:|---|---|
| 1 | Aucun 230 V / secteur connecté au relais | PASS |
| 2 | Arduino/logique sur alimentation nominale 5 V | PASS |
| 3 | Actionneurs sur alimentation externe nominale 5 V | PASS |
| 4 | GND Arduino et GND actionneurs communs | PASS |
| 5 | Servo alimenté par rail externe, D9 signal uniquement | PASS |
| 6 | Stepper alimenté via ULN2003, D3-D6 commandes uniquement | PASS |
| 7 | Moteur DC alimenté via L293D, D10/D12 commandes | PASS |
| 8 | Relais piloté via PN2222 + résistance + diode flyback | PASS |
| 9 | Aucun actionneur de puissance alimenté directement par GPIO | PASS |
| 10 | Polarités vérifiées avant mise sous tension | PASS |

The explicit user confirmation is recorded as the validation-session sign-off;
no handwritten signature is claimed. The standalone checklist is
[`../validation/pre_power_checklist.md`](../validation/pre_power_checklist.md).

## Photo Evidence

The following four files are present in `docs/hardware/photos/` and were
reviewed:

- [`final_system_overview.png`](photos/final_system_overview.png): overall
  integrated low-voltage prototype, including the Arduino, breadboard, sensors,
  driver boards, and actuators visible in the assembled setup.
- [`final_breadboard_wiring.png`](photos/final_breadboard_wiring.png): close view
  of the breadboard wiring, HC-SR04, and nearby driver area.
- [`final_actuators.png`](photos/final_actuators.png): servo, DC motor/fan, relay,
  and stepper hardware visible with the integrated setup.
- [`final_power_supply.png`](photos/final_power_supply.png): commercial adapter
  marking showing a nominal output of 5.0 V DC / 2.4 A. This is a nominal label,
  not a multimeter measurement.

The photos do not by themselves verify every hidden conductor, breadboard node,
polarity, or voltage. Those points rely on the user inspection, measurements,
and physical tests recorded separately.

## Physical Validation Evidence

The user supplied the following real physical validation results:

- Complete actuator smoke test: PASS.
- Stepper physical test: PASS.
- Servo physical test: PASS.
- DC motor physical test: PASS.
- Relay physical test: PASS.
- Complete integrated operation: PASS.
- SAFE_STATE physical behavior: PASS.
- Watchdog safe/recovery physical test: PASS.
- External nominal 5 V actuator architecture and common ground used for the
  final setup: CONFIRMED.
- No mains connection and low-voltage relay use only: CONFIRMED.

These statements preserve the supplied physical record. They do not add an
unperformed voltage, current, EMC, thermal, or endurance test.

## Known Limitations

- Experimental prototype only.
- Not SIL certified.
- Not ASIL certified.
- No EMC/EMI certification.
- No detailed current-consumption characterization.
- No guaranteed brownout or electrical-noise margin.
- No mains switching is permitted or validated.
- Photograph review cannot verify hidden electrical nodes or all conductor
  continuity/polarity.
- The adapter's 2.4 A marking is nominal; prototype current was not measured.
- No production-equipment electrical-safety certification is claimed.

## VAL-REQ-028 Traceability

**Requirement:** The prototype shall remain low-voltage only: no 230 V
connection, controlled logic/actuator supplies, common grounds where required,
and no power actuator driven directly from an MCU GPIO.

**Priority:** MUST

**Acceptance criterion:** Pre-power inspection confirms no mains connection;
supply voltages/polarities and common ground are recorded; relay, stepper, DC
motor, and servo use their required transistor/driver/external-power paths.

**Evidence expected:** Wiring diagram/photos, signed pre-power checklist,
measured supply voltages, smoke-test record.

**Design / implementation evidence:** The low-voltage architecture, separate
logic and actuator supplies, common ground, external servo power, ULN2003,
L293D, PN2222/base-resistor/flyback stage, and GPIO signal-only policy are
documented above.

**Measured evidence:** Arduino logic rail approximately 4.8 V; external actuator
rail approximately 4.9 V. The measurements are distinct from the nominal 5 V
ratings.

**Physical evidence:** The user-confirmed 10/10 pre-power inspection, all four
final photographs, complete actuator smoke test, integrated operation,
SAFE_STATE behavior, and watchdog safe/recovery test are recorded above.

**Document evidence:**

- `docs/hardware/electrical_safety_evidence.md`
- `docs/validation/pre_power_checklist.md`
- `docs/hardware/photos/final_system_overview.png`
- `docs/hardware/photos/final_breadboard_wiring.png`
- `docs/hardware/photos/final_actuators.png`
- `docs/hardware/photos/final_power_supply.png`

**Status:** SATISFIED

The current requirement, acceptance criterion, and expected evidence are
covered by the recorded low-voltage design, measured rails, polarity/common-
ground inspection, driver/power paths, user validation-session sign-off,
photographs, and physical smoke-test record. This evidence closes VAL-REQ-028;
it does not certify the prototype or authorize mains switching.
