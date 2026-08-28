from dataclasses import dataclass


SOF = 0xA5
VERSION = 0x01
MAX_PAYLOAD = 8

TYPE_PING = 0x01
TYPE_ECHO = 0x02
TYPE_GET_COMM_STATUS = 0x03
TYPE_GET_TIMING_STATUS = 0x04
TYPE_GET_JITTER_STATUS = 0x05
TYPE_GET_RUNTIME_MEMORY_STATUS = 0x06
TYPE_GET_CPU_LOAD_STATUS = 0x07
TYPE_GET_OVERRUN_STATUS = 0x08
TYPE_GET_RESET_CAUSE = 0x09
TYPE_INJECT_WATCHDOG_BLOCK = 0x0A
TYPE_GET_WATCHDOG_STATUS = 0x0B
TYPE_PONG = 0x81
TYPE_COMM_STATUS = 0x83
TYPE_TIMING_STATUS = 0x84
TYPE_JITTER_STATUS = 0x85
TYPE_RUNTIME_MEMORY_STATUS = 0x86
TYPE_CPU_LOAD_STATUS = 0x87
TYPE_OVERRUN_STATUS = 0x88
TYPE_RESET_CAUSE = 0x89
TYPE_WATCHDOG_STATUS = 0x8B
TYPE_ACK = 0x90
TYPE_NACK = 0x91

NACK_UNSUPPORTED_TYPE = 0x01
NACK_INVALID_LENGTH = 0x02
MCUSR_WDRF_MASK = 1 << 3


class ProtocolError(Exception):
    """Base exception for malformed or unsupported protocol frames."""


class CRCError(ProtocolError):
    """Raised when a frame CRC does not match its contents."""


@dataclass(frozen=True)
class Frame:
    frame_type: int
    sequence: int
    payload: bytes


@dataclass(frozen=True)
class CommStatus:
    uart_rx_overflow: int
    parser_timeouts: int
    crc_errors: int


@dataclass(frozen=True)
class TimingStatus:
    actuator_ticks: int
    control_ticks: int
    sensor_safety_ticks: int
    communication_ticks: int


@dataclass(frozen=True)
class JitterStatus:
    actuator_ms: int
    control_ms: int
    sensor_safety_ms: int
    communication_ms: int


@dataclass(frozen=True)
class RuntimeMemoryStatus:
    min_free_bytes: int
    painted_bytes: int
    used_painted_bytes: int


@dataclass(frozen=True)
class CpuLoadStatus:
    busy_ticks: int
    elapsed_ms: int


@dataclass(frozen=True)
class OverrunStatus:
    actuator: int
    control: int
    sensor_safety: int
    communication: int


@dataclass(frozen=True)
class ResetCauseStatus:
    reset_cause: int


@dataclass(frozen=True)
class WatchdogStatus:
    """Persistent watchdog ISR marker captured at boot, not MCUSR."""

    timeout_marker: int


def crc8_atm(data: bytes) -> int:
    crc = 0x00

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc


def _validate_octet(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"{name} must be an integer")
    if not 0 <= value <= 0xFF:
        raise ProtocolError(f"{name} must be in range 0..255")


def encode_frame(frame: Frame) -> bytes:
    _validate_octet("frame_type", frame.frame_type)
    _validate_octet("sequence", frame.sequence)

    if not isinstance(frame.payload, bytes):
        raise ProtocolError("payload must be bytes")
    if len(frame.payload) > MAX_PAYLOAD:
        raise ProtocolError(
            f"payload length {len(frame.payload)} exceeds {MAX_PAYLOAD} bytes"
        )

    body = bytes(
        (VERSION, frame.frame_type, frame.sequence, len(frame.payload))
    ) + frame.payload
    return bytes((SOF,)) + body + bytes((crc8_atm(body),))


def decode_frame(data: bytes) -> Frame:
    if not isinstance(data, bytes):
        raise ProtocolError("encoded frame must be bytes")
    if len(data) < 6:
        raise ProtocolError("frame is shorter than the 6-byte minimum")
    if data[0] != SOF:
        raise ProtocolError(f"invalid SOF 0x{data[0]:02X}")
    if data[1] != VERSION:
        raise ProtocolError(f"unsupported protocol version 0x{data[1]:02X}")

    payload_length = data[4]
    if payload_length > MAX_PAYLOAD:
        raise ProtocolError(
            f"payload length {payload_length} exceeds {MAX_PAYLOAD} bytes"
        )

    expected_size = 6 + payload_length
    if len(data) != expected_size:
        raise ProtocolError(
            f"frame size {len(data)} does not match LENGTH {payload_length} "
            f"(expected {expected_size})"
        )

    expected_crc = crc8_atm(data[1:-1])
    if data[-1] != expected_crc:
        raise CRCError(
            f"CRC mismatch: received 0x{data[-1]:02X}, "
            f"expected 0x{expected_crc:02X}"
        )

    return Frame(
        frame_type=data[2],
        sequence=data[3],
        payload=data[5 : 5 + payload_length],
    )


def decode_comm_status(frame: Frame) -> CommStatus:
    if frame.frame_type != TYPE_COMM_STATUS:
        raise ProtocolError(
            f"expected COMM_STATUS type 0x{TYPE_COMM_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 3:
        raise ProtocolError(
            f"COMM_STATUS payload must contain exactly 3 bytes, "
            f"received {len(frame.payload)}"
        )

    return CommStatus(
        uart_rx_overflow=frame.payload[0],
        parser_timeouts=frame.payload[1],
        crc_errors=frame.payload[2],
    )


def decode_timing_status(frame: Frame) -> TimingStatus:
    if frame.frame_type != TYPE_TIMING_STATUS:
        raise ProtocolError(
            f"expected TIMING_STATUS type 0x{TYPE_TIMING_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 8:
        raise ProtocolError(
            f"TIMING_STATUS payload must contain exactly 8 bytes, "
            f"received {len(frame.payload)}"
        )

    return TimingStatus(
        actuator_ticks=int.from_bytes(frame.payload[0:2], "little"),
        control_ticks=int.from_bytes(frame.payload[2:4], "little"),
        sensor_safety_ticks=int.from_bytes(frame.payload[4:6], "little"),
        communication_ticks=int.from_bytes(frame.payload[6:8], "little"),
    )


def ticks_to_microseconds(ticks: int) -> float:
    return ticks * 0.5


def decode_jitter_status(frame: Frame) -> JitterStatus:
    if frame.frame_type != TYPE_JITTER_STATUS:
        raise ProtocolError(
            f"expected JITTER_STATUS type 0x{TYPE_JITTER_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 8:
        raise ProtocolError(
            f"JITTER_STATUS payload must contain exactly 8 bytes, "
            f"received {len(frame.payload)}"
        )

    return JitterStatus(
        actuator_ms=int.from_bytes(frame.payload[0:2], "little"),
        control_ms=int.from_bytes(frame.payload[2:4], "little"),
        sensor_safety_ms=int.from_bytes(frame.payload[4:6], "little"),
        communication_ms=int.from_bytes(frame.payload[6:8], "little"),
    )


def decode_runtime_memory_status(frame: Frame) -> RuntimeMemoryStatus:
    if frame.frame_type != TYPE_RUNTIME_MEMORY_STATUS:
        raise ProtocolError(
            f"expected RUNTIME_MEMORY_STATUS type "
            f"0x{TYPE_RUNTIME_MEMORY_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 6:
        raise ProtocolError(
            f"RUNTIME_MEMORY_STATUS payload must contain exactly 6 bytes, "
            f"received {len(frame.payload)}"
        )

    return RuntimeMemoryStatus(
        min_free_bytes=int.from_bytes(frame.payload[0:2], "little"),
        painted_bytes=int.from_bytes(frame.payload[2:4], "little"),
        used_painted_bytes=int.from_bytes(frame.payload[4:6], "little"),
    )


def decode_cpu_load_status(frame: Frame) -> CpuLoadStatus:
    if frame.frame_type != TYPE_CPU_LOAD_STATUS:
        raise ProtocolError(
            f"expected CPU_LOAD_STATUS type 0x{TYPE_CPU_LOAD_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 8:
        raise ProtocolError(
            f"CPU_LOAD_STATUS payload must contain exactly 8 bytes, "
            f"received {len(frame.payload)}"
        )

    return CpuLoadStatus(
        busy_ticks=int.from_bytes(frame.payload[0:4], "little"),
        elapsed_ms=int.from_bytes(frame.payload[4:8], "little"),
    )


def calculate_scheduled_task_utilization(
    busy_ticks: int,
    elapsed_ms: int,
) -> float:
    if elapsed_ms == 0:
        return 0.0

    available_ticks = elapsed_ms * 2000
    return 100.0 * busy_ticks / available_ticks


def decode_overrun_status(frame: Frame) -> OverrunStatus:
    if frame.frame_type != TYPE_OVERRUN_STATUS:
        raise ProtocolError(
            f"expected OVERRUN_STATUS type 0x{TYPE_OVERRUN_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 8:
        raise ProtocolError(
            f"OVERRUN_STATUS payload must contain exactly 8 bytes, "
            f"received {len(frame.payload)}"
        )

    return OverrunStatus(
        actuator=int.from_bytes(frame.payload[0:2], "little"),
        control=int.from_bytes(frame.payload[2:4], "little"),
        sensor_safety=int.from_bytes(frame.payload[4:6], "little"),
        communication=int.from_bytes(frame.payload[6:8], "little"),
    )


def decode_reset_cause(frame: Frame) -> ResetCauseStatus:
    if frame.frame_type != TYPE_RESET_CAUSE:
        raise ProtocolError(
            f"expected RESET_CAUSE type 0x{TYPE_RESET_CAUSE:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 1:
        raise ProtocolError(
            f"RESET_CAUSE payload must contain exactly 1 byte, "
            f"received {len(frame.payload)}"
        )

    return ResetCauseStatus(reset_cause=frame.payload[0])


def reset_cause_has_wdrf(reset_cause: int) -> bool:
    return (reset_cause & MCUSR_WDRF_MASK) != 0


def decode_watchdog_status(frame: Frame) -> WatchdogStatus:
    if frame.frame_type != TYPE_WATCHDOG_STATUS:
        raise ProtocolError(
            f"expected WATCHDOG_STATUS type 0x{TYPE_WATCHDOG_STATUS:02X}, "
            f"received 0x{frame.frame_type:02X}"
        )
    if len(frame.payload) != 1:
        raise ProtocolError(
            f"WATCHDOG_STATUS payload must contain exactly 1 byte, "
            f"received {len(frame.payload)}"
        )
    if frame.payload[0] not in (0, 1):
        raise ProtocolError(
            f"WATCHDOG_STATUS marker must be 0 or 1, "
            f"received {frame.payload[0]}"
        )

    return WatchdogStatus(timeout_marker=frame.payload[0])


def watchdog_test_passed(
    mcu_recovered: bool,
    ping_after_reset: bool,
    timeout_marker: int,
) -> bool:
    return mcu_recovered and ping_after_reset and timeout_marker == 1
