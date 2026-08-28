import argparse
import sys
import time
from datetime import datetime
from typing import Sequence

if __package__:
    from .dashboard import (
        DEFAULT_DASHBOARD_HOST,
        DEFAULT_DASHBOARD_PORT,
        run_dashboard,
    )
    from .fault_injection import (
        FaultInjectionCsvLogger,
        FaultInjectionResult,
        build_fault_result,
        require_counter_increment_capacity,
    )
    from .monitoring import (
        CommHealthSample,
        CsvLogger,
        next_sequence,
        validate_monitor_options,
    )
    from .protocol import (
        MAX_PAYLOAD,
        TYPE_ACK,
        TYPE_ECHO,
        TYPE_GET_COMM_STATUS,
        TYPE_GET_CPU_LOAD_STATUS,
        TYPE_GET_JITTER_STATUS,
        TYPE_GET_OVERRUN_STATUS,
        TYPE_GET_RESET_CAUSE,
        TYPE_GET_WATCHDOG_STATUS,
        TYPE_GET_RUNTIME_MEMORY_STATUS,
        TYPE_GET_TIMING_STATUS,
        TYPE_INJECT_WATCHDOG_BLOCK,
        TYPE_PING,
        TYPE_PONG,
        Frame,
        ProtocolError,
        calculate_scheduled_task_utilization,
        decode_comm_status,
        decode_cpu_load_status,
        decode_frame,
        decode_jitter_status,
        decode_overrun_status,
        decode_reset_cause,
        decode_watchdog_status,
        decode_runtime_memory_status,
        decode_timing_status,
        encode_frame,
        ticks_to_microseconds,
        watchdog_test_passed,
    )
    from .serial_link import SerialLink, SerialLinkError, SerialTimeoutError
    from .validation_campaign import (
        collect_build_evidence,
        format_validation_report,
        measurement_report_path,
        write_measurement_report,
    )
else:
    from dashboard import (
        DEFAULT_DASHBOARD_HOST,
        DEFAULT_DASHBOARD_PORT,
        run_dashboard,
    )
    from fault_injection import (
        FaultInjectionCsvLogger,
        FaultInjectionResult,
        build_fault_result,
        require_counter_increment_capacity,
    )
    from monitoring import (
        CommHealthSample,
        CsvLogger,
        next_sequence,
        validate_monitor_options,
    )
    from protocol import (
        MAX_PAYLOAD,
        TYPE_ACK,
        TYPE_ECHO,
        TYPE_GET_COMM_STATUS,
        TYPE_GET_CPU_LOAD_STATUS,
        TYPE_GET_JITTER_STATUS,
        TYPE_GET_OVERRUN_STATUS,
        TYPE_GET_RESET_CAUSE,
        TYPE_GET_WATCHDOG_STATUS,
        TYPE_GET_RUNTIME_MEMORY_STATUS,
        TYPE_GET_TIMING_STATUS,
        TYPE_INJECT_WATCHDOG_BLOCK,
        TYPE_PING,
        TYPE_PONG,
        Frame,
        ProtocolError,
        calculate_scheduled_task_utilization,
        decode_comm_status,
        decode_cpu_load_status,
        decode_frame,
        decode_jitter_status,
        decode_overrun_status,
        decode_reset_cause,
        decode_watchdog_status,
        decode_runtime_memory_status,
        decode_timing_status,
        encode_frame,
        ticks_to_microseconds,
        watchdog_test_passed,
    )
    from serial_link import SerialLink, SerialLinkError, SerialTimeoutError
    from validation_campaign import (
        collect_build_evidence,
        format_validation_report,
        measurement_report_path,
        write_measurement_report,
    )


class SupervisorError(Exception):
    """Raised when an otherwise valid response is not the expected one."""


def validate_observe_seconds(observe_seconds: float) -> None:
    if not (observe_seconds > 0.0):
        raise ValueError("observe-seconds must be greater than zero")


def read_protocol_frame(link: SerialLink, timeout_s: float = 1.0) -> Frame:
    header = link.read_exact(5, timeout_s)
    payload_length = header[4]
    if payload_length > MAX_PAYLOAD:
        raise ProtocolError(
            f"response LENGTH {payload_length} exceeds {MAX_PAYLOAD} bytes"
        )

    payload_and_crc = link.read_exact(payload_length + 1, timeout_s)
    return decode_frame(header + payload_and_crc)


def require_response(
    response: Frame,
    expected_type: int,
    expected_sequence: int,
    expected_payload: bytes,
) -> None:
    if response.frame_type != expected_type:
        raise SupervisorError(
            f"unexpected response type 0x{response.frame_type:02X}; "
            f"expected 0x{expected_type:02X}"
        )
    if response.sequence != expected_sequence:
        raise SupervisorError(
            f"unexpected response sequence 0x{response.sequence:02X}; "
            f"expected 0x{expected_sequence:02X}"
        )
    if response.payload != expected_payload:
        raise SupervisorError(
            f"unexpected response payload {response.payload.hex(' ').upper()}"
        )


def run_supervisor(
    port: str,
    status_requested: bool,
    timing_requested: bool,
    jitter_requested: bool,
) -> None:
    print("SENTRY-CELL UNO Supervisor")
    print(f"Port: {port}")
    print()

    with SerialLink(port) as link:
        time.sleep(2.2)

        ping_sequence = 0x10
        link.write(encode_frame(Frame(TYPE_PING, ping_sequence, b"")))
        ping_response = read_protocol_frame(link)
        require_response(ping_response, TYPE_PONG, ping_sequence, b"")
        print("PING seq=0x10 -> PONG [PASS]")

        echo_sequence = 0x20
        echo_payload = bytes((0x11, 0x22, 0x33, 0x44))
        link.write(encode_frame(Frame(TYPE_ECHO, echo_sequence, echo_payload)))
        echo_response = read_protocol_frame(link)
        require_response(echo_response, TYPE_ACK, echo_sequence, echo_payload)
        print("ECHO seq=0x20 payload=11 22 33 44 -> ACK [PASS]")

        if status_requested:
            status_sequence = 0x30
            status_request = Frame(TYPE_GET_COMM_STATUS, status_sequence, b"")
            link.write(encode_frame(status_request))
            status_response = read_protocol_frame(link)
            if status_response.sequence != status_sequence:
                raise SupervisorError(
                    f"unexpected COMM_STATUS sequence "
                    f"0x{status_response.sequence:02X}; "
                    f"expected 0x{status_sequence:02X}"
                )
            status = decode_comm_status(status_response)

            print()
            print("Communication health")
            print(f"UART RX overflow : {status.uart_rx_overflow}")
            print(f"Parser timeouts  : {status.parser_timeouts}")
            print(f"CRC errors       : {status.crc_errors}")

        if timing_requested:
            timing_sequence = 0x40
            timing_request = Frame(
                TYPE_GET_TIMING_STATUS, timing_sequence, b""
            )
            link.write(encode_frame(timing_request))
            timing_response = read_protocol_frame(link)
            if timing_response.sequence != timing_sequence:
                raise SupervisorError(
                    f"unexpected TIMING_STATUS sequence "
                    f"0x{timing_response.sequence:02X}; "
                    f"expected 0x{timing_sequence:02X}"
                )
            timing = decode_timing_status(timing_response)

            print()
            print("Task execution-time maxima")
            print(
                f"Actuator        : {timing.actuator_ticks} ticks = "
                f"{ticks_to_microseconds(timing.actuator_ticks):g} us"
            )
            print(
                f"Control         : {timing.control_ticks} ticks = "
                f"{ticks_to_microseconds(timing.control_ticks):g} us"
            )
            print(
                f"Sensor/Safety   : {timing.sensor_safety_ticks} ticks = "
                f"{ticks_to_microseconds(timing.sensor_safety_ticks):g} us"
            )
            print(
                f"Communication   : {timing.communication_ticks} ticks = "
                f"{ticks_to_microseconds(timing.communication_ticks):g} us"
            )

        if jitter_requested:
            jitter_sequence = 0x50
            jitter_request = Frame(
                TYPE_GET_JITTER_STATUS, jitter_sequence, b""
            )
            link.write(encode_frame(jitter_request))
            jitter_response = read_protocol_frame(link)
            if jitter_response.sequence != jitter_sequence:
                raise SupervisorError(
                    f"unexpected JITTER_STATUS sequence "
                    f"0x{jitter_response.sequence:02X}; "
                    f"expected 0x{jitter_sequence:02X}"
                )
            jitter = decode_jitter_status(jitter_response)

            print()
            print("Scheduler jitter maxima")
            print("Resolution: 1 ms")
            print()
            print(f"Actuator        : {jitter.actuator_ms} ms")
            print(f"Control         : {jitter.control_ms} ms")
            print(f"Sensor/Safety   : {jitter.sensor_safety_ms} ms")
            print(f"Communication   : {jitter.communication_ms} ms")

    print()
    print("Protocol checks: PASS")
    print("Serial link: PASS")
    print("Supervisor bring-up: PASS")


def run_runtime_memory(port: str, observe_seconds: float) -> None:
    validate_observe_seconds(observe_seconds)

    print("SENTRY-CELL UNO Runtime SRAM Watermark")
    print(f"Port: {port}")
    print(f"Observation window: {observe_seconds:g} s")
    print()

    with SerialLink(port) as link:
        time.sleep(2.2)

        print("RUN PHYSICAL SCENARIO NOW", flush=True)
        time.sleep(observe_seconds)

        sequence = 0x60
        request = Frame(TYPE_GET_RUNTIME_MEMORY_STATUS, sequence, b"")
        link.write(encode_frame(request))
        response = read_protocol_frame(link)

        if response.sequence != sequence:
            raise SupervisorError(
                f"unexpected RUNTIME_MEMORY_STATUS sequence "
                f"0x{response.sequence:02X}; expected 0x{sequence:02X}"
            )

        status = decode_runtime_memory_status(response)

    print()
    print("Runtime SRAM watermark")
    print()
    print(f"Painted region        : {status.painted_bytes} bytes")
    print(f"Used painted region   : {status.used_painted_bytes} bytes")
    print(f"Minimum free observed : {status.min_free_bytes} bytes")
    print()
    print("Observed watermark, not guaranteed worst-case stack bound.")


def run_rt_profile(port: str, observe_seconds: float) -> None:
    validate_observe_seconds(observe_seconds)

    print("SENTRY-CELL UNO Scheduled-Task Runtime Profile")
    print(f"Port: {port}")
    print(f"Observation window: {observe_seconds:g} s")
    print()

    with SerialLink(port) as link:
        time.sleep(2.2)

        print("RUN PHYSICAL SCENARIO NOW", flush=True)
        time.sleep(observe_seconds)

        cpu_sequence = 0x70
        cpu_request = Frame(TYPE_GET_CPU_LOAD_STATUS, cpu_sequence, b"")
        link.write(encode_frame(cpu_request))
        cpu_response = read_protocol_frame(link)

        if cpu_response.sequence != cpu_sequence:
            raise SupervisorError(
                f"unexpected CPU_LOAD_STATUS sequence "
                f"0x{cpu_response.sequence:02X}; expected 0x{cpu_sequence:02X}"
            )

        cpu_status = decode_cpu_load_status(cpu_response)

        overrun_sequence = 0x71
        overrun_request = Frame(
            TYPE_GET_OVERRUN_STATUS, overrun_sequence, b""
        )
        link.write(encode_frame(overrun_request))
        overrun_response = read_protocol_frame(link)

        if overrun_response.sequence != overrun_sequence:
            raise SupervisorError(
                f"unexpected OVERRUN_STATUS sequence "
                f"0x{overrun_response.sequence:02X}; "
                f"expected 0x{overrun_sequence:02X}"
            )

        overruns = decode_overrun_status(overrun_response)

    utilization = calculate_scheduled_task_utilization(
        cpu_status.busy_ticks,
        cpu_status.elapsed_ms,
    )

    print()
    print("Real-Time Runtime Profile")
    print()
    print(f"Observation time                : {cpu_status.elapsed_ms} ms")
    print(f"Scheduled-task busy time        : {cpu_status.busy_ticks} ticks")
    print(f"Scheduled-task CPU utilization  : {utilization:.1f} %")
    print()
    print("Execution overruns")
    print(f"Actuator       : {overruns.actuator}")
    print(f"Control        : {overruns.control}")
    print(f"Sensor/Safety  : {overruns.sensor_safety}")
    print(f"Communication  : {overruns.communication}")
    print()
    print("ISR and scheduler overhead are not included in this utilization.")


def _request_validation_status(
    link: SerialLink,
    request_type: int,
    sequence: int,
    status_name: str,
    decoder,
):
    request = Frame(request_type, sequence, b"")
    link.write(encode_frame(request))
    response = read_protocol_frame(link)

    if response.sequence != sequence:
        raise SupervisorError(
            f"unexpected {status_name} sequence "
            f"0x{response.sequence:02X}; expected 0x{sequence:02X}"
        )

    return decoder(response)


def _collect_validation_runtime(link: SerialLink):
    timing = _request_validation_status(
        link,
        TYPE_GET_TIMING_STATUS,
        0x80,
        "TIMING_STATUS",
        decode_timing_status,
    )
    jitter = _request_validation_status(
        link,
        TYPE_GET_JITTER_STATUS,
        0x81,
        "JITTER_STATUS",
        decode_jitter_status,
    )
    runtime_memory = _request_validation_status(
        link,
        TYPE_GET_RUNTIME_MEMORY_STATUS,
        0x82,
        "RUNTIME_MEMORY_STATUS",
        decode_runtime_memory_status,
    )
    cpu_load = _request_validation_status(
        link,
        TYPE_GET_CPU_LOAD_STATUS,
        0x83,
        "CPU_LOAD_STATUS",
        decode_cpu_load_status,
    )
    overruns = _request_validation_status(
        link,
        TYPE_GET_OVERRUN_STATUS,
        0x84,
        "OVERRUN_STATUS",
        decode_overrun_status,
    )

    return timing, jitter, runtime_memory, cpu_load, overruns


def run_validation_profile(port: str) -> None:
    build_evidence = collect_build_evidence()

    print("Final validation measurement campaign")
    print(f"Port: {port}")
    print()
    print("Scenario:")
    print("IDLE       : 5 s")
    print("ACTIVE     : 10 s")
    print("SAFE_STATE : 5 s")
    print("Host-timed instructions only; FSM states are not automatically detected.")
    print()

    with SerialLink(port) as link:
        time.sleep(2.2)

        print("Keep system in IDLE", flush=True)
        time.sleep(5.0)

        print("Press D2 once now to enter ACTIVE", flush=True)
        time.sleep(10.0)

        print("Introduce obstacle now to enter SAFE_STATE", flush=True)
        time.sleep(5.0)

        timing, jitter, runtime_memory, cpu_load, overruns = (
            _collect_validation_runtime(link)
        )

    campaign_timestamp = datetime.now().astimezone()
    report = format_validation_report(
        campaign_timestamp,
        build_evidence,
        timing,
        jitter,
        runtime_memory,
        cpu_load,
        overruns,
    )
    report_path = measurement_report_path(campaign_timestamp)
    write_measurement_report(report_path, report)

    print()
    print(report, end="")
    print(f"Measurement report written: {report_path}")


def run_monitor(
    port: str,
    samples: int,
    interval_s: float,
    csv_path: str,
) -> None:
    validate_monitor_options(samples, interval_s)

    print("SENTRY-CELL UNO Communication Monitor")
    print(f"Port: {port}")
    print(f"Samples: {samples}")
    print(f"Interval: {interval_s} s")
    print(f"CSV: {csv_path}")
    print()

    sequence = 0x40

    with SerialLink(port) as link:
        time.sleep(2.2)

        with CsvLogger(csv_path) as csv_logger:
            next_acquisition = time.monotonic()

            for sample_index in range(samples):
                if sample_index > 0:
                    next_acquisition += interval_s
                    remaining = next_acquisition - time.monotonic()
                    if remaining > 0.0:
                        time.sleep(remaining)

                request = Frame(TYPE_GET_COMM_STATUS, sequence, b"")
                link.write(encode_frame(request))
                response = read_protocol_frame(link)

                if response.sequence != sequence:
                    raise SupervisorError(
                        f"unexpected COMM_STATUS sequence "
                        f"0x{response.sequence:02X}; expected 0x{sequence:02X}"
                    )

                status = decode_comm_status(response)
                sample = CommHealthSample(
                    timestamp=datetime.now().astimezone().isoformat(),
                    sequence=sequence,
                    uart_rx_overflow=status.uart_rx_overflow,
                    parser_timeouts=status.parser_timeouts,
                    crc_errors=status.crc_errors,
                )
                csv_logger.write(sample)

                print(
                    f"[{sample_index + 1}/{samples}] "
                    f"seq=0x{sample.sequence:02X} "
                    f"overflow={sample.uart_rx_overflow} "
                    f"timeout={sample.parser_timeouts} "
                    f"crc={sample.crc_errors}"
                )

                sequence = next_sequence(sequence)

    print()
    print("Communication monitoring: PASS")
    print(f"CSV written: {csv_path}")


def _request_comm_status(link: SerialLink, sequence: int):
    request = Frame(TYPE_GET_COMM_STATUS, sequence, b"")
    link.write(encode_frame(request))
    response = read_protocol_frame(link)

    if response.sequence != sequence:
        raise SupervisorError(
            f"unexpected COMM_STATUS sequence 0x{response.sequence:02X}; "
            f"expected 0x{sequence:02X}"
        )

    return decode_comm_status(response)


def _verify_recovery_ping(link: SerialLink, sequence: int) -> bool:
    try:
        link.write(encode_frame(Frame(TYPE_PING, sequence, b"")))
        response = read_protocol_frame(link)
        require_response(response, TYPE_PONG, sequence, b"")
    except (OSError, ProtocolError, SerialLinkError, SupervisorError):
        return False

    return True


def _request_reset_cause(link: SerialLink, sequence: int):
    request = Frame(TYPE_GET_RESET_CAUSE, sequence, b"")
    link.write(encode_frame(request))
    response = read_protocol_frame(link)

    if response.sequence != sequence:
        raise SupervisorError(
            f"unexpected RESET_CAUSE sequence 0x{response.sequence:02X}; "
            f"expected 0x{sequence:02X}"
        )

    return decode_reset_cause(response)


def _request_watchdog_status(link: SerialLink, sequence: int):
    request = Frame(TYPE_GET_WATCHDOG_STATUS, sequence, b"")
    link.write(encode_frame(request))
    response = read_protocol_frame(link)

    if response.sequence != sequence:
        raise SupervisorError(
            f"unexpected WATCHDOG_STATUS sequence "
            f"0x{response.sequence:02X}; expected 0x{sequence:02X}"
        )

    return decode_watchdog_status(response)


def run_watchdog_test(port: str) -> None:
    print("Watchdog fault injection")
    print(f"Port: {port}")
    print()

    with SerialLink(port) as link:
        time.sleep(2.2)

        initial_status = _request_watchdog_status(link, 0x70)
        print(
            "Initial watchdog marker : "
            f"{initial_status.timeout_marker}"
        )
        print("Injecting controlled firmware block...", flush=True)

        injection = Frame(TYPE_INJECT_WATCHDOG_BLOCK, 0x71, b"")
        link.write(encode_frame(injection))

        time.sleep(4.0)

        recovery_ping = _verify_recovery_ping(link, 0x72)
        watchdog_marker = 0
        reset_cause = 0
        if recovery_ping:
            watchdog_status = _request_watchdog_status(link, 0x73)
            watchdog_marker = watchdog_status.timeout_marker
            reset_status = _request_reset_cause(link, 0x74)
            reset_cause = reset_status.reset_cause

    mcu_recovered = recovery_ping
    passed = watchdog_test_passed(
        mcu_recovered, recovery_ping, watchdog_marker)

    print()
    print(f"MCU recovered            : {'PASS' if mcu_recovered else 'FAIL'}")
    print(f"PING after reset         : {'PASS' if recovery_ping else 'FAIL'}")
    print(
        "Watchdog timeout marker  : "
        f"{'PASS' if watchdog_marker == 1 else 'FAIL'}"
    )
    print(f"Raw boot reset cause     : 0x{reset_cause:02X} [informational]")
    print()
    print(f"Watchdog test            : {'PASS' if passed else 'FAIL'}")

    if not passed:
        raise SupervisorError(
            "watchdog test requires recovered communication, PING, "
            "and timeout marker 1"
        )


def _require_no_bad_crc_response(link: SerialLink) -> None:
    try:
        unexpected = link.read_exact(1, 0.15)
    except SerialTimeoutError:
        return

    raise SupervisorError(
        f"corrupted-CRC frame produced an unexpected response byte "
        f"0x{unexpected[0]:02X}"
    )


def _print_fault_result(
    title: str,
    counter_label: str,
    result: FaultInjectionResult,
) -> None:
    print(title)
    print(f"{counter_label}: {result.before} -> {result.after}")
    print(
        "Recovery PING/PONG: "
        f"{'PASS' if result.recovery_ping else 'FAIL'}"
    )
    print(f"Result: {'PASS' if result.passed else 'FAIL'}")
    print()


def run_fault_injection_comm(port: str, csv_path: str) -> None:
    print("SENTRY-CELL UNO Communication Fault Injection")
    print(f"Port: {port}")
    print(f"CSV: {csv_path}")
    print()

    results = []

    with SerialLink(port) as link:
        time.sleep(2.2)

        with FaultInjectionCsvLogger(csv_path) as csv_logger:
            crc_before_status = _request_comm_status(link, 0x50)
            crc_before = crc_before_status.crc_errors
            require_counter_increment_capacity("CRC errors", crc_before)

            bad_crc_frame = bytearray(
                encode_frame(Frame(TYPE_PING, 0x51, b""))
            )
            bad_crc_frame[-1] ^= 0xFF
            link.write(bytes(bad_crc_frame))
            _require_no_bad_crc_response(link)

            crc_after_status = _request_comm_status(link, 0x52)
            crc_recovery = _verify_recovery_ping(link, 0x53)
            crc_result = build_fault_result(
                fault_id="FI-COM-001",
                counter_name="crc_errors",
                before=crc_before,
                after=crc_after_status.crc_errors,
                recovery_ping=crc_recovery,
            )
            csv_logger.write(
                datetime.now().astimezone().isoformat(),
                crc_result,
            )
            results.append(crc_result)
            _print_fault_result(
                "FI-COM-001 BAD_CRC",
                "CRC errors",
                crc_result,
            )

            timeout_before_status = _request_comm_status(link, 0x60)
            timeout_before = timeout_before_status.parser_timeouts
            require_counter_increment_capacity(
                "Parser timeouts",
                timeout_before,
            )

            link.write(bytes((0xA5, 0x01, 0x01)))
            time.sleep(0.20)

            timeout_after_status = _request_comm_status(link, 0x61)
            timeout_recovery = _verify_recovery_ping(link, 0x62)
            timeout_result = build_fault_result(
                fault_id="FI-COM-002",
                counter_name="parser_timeouts",
                before=timeout_before,
                after=timeout_after_status.parser_timeouts,
                recovery_ping=timeout_recovery,
            )
            csv_logger.write(
                datetime.now().astimezone().isoformat(),
                timeout_result,
            )
            results.append(timeout_result)
            _print_fault_result(
                "FI-COM-002 PARTIAL_FRAME_TIMEOUT",
                "Parser timeouts",
                timeout_result,
            )

    campaign_passed = len(results) == 2 and all(
        result.passed for result in results
    )
    print(
        "Communication fault campaign: "
        f"{'PASS' if campaign_passed else 'FAIL'}"
    )

    if not campaign_passed:
        raise SupervisorError("communication fault campaign failed")


def parse_args(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SENTRY-CELL UNO supervisor")
    parser.add_argument("--port", required=True, help="exact serial device path")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--status",
        action="store_true",
        help="request and display communication health counters",
    )
    mode.add_argument(
        "--timing",
        action="store_true",
        help="request and display task execution-time maxima",
    )
    mode.add_argument(
        "--jitter",
        action="store_true",
        help="request and display scheduler start-interval jitter maxima",
    )
    mode.add_argument(
        "--memory-runtime",
        action="store_true",
        help="observe and request the runtime SRAM watermark",
    )
    mode.add_argument(
        "--rt-profile",
        action="store_true",
        help="observe scheduled-task CPU utilization and task overruns",
    )
    mode.add_argument(
        "--monitor",
        action="store_true",
        help="monitor communication health for a finite number of samples",
    )
    mode.add_argument(
        "--fault-injection-comm",
        action="store_true",
        help="run the finite communication fault-injection campaign",
    )
    mode.add_argument(
        "--watchdog-test",
        action="store_true",
        help="run the controlled hardware-watchdog reset test",
    )
    mode.add_argument(
        "--validation-profile",
        action="store_true",
        help="run the single-session final validation measurement campaign",
    )
    mode.add_argument(
        "--dashboard",
        action="store_true",
        help="run the local read-only real-time dashboard",
    )
    parser.add_argument(
        "--dashboard-host",
        default=DEFAULT_DASHBOARD_HOST,
        help="dashboard bind host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=DEFAULT_DASHBOARD_PORT,
        help="dashboard HTTP port (default: 8080)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="number of monitoring samples (must be greater than zero)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="seconds between monitoring acquisitions (must be greater than zero)",
    )
    parser.add_argument(
        "--observe-seconds",
        type=float,
        default=25.0,
        help="runtime profiling observation window in seconds (must be positive)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="CSV output path for monitoring or fault injection",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if arguments is None else arguments)

    try:
        if args.dashboard:
            run_dashboard(
                args.port,
                args.dashboard_host,
                args.dashboard_port,
                read_protocol_frame,
            )
        elif args.validation_profile:
            run_validation_profile(args.port)
        elif args.rt_profile:
            run_rt_profile(args.port, args.observe_seconds)
        elif args.memory_runtime:
            run_runtime_memory(args.port, args.observe_seconds)
        elif args.fault_injection_comm:
            csv_path = args.csv or "measurements/fault_injection_comm.csv"
            run_fault_injection_comm(args.port, csv_path)
        elif args.watchdog_test:
            run_watchdog_test(args.port)
        elif args.monitor:
            csv_path = args.csv or "measurements/comm_health.csv"
            run_monitor(args.port, args.samples, args.interval, csv_path)
        else:
            run_supervisor(
                args.port,
                args.status,
                args.timing,
                args.jitter,
            )
    except (
        OSError,
        ProtocolError,
        SerialLinkError,
        SupervisorError,
        ValueError,
    ) as error:
        print(f"Supervisor error: {error}", file=sys.stderr)
        print("Supervisor bring-up: FAIL", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
