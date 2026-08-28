# SENTRY-CELL UNO — Demo Runbook

This runbook presents a reproducible demonstration of the validated
SENTRY-CELL UNO low-voltage prototype. The browser dashboard is read-only; the
MCU retains all local control and Safety decisions.

## 1. Preparation

- Connect the Arduino UNO to the host by USB.
- Discover the current serial port instead of assuming a persistent device
  name:

  ```bash
  ls /dev/cu.*
  ```

- Close VS Code Serial Monitor and any other process that may be using the
  selected port.
- Treat the system as a low-voltage experimental prototype only.
- Keep the external actuator 5 V supply **OFF** for a dashboard-only demo.
- Turn the external actuator 5 V supply **ON** only for the full physical demo,
  after verifying the wiring and common ground.

## 2. Supervisor Bring-Up

Run the terminal bring-up with the exact discovered port:

```bash
python3 supervisor/main.py --port <PORT>
```

Expected result:

```text
PING seq=0x10 -> PONG [PASS]
ECHO seq=0x20 payload=11 22 33 44 -> ACK [PASS]
Protocol checks: PASS
Serial link: PASS
Supervisor bring-up: PASS
```

Opening the serial port may reset the UNO through DTR. Allow the bring-up to
finish, then close it before starting another Supervisor mode.

## 3. Live Dashboard

Start the read-only dashboard:

```bash
python3 supervisor/main.py --port <PORT> --dashboard
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) in a local browser. Keep
the terminal process running; press `Ctrl+C` when the demonstration is over.
Loopback is the safe default. A deliberate non-loopback `--dashboard-host`
binding exposes the read-only telemetry UI to that reachable network without
built-in authentication or TLS; use it only in a trusted environment. The
dashboard has no actuator-control endpoint.

The page reports only telemetry implemented by the current binary protocol:

- connection health and stale/disconnected indication;
- scheduled-task CPU utilization;
- empirical runtime SRAM watermark;
- UART RX overflow, parser-timeout, and CRC-error counters;
- observed task execution-time maxima;
- task jitter at 1 ms measurement resolution;
- observed execution-overrun counters;
- persistent previous-watchdog-timeout marker;
- bounded CPU/SRAM history graphs and a bounded host-derived event log.

The dashboard uses one persistent `SerialLink`. A serial timeout remains visible
as a warning; host recovery waits approximately 114.6 ms, purges stale RX data
without reopening the port or toggling DTR, abandons that polling cycle, and
resumes on the next scheduled cycle.

The dashboard does **not** receive the FSM state, HC-SR04 distance, or actuator
states. Verify those system behaviors physically during the demo.

## 4. Full Physical Demo

Turn the external actuator 5 V supply **ON** only after the preparation checks.
Keep the dashboard open throughout the sequence.

1. Reset the UNO. The physical system should enter safe `IDLE`:
   - stepper: STOP;
   - DC motor: STOP;
   - relay: OFF;
   - servo: SAFE.
2. Press the D2 button once. The physical system should enter `ACTIVE`:
   - stepper: RUN;
   - DC motor: RUN;
   - relay: ON;
   - servo: ACTIVE.
3. Introduce an obstacle approximately 10–15 cm from the HC-SR04. The physical
   system should enter latched `SAFE_STATE`:
   - stepper: STOP;
   - DC motor: STOP;
   - relay: OFF;
   - servo: SAFE.
4. Remove the obstacle and press D2 again. `SAFE_STATE` should remain latched;
   no actuator should restart.
5. Reset the UNO. The system should return to safe `IDLE`.

These state and actuator checks are physical observations, not dashboard state
telemetry.

## 5. Watchdog Recovery Demo

The watchdog test is an optional destructive fault-injection demonstration. It
intentionally blocks foreground firmware progress and causes a hardware reset:

```bash
python3 supervisor/main.py --port <PORT> --watchdog-test
```

Expected sequence:

```text
controlled firmware block
-> watchdog timeout
-> hardware reset
-> MCU recovery
-> PING recovery
-> persistent watchdog marker detected
```

Do not interpret the informational raw reset-cause value `0xF7` as proof of
WDRF. The persistent watchdog marker is the validated indication.

## 6. Key Talking Points

- ATmega328P at 16 MHz with 2 KB SRAM.
- Direct AVR register programming without the Arduino framework.
- Cooperative scheduler with four fixed periodic tasks.
- Timer1 shared between HC-SR04 Input Capture and Servo Compare A.
- Timer2 1 ms system time.
- Interrupt-driven UART RX/TX with fixed-size ring buffers.
- Bounded binary framing, sequence identifiers, and CRC-8/ATM.
- Parser timeout and resynchronization.
- Local MCU Safety independent of the Python Supervisor.
- Retained diagnostics and watchdog recovery.
- Automated communication fault injection.
- Execution-time, jitter, CPU, and SRAM profiling.
- Traceable requirements and final validation evidence.

## 7. Measurement Caveats

The canonical PHASE 15 measurement record remains
[`measurements/val_req_027_campaign_2026-08-27_202840.txt`](../../measurements/val_req_027_campaign_2026-08-27_202840.txt).
Dashboard values are live empirical observations and can differ from that
campaign.

The canonical campaign is immutable. Future `--validation-profile` runs create
new exclusive timestamped campaign files and never overwrite existing evidence.
[`measurements/val_req_027_current_build.txt`](../../measurements/val_req_027_current_build.txt)
is the curated campaign index, not a runtime campaign output.

Never describe dashboard observations as:

- guaranteed WCET;
- zero physical jitter;
- total MCU CPU load;
- guaranteed minimum free SRAM;
- SIL/ASIL certification.

Scheduled-task CPU utilization excludes ISR and scheduler overhead. Jitter is
observed at 1 ms resolution, and SRAM is an empirical runtime watermark.

## 8. Safety

- Low-voltage experimental prototype only.
- Never connect the relay contacts or any part of the prototype to 230 V or
  other mains voltage.
- External actuator supply is nominal 5 V.
- Arduino and external actuator supplies require a common ground.
- Stepper, DC motor, relay, and servo power paths require their validated
  driver/transistor stages; no power actuator is driven directly by an MCU
  GPIO.
