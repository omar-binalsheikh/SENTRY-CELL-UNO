import json
import termios
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

from supervisor.dashboard import (
    CONNECTION_CONNECTED,
    CONNECTION_DISCONNECTED,
    DEFAULT_DASHBOARD_HOST,
    DEFAULT_DASHBOARD_PORT,
    DashboardPoller,
    DashboardSnapshot,
    DashboardStore,
    create_http_server,
    open_serial_session,
)
from supervisor.main import parse_args
from supervisor.protocol import (
    TYPE_COMM_STATUS,
    TYPE_CPU_LOAD_STATUS,
    TYPE_GET_COMM_STATUS,
    TYPE_GET_CPU_LOAD_STATUS,
    TYPE_GET_JITTER_STATUS,
    TYPE_GET_OVERRUN_STATUS,
    TYPE_GET_RUNTIME_MEMORY_STATUS,
    TYPE_GET_TIMING_STATUS,
    TYPE_GET_WATCHDOG_STATUS,
    TYPE_JITTER_STATUS,
    TYPE_OVERRUN_STATUS,
    TYPE_RUNTIME_MEMORY_STATUS,
    TYPE_TIMING_STATUS,
    TYPE_WATCHDOG_STATUS,
    CommStatus,
    CpuLoadStatus,
    Frame,
    JitterStatus,
    OverrunStatus,
    RuntimeMemoryStatus,
    TimingStatus,
    WatchdogStatus,
    decode_frame,
)
from supervisor.serial_link import (
    RX_TIMEOUT_RECOVERY_SETTLE_SECONDS,
    SerialLink,
    SerialTimeoutError,
)


def _u16_payload(*values: int) -> bytes:
    return b"".join(value.to_bytes(2, "little") for value in values)


def _u32_payload(*values: int) -> bytes:
    return b"".join(value.to_bytes(4, "little") for value in values)


def _record_sample(
    store: DashboardStore,
    index: int,
    now_epoch: float | None = None,
) -> None:
    store.record_success(
        comm=CommStatus(index, index, index),
        timing=TimingStatus(2, 4, 6, 8),
        jitter=JitterStatus(0, 1, 2, 3),
        runtime_memory=RuntimeMemoryStatus(1600 - index, 1700, 100 + index),
        cpu=CpuLoadStatus(50000 + index, 1000),
        overruns=OverrunStatus(index, 0, 0, 0),
        watchdog=WatchdogStatus(0),
        now_epoch=(1000.0 + index if now_epoch is None else now_epoch),
    )


class DashboardSnapshotTests(unittest.TestCase):
    def test_snapshot_serialization_uses_real_status_fields(self) -> None:
        snapshot = DashboardSnapshot(
            connection=CONNECTION_CONNECTED,
            updated_at_epoch=1000.0,
            comm=CommStatus(1, 2, 3),
            timing=TimingStatus(2, 4, 6, 8),
            jitter=JitterStatus(0, 1, 2, 3),
            runtime_memory=RuntimeMemoryStatus(1600, 1700, 100),
            cpu=CpuLoadStatus(50000, 1000),
            overruns=OverrunStatus(0, 1, 2, 3),
            watchdog=WatchdogStatus(1),
        )

        payload = snapshot.to_dict(now_epoch=1001.0)

        self.assertEqual(payload["connection"], CONNECTION_CONNECTED)
        self.assertFalse(payload["stale"])
        self.assertEqual(payload["comm"]["crc_errors"], 3)
        self.assertEqual(payload["timing"]["actuator_us"], 1.0)
        self.assertEqual(payload["jitter"]["actuator_ms"], 0)
        self.assertEqual(
            payload["runtime_memory"]["minimum_free_observed_bytes"],
            1600,
        )
        self.assertEqual(
            payload["cpu"]["scheduled_task_utilization_percent"],
            2.5,
        )
        self.assertTrue(
            payload["watchdog"]["previous_timeout_detected"]
        )


class DashboardStoreTests(unittest.TestCase):
    def test_history_is_bounded(self) -> None:
        store = DashboardStore(history_limit=3)

        for index in range(5):
            _record_sample(store, index)

        history = store.history_payload()["samples"]
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["rx_overflow"], 2)
        self.assertEqual(history[-1]["rx_overflow"], 4)

    def test_event_log_is_bounded(self) -> None:
        store = DashboardStore(event_limit=2)

        for index in range(4):
            _record_sample(store, index)

        events = store.status_payload(now_epoch=1004.0)["events"]
        self.assertEqual(len(events), 2)
        self.assertTrue(
            all("counter changed" in event["message"] for event in events)
        )


class SerialSessionTests(unittest.TestCase):
    def test_serial_session_opens_and_closes_exactly_once(self) -> None:
        created = []

        class FakeLink:
            def __init__(self, port: str) -> None:
                self.port = port
                self.open_count = 0
                self.close_count = 0

            def open(self) -> None:
                self.open_count += 1

            def close(self) -> None:
                self.close_count += 1

        def factory(port: str):
            link = FakeLink(port)
            created.append(link)
            return link

        with open_serial_session("/dev/example", factory) as link:
            self.assertEqual(link.open_count, 1)
            self.assertEqual(link.close_count, 0)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].close_count, 1)

    def test_dashboard_cli_defaults_to_loopback(self) -> None:
        args = parse_args(["--port", "/dev/example", "--dashboard"])

        self.assertTrue(args.dashboard)
        self.assertEqual(args.dashboard_host, DEFAULT_DASHBOARD_HOST)
        self.assertEqual(args.dashboard_host, "127.0.0.1")
        self.assertEqual(args.dashboard_port, DEFAULT_DASHBOARD_PORT)
        self.assertEqual(args.dashboard_port, 8080)


class SerialRecoveryTests(unittest.TestCase):
    def test_recovery_waits_then_flushes_rx_without_reopen_or_dtr(self) -> None:
        link = SerialLink("unused")
        link._fd = 123
        operations = []

        with (
            mock.patch(
                "supervisor.serial_link.time.sleep",
                side_effect=lambda delay: operations.append(("sleep", delay)),
            ) as sleep_call,
            mock.patch(
                "supervisor.serial_link.termios.tcflush",
                side_effect=lambda fd, queue: operations.append(
                    ("flush", fd, queue)
                ),
            ) as flush_call,
            mock.patch("supervisor.serial_link.os.open") as open_call,
            mock.patch("supervisor.serial_link.termios.tcsetattr") as set_call,
        ):
            link.recover_rx_after_timeout()

        expected_settle = 0.100 + (14 * 10 / 9600)
        self.assertAlmostEqual(
            RX_TIMEOUT_RECOVERY_SETTLE_SECONDS,
            expected_settle,
        )
        sleep_call.assert_called_once_with(expected_settle)
        flush_call.assert_called_once()
        self.assertEqual(operations[0][0], "sleep")
        self.assertEqual(operations[1][0], "flush")
        self.assertEqual(operations[1][1], 123)
        self.assertEqual(operations[1][2], termios.TCIFLUSH)
        open_call.assert_not_called()
        set_call.assert_not_called()
        self.assertEqual(link._fd, 123)


class DashboardPollerTests(unittest.TestCase):
    class FakeLink:
        def __init__(self) -> None:
            self.writes = []

        def write(self, data: bytes) -> None:
            self.writes.append(data)

    class RecoveringFakeLink(FakeLink):
        def __init__(self) -> None:
            super().__init__()
            self.recovery_count = 0
            self.stale_rx = bytearray()

        def recover_rx_after_timeout(self) -> None:
            self.recovery_count += 1
            self.stale_rx.clear()

    @staticmethod
    def _read_response(link, timeout_s: float) -> Frame:
        del timeout_s
        request = decode_frame(link.writes[-1])
        responses = {
            TYPE_GET_COMM_STATUS: Frame(
                TYPE_COMM_STATUS, request.sequence, bytes((1, 2, 3))
            ),
            TYPE_GET_TIMING_STATUS: Frame(
                TYPE_TIMING_STATUS,
                request.sequence,
                _u16_payload(2, 4, 6, 8),
            ),
            TYPE_GET_JITTER_STATUS: Frame(
                TYPE_JITTER_STATUS,
                request.sequence,
                _u16_payload(0, 1, 2, 3),
            ),
            TYPE_GET_RUNTIME_MEMORY_STATUS: Frame(
                TYPE_RUNTIME_MEMORY_STATUS,
                request.sequence,
                _u16_payload(1659, 1721, 62),
            ),
            TYPE_GET_CPU_LOAD_STATUS: Frame(
                TYPE_CPU_LOAD_STATUS,
                request.sequence,
                _u32_payload(50000, 1000),
            ),
            TYPE_GET_OVERRUN_STATUS: Frame(
                TYPE_OVERRUN_STATUS,
                request.sequence,
                _u16_payload(0, 0, 0, 0),
            ),
            TYPE_GET_WATCHDOG_STATUS: Frame(
                TYPE_WATCHDOG_STATUS,
                request.sequence,
                bytes((0,)),
            ),
        }
        return responses[request.frame_type]

    def test_one_link_is_reused_for_all_seven_queries(self) -> None:
        link = self.FakeLink()
        observed_link_ids = []

        def read_response(observed_link, timeout_s: float) -> Frame:
            observed_link_ids.append(id(observed_link))
            return self._read_response(observed_link, timeout_s)

        store = DashboardStore()
        poller = DashboardPoller(link, store, read_response)

        self.assertTrue(poller.poll_once())
        self.assertEqual(len(link.writes), 7)
        self.assertEqual(set(observed_link_ids), {id(link)})
        self.assertEqual(
            store.status_payload()["connection"], CONNECTION_CONNECTED
        )
        self.assertEqual(len(store.history_payload()["samples"]), 1)

    def test_polling_failure_is_recorded_without_raising(self) -> None:
        class FailingLink:
            def write(self, data: bytes) -> None:
                del data
                raise OSError("serial unavailable")

        store = DashboardStore()
        poller = DashboardPoller(
            FailingLink(),
            store,
            lambda link, timeout: None,
        )

        self.assertFalse(poller.poll_once())
        payload = store.status_payload()
        self.assertEqual(payload["connection"], CONNECTION_DISCONNECTED)
        self.assertIn("serial unavailable", payload["last_error"])

    def test_header_timeout_recovers_aborts_cycle_and_later_recovers(self) -> None:
        link = self.RecoveringFakeLink()
        store = DashboardStore()
        _record_sample(store, 0, now_epoch=time.time())
        read_count = 0

        def read_response(observed_link, timeout_s: float) -> Frame:
            nonlocal read_count
            read_count += 1
            if read_count == 1:
                raise SerialTimeoutError(
                    "timed out waiting for 5 bytes (received 0)"
                )
            return self._read_response(observed_link, timeout_s)

        poller = DashboardPoller(link, store, read_response)

        self.assertFalse(poller.poll_once())
        self.assertEqual(len(link.writes), 1)
        self.assertEqual(link.recovery_count, 1)
        failed_payload = store.status_payload()
        self.assertEqual(failed_payload["connection"], "DEGRADED")
        self.assertIn(
            "timed out waiting for 5 bytes (received 0)",
            failed_payload["last_error"],
        )
        self.assertTrue(
            any(
                "Connection degraded" in event["message"]
                and "timed out waiting for 5 bytes" in event["message"]
                for event in failed_payload["events"]
            )
        )

        self.assertTrue(poller.poll_once())
        recovered_payload = store.status_payload()
        self.assertEqual(
            recovered_payload["connection"], CONNECTION_CONNECTED
        )
        self.assertTrue(
            any(
                event["message"] == "Connection recovered"
                for event in recovered_payload["events"]
            )
        )

    def test_partial_payload_timeout_discards_late_tail(self) -> None:
        link = self.RecoveringFakeLink()
        store = DashboardStore()
        read_count = 0

        def read_response(observed_link, timeout_s: float) -> Frame:
            nonlocal read_count
            read_count += 1
            if read_count == 1:
                observed_link.stale_rx.extend(b"\x11\x22\x33")
                raise SerialTimeoutError(
                    "timed out waiting for 4 bytes (received 1)"
                )
            if observed_link.stale_rx:
                raise AssertionError("late response tail was not discarded")
            return self._read_response(observed_link, timeout_s)

        poller = DashboardPoller(link, store, read_response)

        self.assertFalse(poller.poll_once())
        self.assertEqual(len(link.writes), 1)
        self.assertEqual(link.recovery_count, 1)
        self.assertEqual(link.stale_rx, b"")
        self.assertTrue(poller.poll_once())
        self.assertEqual(len(link.writes), 8)

    def test_failed_cycle_waits_full_interval_before_next_attempt(self) -> None:
        class RecordingStopEvent:
            def __init__(self) -> None:
                self.waits = []

            def is_set(self) -> bool:
                return False

            def wait(self, timeout: float) -> bool:
                self.waits.append(timeout)
                return True

            def set(self) -> None:
                return

        stop_event = RecordingStopEvent()
        poller = DashboardPoller(
            self.FakeLink(),
            DashboardStore(),
            self._read_response,
            stop_event=stop_event,
            poll_interval_seconds=1.0,
        )
        poller.poll_once = mock.Mock(return_value=False)

        with mock.patch(
            "supervisor.dashboard.time.monotonic",
            side_effect=(0.0, 0.0, 1.2, 1.2),
        ):
            poller.run()

        poller.poll_once.assert_called_once_with()
        self.assertEqual(len(stop_event.waits), 1)
        self.assertAlmostEqual(stop_event.waits[0], 1.0)

    def test_poller_thread_stops_cleanly_after_failures(self) -> None:
        class FailingLink:
            def write(self, data: bytes) -> None:
                del data
                raise OSError("serial unavailable")

        poller = DashboardPoller(
            FailingLink(),
            DashboardStore(),
            lambda link, timeout: None,
            poll_interval_seconds=0.01,
            response_timeout_seconds=0.01,
        )
        poller.start()
        time.sleep(0.03)
        poller.stop()
        poller.join(timeout=1.0)

        self.assertFalse(poller.is_alive())


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = DashboardStore()
        self.server = create_http_server("127.0.0.1", 0, self.store)
        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        self.server_thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=1.0)

    def test_api_status_returns_json_snapshot(self) -> None:
        with urllib.request.urlopen(
            f"{self.base_url}/api/status", timeout=1.0
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["connection"], CONNECTION_DISCONNECTED)
        self.assertTrue(payload["stale"])
        self.assertIsNone(payload["cpu"]["busy_ticks"])

    def test_static_assets_are_served_without_device(self) -> None:
        expected_markers = {
            "/": b"SENTRY-CELL UNO",
            "/dashboard.css": b"--bg:",
            "/dashboard.js": b"LIVE DEVICE TELEMETRY",
        }

        for route, marker in expected_markers.items():
            with self.subTest(route=route):
                with urllib.request.urlopen(
                    f"{self.base_url}{route}", timeout=1.0
                ) as response:
                    body = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn(marker, body)

    def test_static_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(
                f"{self.base_url}/%2e%2e/protocol.py", timeout=1.0
            )

        self.assertEqual(context.exception.code, 404)
        context.exception.close()


if __name__ == "__main__":
    unittest.main()
