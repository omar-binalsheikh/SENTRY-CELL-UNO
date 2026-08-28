# SENTRY-CELL UNO — Pre-Power Checklist

Inspection date: **2026-08-27**  
Validation-session user sign-off: **CONFIRMED**  
Final result: **10 / 10 PASS**

This record preserves the explicit validation-session confirmation supplied by
the user. It does not claim a handwritten signature or third-party electrical
certification.

| # | Inspection item | PASS / FAIL |
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

## Recorded supply evidence

| Rail or source | Nominal | Measured |
|---|---:|---:|
| Arduino logic rail | 5 V | approximately 4.8 V |
| External actuator rail | 5 V | approximately 4.9 V |
| Commercial adapter marking | 5.0 V DC / 2.4 A | Label only; not a measurement |

## Scope note

The commercial adapter may itself connect to mains, but only its low-voltage DC
output powers this prototype. No 230 V connection or mains switching is present
at the prototype or relay. The photographs are complementary evidence and
cannot prove hidden electrical nodes.
