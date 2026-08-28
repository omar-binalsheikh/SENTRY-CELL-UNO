import os
import unittest

from supervisor.protocol import (
    MAX_PAYLOAD,
    SOF,
    TYPE_COMM_STATUS,
    TYPE_CPU_LOAD_STATUS,
    TYPE_ECHO,
    TYPE_GET_COMM_STATUS,
    TYPE_JITTER_STATUS,
    TYPE_OVERRUN_STATUS,
    TYPE_RUNTIME_MEMORY_STATUS,
    TYPE_RESET_CAUSE,
    TYPE_WATCHDOG_STATUS,
    TYPE_TIMING_STATUS,
    TYPE_PING,
    VERSION,
    CRCError,
    CommStatus,
    CpuLoadStatus,
    Frame,
    JitterStatus,
    OverrunStatus,
    ProtocolError,
    RuntimeMemoryStatus,
    ResetCauseStatus,
    WatchdogStatus,
    TimingStatus,
    calculate_scheduled_task_utilization,
    crc8_atm,
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
    reset_cause_has_wdrf,
    ticks_to_microseconds,
    watchdog_test_passed,
)
from supervisor.main import validate_observe_seconds
from supervisor.serial_link import SerialLink, SerialTimeoutError


class ProtocolCodecTests(unittest.TestCase):
    def test_standard_crc_vector(self) -> None:
        self.assertEqual(crc8_atm(b"123456789"), 0xF4)

    def test_ping_round_trip(self) -> None:
        frame = Frame(TYPE_PING, 0x2A, b"")
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 6)
        self.assertEqual(decode_frame(encoded), frame)

    def test_echo_round_trip(self) -> None:
        payload = bytes((0x11, 0x22, 0x33, 0x44))
        frame = Frame(TYPE_ECHO, 0x20, payload)

        self.assertEqual(decode_frame(encode_frame(frame)), frame)

    def test_maximum_payload_round_trip(self) -> None:
        payload = bytes(range(MAX_PAYLOAD))
        frame = Frame(TYPE_ECHO, 0x21, payload)

        self.assertEqual(decode_frame(encode_frame(frame)), frame)

    def test_get_comm_status_encoding(self) -> None:
        frame = Frame(TYPE_GET_COMM_STATUS, 0x30, b"")
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 6)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_comm_status(self) -> None:
        frame = Frame(TYPE_COMM_STATUS, 0x30, bytes((3, 4, 5)))

        self.assertEqual(
            decode_comm_status(frame),
            CommStatus(uart_rx_overflow=3, parser_timeouts=4, crc_errors=5),
        )

    def test_decode_comm_status_rejects_wrong_payload_length(self) -> None:
        for payload in (b"", bytes((1, 2)), bytes((1, 2, 3, 4))):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_comm_status(Frame(TYPE_COMM_STATUS, 0x30, payload))

    def test_timing_status_exact_payload_length(self) -> None:
        payload = bytes((0x01, 0x00, 0x02, 0x00, 0x03, 0x00, 0x04, 0x00))
        frame = Frame(TYPE_TIMING_STATUS, 0x40, payload)
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 14)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_timing_status_little_endian(self) -> None:
        frame = Frame(
            TYPE_TIMING_STATUS,
            0x40,
            bytes((0x34, 0x12, 0xCD, 0xAB, 0x00, 0x01, 0xFF, 0x00)),
        )

        self.assertEqual(
            decode_timing_status(frame),
            TimingStatus(
                actuator_ticks=0x1234,
                control_ticks=0xABCD,
                sensor_safety_ticks=0x0100,
                communication_ticks=0x00FF,
            ),
        )

    def test_decode_timing_status_rejects_wrong_payload_length(self) -> None:
        for payload in (b"", bytes(7), bytes(9)):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_timing_status(
                        Frame(TYPE_TIMING_STATUS, 0x40, payload)
                    )

    def test_timing_ticks_to_microseconds(self) -> None:
        self.assertEqual(ticks_to_microseconds(0), 0.0)
        self.assertEqual(ticks_to_microseconds(1), 0.5)
        self.assertEqual(ticks_to_microseconds(2000), 1000.0)

    def test_jitter_status_exact_payload_length(self) -> None:
        payload = bytes((0x01, 0x00, 0x02, 0x00, 0x03, 0x00, 0x04, 0x00))
        frame = Frame(TYPE_JITTER_STATUS, 0x50, payload)
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 14)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_jitter_status_little_endian(self) -> None:
        frame = Frame(
            TYPE_JITTER_STATUS,
            0x50,
            bytes((0x34, 0x12, 0xCD, 0xAB, 0x00, 0x01, 0xFF, 0x00)),
        )

        self.assertEqual(
            decode_jitter_status(frame),
            JitterStatus(
                actuator_ms=0x1234,
                control_ms=0xABCD,
                sensor_safety_ms=0x0100,
                communication_ms=0x00FF,
            ),
        )

    def test_decode_jitter_status_rejects_wrong_payload_length(self) -> None:
        for payload in (b"", bytes(7), bytes(9)):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_jitter_status(
                        Frame(TYPE_JITTER_STATUS, 0x50, payload)
                    )

    def test_decode_jitter_status_preserves_uint16_values(self) -> None:
        frame = Frame(
            TYPE_JITTER_STATUS,
            0x50,
            bytes((0x00, 0x00, 0xFF, 0xFF, 0x00, 0x80, 0xFF, 0x7F)),
        )

        self.assertEqual(
            decode_jitter_status(frame),
            JitterStatus(
                actuator_ms=0,
                control_ms=65535,
                sensor_safety_ms=32768,
                communication_ms=32767,
            ),
        )

    def test_runtime_memory_status_exact_payload_length(self) -> None:
        payload = bytes((0x01, 0x00, 0x02, 0x00, 0x03, 0x00))
        frame = Frame(TYPE_RUNTIME_MEMORY_STATUS, 0x60, payload)
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 12)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_runtime_memory_status_little_endian(self) -> None:
        frame = Frame(
            TYPE_RUNTIME_MEMORY_STATUS,
            0x60,
            bytes((0x34, 0x12, 0xCD, 0xAB, 0x00, 0x01)),
        )

        self.assertEqual(
            decode_runtime_memory_status(frame),
            RuntimeMemoryStatus(
                min_free_bytes=0x1234,
                painted_bytes=0xABCD,
                used_painted_bytes=0x0100,
            ),
        )

    def test_runtime_memory_status_rejects_wrong_payload_length(self) -> None:
        for payload in (b"", bytes(5), bytes(7)):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_runtime_memory_status(
                        Frame(TYPE_RUNTIME_MEMORY_STATUS, 0x60, payload)
                    )

    def test_runtime_memory_status_preserves_uint16_values(self) -> None:
        frame = Frame(
            TYPE_RUNTIME_MEMORY_STATUS,
            0x60,
            bytes((0x00, 0x00, 0xFF, 0xFF, 0x00, 0x80)),
        )

        self.assertEqual(
            decode_runtime_memory_status(frame),
            RuntimeMemoryStatus(
                min_free_bytes=0,
                painted_bytes=65535,
                used_painted_bytes=32768,
            ),
        )

    def test_validate_observe_seconds_requires_positive_value(self) -> None:
        validate_observe_seconds(0.1)

        for value in (0.0, -1.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_observe_seconds(value)

    def test_cpu_load_status_exact_payload_length(self) -> None:
        payload = bytes((1, 2, 3, 4, 5, 6, 7, 8))
        frame = Frame(TYPE_CPU_LOAD_STATUS, 0x70, payload)
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 14)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_cpu_load_status_little_endian_uint32(self) -> None:
        frame = Frame(
            TYPE_CPU_LOAD_STATUS,
            0x70,
            bytes((0x78, 0x56, 0x34, 0x12, 0xEF, 0xCD, 0xAB, 0x90)),
        )

        self.assertEqual(
            decode_cpu_load_status(frame),
            CpuLoadStatus(busy_ticks=0x12345678, elapsed_ms=0x90ABCDEF),
        )

    def test_scheduled_task_utilization_handles_zero_elapsed(self) -> None:
        self.assertEqual(calculate_scheduled_task_utilization(1234, 0), 0.0)

    def test_scheduled_task_utilization_calculation(self) -> None:
        self.assertEqual(
            calculate_scheduled_task_utilization(50000, 1000),
            2.5,
        )

    def test_overrun_status_exact_payload_length(self) -> None:
        payload = bytes((1, 0, 2, 0, 3, 0, 4, 0))
        frame = Frame(TYPE_OVERRUN_STATUS, 0x71, payload)
        encoded = encode_frame(frame)

        self.assertEqual(len(encoded), 14)
        self.assertEqual(decode_frame(encoded), frame)

    def test_decode_overrun_status_four_uint16_values(self) -> None:
        frame = Frame(
            TYPE_OVERRUN_STATUS,
            0x71,
            bytes((0x34, 0x12, 0xCD, 0xAB, 0x00, 0x80, 0xFF, 0xFF)),
        )

        self.assertEqual(
            decode_overrun_status(frame),
            OverrunStatus(
                actuator=0x1234,
                control=0xABCD,
                sensor_safety=0x8000,
                communication=0xFFFF,
            ),
        )

    def test_runtime_profile_status_rejects_invalid_payloads(self) -> None:
        decoders_and_types = (
            (decode_cpu_load_status, TYPE_CPU_LOAD_STATUS),
            (decode_overrun_status, TYPE_OVERRUN_STATUS),
        )

        for decoder, frame_type in decoders_and_types:
            for payload in (b"", bytes(7), bytes(9)):
                with self.subTest(
                    decoder=decoder.__name__, payload_length=len(payload)
                ):
                    with self.assertRaises(ProtocolError):
                        decoder(Frame(frame_type, 0x70, payload))

    def test_reset_cause_payload_is_exactly_one_byte(self) -> None:
        frame = Frame(TYPE_RESET_CAUSE, 0x72, bytes((0x08,)))

        self.assertEqual(len(encode_frame(frame)), 7)
        self.assertEqual(
            decode_reset_cause(frame),
            ResetCauseStatus(reset_cause=0x08),
        )

    def test_reset_cause_rejects_bad_payload_length(self) -> None:
        for payload in (b"", bytes((0x08, 0x00))):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_reset_cause(
                        Frame(TYPE_RESET_CAUSE, 0x72, payload)
                    )

    def test_wdrf_mask_detection(self) -> None:
        self.assertTrue(reset_cause_has_wdrf(0x08))
        self.assertTrue(reset_cause_has_wdrf(0x0A))
        self.assertFalse(reset_cause_has_wdrf(0x00))
        self.assertFalse(reset_cause_has_wdrf(0x02))

    def test_watchdog_status_zero_marker(self) -> None:
        frame = Frame(TYPE_WATCHDOG_STATUS, 0x73, bytes((0,)))

        self.assertEqual(len(encode_frame(frame)), 7)
        self.assertEqual(
            decode_watchdog_status(frame),
            WatchdogStatus(timeout_marker=0),
        )

    def test_watchdog_status_one_marker(self) -> None:
        frame = Frame(TYPE_WATCHDOG_STATUS, 0x73, bytes((1,)))

        self.assertEqual(
            decode_watchdog_status(frame),
            WatchdogStatus(timeout_marker=1),
        )

    def test_watchdog_status_rejects_bad_payload(self) -> None:
        for payload in (b"", bytes((0, 1)), bytes((2,))):
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError):
                    decode_watchdog_status(
                        Frame(TYPE_WATCHDOG_STATUS, 0x73, payload)
                    )

    def test_watchdog_pass_requires_recovery_ping_and_marker(self) -> None:
        self.assertTrue(watchdog_test_passed(True, True, 1))
        self.assertFalse(watchdog_test_passed(False, True, 1))
        self.assertFalse(watchdog_test_passed(True, False, 1))
        self.assertFalse(watchdog_test_passed(True, True, 0))

    def test_encode_rejects_payload_over_maximum(self) -> None:
        with self.assertRaises(ProtocolError):
            encode_frame(Frame(TYPE_ECHO, 0x20, bytes(MAX_PAYLOAD + 1)))

    def test_encode_rejects_invalid_octets(self) -> None:
        invalid_frames = (
            Frame(-1, 0x10, b""),
            Frame(0x100, 0x10, b""),
            Frame(TYPE_PING, -1, b""),
            Frame(TYPE_PING, 0x100, b""),
        )

        for frame in invalid_frames:
            with self.subTest(frame=frame):
                with self.assertRaises(ProtocolError):
                    encode_frame(frame)

    def test_decode_rejects_bad_sof(self) -> None:
        encoded = bytearray(encode_frame(Frame(TYPE_PING, 0x2A, b"")))
        encoded[0] = 0x00

        with self.assertRaises(ProtocolError):
            decode_frame(bytes(encoded))

    def test_decode_rejects_bad_version(self) -> None:
        encoded = bytearray(encode_frame(Frame(TYPE_PING, 0x2A, b"")))
        encoded[1] = 0x02

        with self.assertRaises(ProtocolError):
            decode_frame(bytes(encoded))

    def test_decode_rejects_bad_crc(self) -> None:
        encoded = bytearray(encode_frame(Frame(TYPE_PING, 0x2A, b"")))
        encoded[-1] ^= 0xFF

        with self.assertRaises(CRCError):
            decode_frame(bytes(encoded))

    def test_decode_rejects_incoherent_length(self) -> None:
        encoded = bytearray(encode_frame(Frame(TYPE_PING, 0x2A, b"")))
        encoded[4] = 1

        with self.assertRaises(ProtocolError):
            decode_frame(bytes(encoded))

    def test_decode_rejects_payload_length_over_maximum(self) -> None:
        encoded = bytes((SOF, VERSION, TYPE_ECHO, 0x20, MAX_PAYLOAD + 1))
        encoded += bytes(MAX_PAYLOAD + 2)

        with self.assertRaises(ProtocolError):
            decode_frame(encoded)


class SerialLinkTests(unittest.TestCase):
    def test_read_exact_returns_requested_bytes(self) -> None:
        read_fd, write_fd = os.pipe()
        link = SerialLink("unused")
        link._fd = read_fd

        try:
            os.write(write_fd, b"ABC")
            self.assertEqual(link.read_exact(3, 0.1), b"ABC")
        finally:
            link.close()
            os.close(write_fd)

    def test_read_exact_times_out(self) -> None:
        read_fd, write_fd = os.pipe()
        link = SerialLink("unused")
        link._fd = read_fd

        try:
            with self.assertRaises(SerialTimeoutError):
                link.read_exact(1, 0.01)
        finally:
            link.close()
            os.close(write_fd)


if __name__ == "__main__":
    unittest.main()
