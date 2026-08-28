from __future__ import annotations

import json
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterator, Optional
from urllib.parse import unquote, urlsplit

if __package__:
    from .protocol import (
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
        calculate_scheduled_task_utilization,
        decode_comm_status,
        decode_cpu_load_status,
        decode_jitter_status,
        decode_overrun_status,
        decode_runtime_memory_status,
        decode_timing_status,
        decode_watchdog_status,
        encode_frame,
        ticks_to_microseconds,
    )
    from .serial_link import SerialLink, SerialTimeoutError
else:
    from protocol import (
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
        calculate_scheduled_task_utilization,
        decode_comm_status,
        decode_cpu_load_status,
        decode_jitter_status,
        decode_overrun_status,
        decode_runtime_memory_status,
        decode_timing_status,
        decode_watchdog_status,
        encode_frame,
        ticks_to_microseconds,
    )
    from serial_link import SerialLink, SerialTimeoutError


DEFAULT_DASHBOARD_HOST = "127.0.0.1"
DEFAULT_DASHBOARD_PORT = 8080
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_RESPONSE_TIMEOUT_SECONDS = 1.0
DEFAULT_STALE_AFTER_SECONDS = 3.0
DASHBOARD_HISTORY_LIMIT = 120
DASHBOARD_EVENT_LIMIT = 50

CONNECTION_CONNECTED = "CONNECTED"
CONNECTION_DEGRADED = "DEGRADED"
CONNECTION_DISCONNECTED = "DISCONNECTED"

ReadFrameFunction = Callable[[SerialLink, float], Frame]


def _utc_timestamp(epoch_seconds: float) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class DashboardSnapshot:
    connection: str = CONNECTION_DISCONNECTED
    updated_at_epoch: Optional[float] = None
    last_error: Optional[str] = None
    comm: Optional[CommStatus] = None
    timing: Optional[TimingStatus] = None
    jitter: Optional[JitterStatus] = None
    runtime_memory: Optional[RuntimeMemoryStatus] = None
    cpu: Optional[CpuLoadStatus] = None
    overruns: Optional[OverrunStatus] = None
    watchdog: Optional[WatchdogStatus] = None

    def to_dict(
        self,
        now_epoch: Optional[float] = None,
        stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    ) -> dict:
        now = time.time() if now_epoch is None else now_epoch
        age_seconds: Optional[float] = None
        last_update: Optional[str] = None

        if self.updated_at_epoch is not None:
            age_seconds = max(0.0, now - self.updated_at_epoch)
            last_update = _utc_timestamp(self.updated_at_epoch)

        stale = (
            self.connection != CONNECTION_CONNECTED
            or age_seconds is None
            or age_seconds > stale_after_seconds
        )

        comm = {
            "rx_overflow": None,
            "parser_timeout": None,
            "crc_errors": None,
        }
        if self.comm is not None:
            comm = {
                "rx_overflow": self.comm.uart_rx_overflow,
                "parser_timeout": self.comm.parser_timeouts,
                "crc_errors": self.comm.crc_errors,
            }

        timing = {
            "actuator_us": None,
            "control_us": None,
            "sensor_safety_us": None,
            "communication_us": None,
        }
        if self.timing is not None:
            timing = {
                "actuator_us": ticks_to_microseconds(
                    self.timing.actuator_ticks
                ),
                "control_us": ticks_to_microseconds(
                    self.timing.control_ticks
                ),
                "sensor_safety_us": ticks_to_microseconds(
                    self.timing.sensor_safety_ticks
                ),
                "communication_us": ticks_to_microseconds(
                    self.timing.communication_ticks
                ),
            }

        jitter = {
            "actuator_ms": None,
            "control_ms": None,
            "sensor_safety_ms": None,
            "communication_ms": None,
        }
        if self.jitter is not None:
            jitter = {
                "actuator_ms": self.jitter.actuator_ms,
                "control_ms": self.jitter.control_ms,
                "sensor_safety_ms": self.jitter.sensor_safety_ms,
                "communication_ms": self.jitter.communication_ms,
            }

        runtime_memory = {
            "painted_region_bytes": None,
            "used_painted_bytes": None,
            "minimum_free_observed_bytes": None,
        }
        if self.runtime_memory is not None:
            runtime_memory = {
                "painted_region_bytes": self.runtime_memory.painted_bytes,
                "used_painted_bytes": self.runtime_memory.used_painted_bytes,
                "minimum_free_observed_bytes": (
                    self.runtime_memory.min_free_bytes
                ),
            }

        cpu = {
            "busy_ticks": None,
            "elapsed_ms": None,
            "scheduled_task_utilization_percent": None,
        }
        if self.cpu is not None:
            cpu = {
                "busy_ticks": self.cpu.busy_ticks,
                "elapsed_ms": self.cpu.elapsed_ms,
                "scheduled_task_utilization_percent": (
                    calculate_scheduled_task_utilization(
                        self.cpu.busy_ticks,
                        self.cpu.elapsed_ms,
                    )
                ),
            }

        overruns = {
            "actuator": None,
            "control": None,
            "sensor_safety": None,
            "communication": None,
        }
        if self.overruns is not None:
            overruns = {
                "actuator": self.overruns.actuator,
                "control": self.overruns.control,
                "sensor_safety": self.overruns.sensor_safety,
                "communication": self.overruns.communication,
            }

        previous_timeout_detected: Optional[bool] = None
        if self.watchdog is not None:
            previous_timeout_detected = self.watchdog.timeout_marker == 1

        return {
            "connection": self.connection,
            "last_update": last_update,
            "age_seconds": (
                None if age_seconds is None else round(age_seconds, 2)
            ),
            "stale": stale,
            "last_error": self.last_error,
            "comm": comm,
            "timing": timing,
            "jitter": jitter,
            "runtime_memory": runtime_memory,
            "cpu": cpu,
            "overruns": overruns,
            "watchdog": {
                "previous_timeout_detected": previous_timeout_detected,
            },
        }


class DashboardStore:
    def __init__(
        self,
        history_limit: int = DASHBOARD_HISTORY_LIMIT,
        event_limit: int = DASHBOARD_EVENT_LIMIT,
        stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    ) -> None:
        if history_limit <= 0:
            raise ValueError("history_limit must be greater than zero")
        if event_limit <= 0:
            raise ValueError("event_limit must be greater than zero")
        if stale_after_seconds <= 0.0:
            raise ValueError("stale_after_seconds must be greater than zero")

        self._lock = threading.Lock()
        self._snapshot = DashboardSnapshot()
        self._history: deque[dict] = deque(maxlen=history_limit)
        self._events: deque[dict] = deque(maxlen=event_limit)
        self._stale_after_seconds = stale_after_seconds

    def _append_event_locked(
        self,
        timestamp: float,
        level: str,
        message: str,
    ) -> None:
        self._events.append(
            {
                "timestamp": _utc_timestamp(timestamp),
                "level": level,
                "message": message[:256],
            }
        )

    def _record_value_change_events_locked(
        self,
        previous: DashboardSnapshot,
        current: DashboardSnapshot,
        timestamp: float,
    ) -> None:
        if previous.comm is not None and current.comm is not None:
            comm_fields = (
                ("RX overflow", "uart_rx_overflow"),
                ("Parser timeout", "parser_timeouts"),
                ("CRC error", "crc_errors"),
            )
            for label, attribute in comm_fields:
                before = getattr(previous.comm, attribute)
                after = getattr(current.comm, attribute)
                if before != after:
                    self._append_event_locked(
                        timestamp,
                        "warning",
                        f"{label} counter changed: {before} → {after}",
                    )

        previous_marker = (
            None
            if previous.watchdog is None
            else previous.watchdog.timeout_marker
        )
        current_marker = (
            None if current.watchdog is None else current.watchdog.timeout_marker
        )
        if current_marker == 1 and previous_marker != 1:
            self._append_event_locked(
                timestamp,
                "warning",
                "Previous watchdog timeout marker detected",
            )

        if previous.overruns is not None and current.overruns is not None:
            overrun_fields = (
                ("Actuator", "actuator"),
                ("Control", "control"),
                ("Sensor/Safety", "sensor_safety"),
                ("Communication", "communication"),
            )
            for label, attribute in overrun_fields:
                before = getattr(previous.overruns, attribute)
                after = getattr(current.overruns, attribute)
                if before != after:
                    self._append_event_locked(
                        timestamp,
                        "warning",
                        f"{label} overrun counter changed: {before} → {after}",
                    )

    def record_success(
        self,
        comm: CommStatus,
        timing: TimingStatus,
        jitter: JitterStatus,
        runtime_memory: RuntimeMemoryStatus,
        cpu: CpuLoadStatus,
        overruns: OverrunStatus,
        watchdog: WatchdogStatus,
        now_epoch: Optional[float] = None,
    ) -> None:
        timestamp = time.time() if now_epoch is None else now_epoch

        with self._lock:
            previous = self._snapshot
            current = DashboardSnapshot(
                connection=CONNECTION_CONNECTED,
                updated_at_epoch=timestamp,
                last_error=None,
                comm=comm,
                timing=timing,
                jitter=jitter,
                runtime_memory=runtime_memory,
                cpu=cpu,
                overruns=overruns,
                watchdog=watchdog,
            )

            if previous.connection != CONNECTION_CONNECTED:
                message = (
                    "Connected"
                    if previous.updated_at_epoch is None
                    else "Connection recovered"
                )
                self._append_event_locked(timestamp, "info", message)

            self._record_value_change_events_locked(
                previous, current, timestamp
            )
            self._snapshot = current

            payload = current.to_dict(
                now_epoch=timestamp,
                stale_after_seconds=self._stale_after_seconds,
            )
            self._history.append(
                {
                    "timestamp": payload["last_update"],
                    "cpu_utilization_percent": payload["cpu"][
                        "scheduled_task_utilization_percent"
                    ],
                    "minimum_free_observed_bytes": payload[
                        "runtime_memory"
                    ]["minimum_free_observed_bytes"],
                    "rx_overflow": payload["comm"]["rx_overflow"],
                    "parser_timeout": payload["comm"]["parser_timeout"],
                    "crc_errors": payload["comm"]["crc_errors"],
                }
            )

    def record_failure(
        self,
        error: str,
        now_epoch: Optional[float] = None,
    ) -> None:
        timestamp = time.time() if now_epoch is None else now_epoch
        bounded_error = (error or "serial polling failed")[:256]

        with self._lock:
            previous = self._snapshot
            if previous.updated_at_epoch is None:
                connection = CONNECTION_DISCONNECTED
            elif (
                timestamp - previous.updated_at_epoch
                > self._stale_after_seconds
            ):
                connection = CONNECTION_DISCONNECTED
            else:
                connection = CONNECTION_DEGRADED

            self._snapshot = replace(
                previous,
                connection=connection,
                last_error=bounded_error,
            )

            if connection != previous.connection:
                label = (
                    "Connection degraded"
                    if connection == CONNECTION_DEGRADED
                    else "Disconnected"
                )
                level = (
                    "warning"
                    if connection == CONNECTION_DEGRADED
                    else "error"
                )
                self._append_event_locked(
                    timestamp,
                    level,
                    f"{label}: {bounded_error}",
                )

    def status_payload(self, now_epoch: Optional[float] = None) -> dict:
        with self._lock:
            payload = self._snapshot.to_dict(
                now_epoch=now_epoch,
                stale_after_seconds=self._stale_after_seconds,
            )
            payload["events"] = list(reversed(self._events))
            return payload

    def history_payload(self) -> dict:
        with self._lock:
            return {"samples": list(self._history)}


class DashboardPoller(threading.Thread):
    def __init__(
        self,
        link: SerialLink,
        store: DashboardStore,
        read_frame: ReadFrameFunction,
        stop_event: Optional[threading.Event] = None,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        response_timeout_seconds: float = DEFAULT_RESPONSE_TIMEOUT_SECONDS,
    ) -> None:
        if poll_interval_seconds <= 0.0:
            raise ValueError("poll_interval_seconds must be greater than zero")
        if response_timeout_seconds <= 0.0:
            raise ValueError(
                "response_timeout_seconds must be greater than zero"
            )

        super().__init__(name="sentry-dashboard-poller", daemon=True)
        self._link = link
        self._store = store
        self._read_frame = read_frame
        self._stop_event = stop_event or threading.Event()
        self._poll_interval_seconds = poll_interval_seconds
        self._response_timeout_seconds = response_timeout_seconds
        self._sequence = 0x90

    def _next_sequence(self) -> int:
        sequence = self._sequence
        self._sequence = (self._sequence + 1) & 0xFF
        return sequence

    def _request(self, request_type: int, response_type: int, decoder):
        sequence = self._next_sequence()
        request = Frame(request_type, sequence, b"")
        self._link.write(encode_frame(request))
        response = self._read_frame(
            self._link, self._response_timeout_seconds
        )

        if response.frame_type != response_type:
            raise ValueError(
                f"unexpected response type 0x{response.frame_type:02X}; "
                f"expected 0x{response_type:02X}"
            )
        if response.sequence != sequence:
            raise ValueError(
                f"unexpected response sequence 0x{response.sequence:02X}; "
                f"expected 0x{sequence:02X}"
            )

        return decoder(response)

    def poll_once(self) -> bool:
        try:
            comm = self._request(
                TYPE_GET_COMM_STATUS,
                TYPE_COMM_STATUS,
                decode_comm_status,
            )
            timing = self._request(
                TYPE_GET_TIMING_STATUS,
                TYPE_TIMING_STATUS,
                decode_timing_status,
            )
            jitter = self._request(
                TYPE_GET_JITTER_STATUS,
                TYPE_JITTER_STATUS,
                decode_jitter_status,
            )
            runtime_memory = self._request(
                TYPE_GET_RUNTIME_MEMORY_STATUS,
                TYPE_RUNTIME_MEMORY_STATUS,
                decode_runtime_memory_status,
            )
            cpu = self._request(
                TYPE_GET_CPU_LOAD_STATUS,
                TYPE_CPU_LOAD_STATUS,
                decode_cpu_load_status,
            )
            overruns = self._request(
                TYPE_GET_OVERRUN_STATUS,
                TYPE_OVERRUN_STATUS,
                decode_overrun_status,
            )
            watchdog = self._request(
                TYPE_GET_WATCHDOG_STATUS,
                TYPE_WATCHDOG_STATUS,
                decode_watchdog_status,
            )
        except SerialTimeoutError as error:
            timeout_message = f"{type(error).__name__}: {error}"
            self._store.record_failure(timeout_message)
            try:
                self._link.recover_rx_after_timeout()
            except Exception as recovery_error:
                self._store.record_failure(
                    f"{timeout_message}; RX recovery failed: "
                    f"{type(recovery_error).__name__}: {recovery_error}"
                )
            return False
        except Exception as error:
            self._store.record_failure(
                f"{type(error).__name__}: {error}"
            )
            return False

        self._store.record_success(
            comm=comm,
            timing=timing,
            jitter=jitter,
            runtime_memory=runtime_memory,
            cpu=cpu,
            overruns=overruns,
            watchdog=watchdog,
        )
        return True

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        next_cycle_at = time.monotonic()

        while not self._stop_event.is_set():
            remaining = max(0.0, next_cycle_at - time.monotonic())
            if remaining > 0.0 and self._stop_event.wait(remaining):
                break
            if self._stop_event.is_set():
                break

            succeeded = self.poll_once()
            now = time.monotonic()

            if succeeded:
                next_cycle_at += self._poll_interval_seconds
                if next_cycle_at <= now:
                    next_cycle_at = now + self._poll_interval_seconds
            else:
                # A failed cycle, including RX recovery after a timeout, is
                # followed by one complete clean interval before more traffic.
                next_cycle_at = now + self._poll_interval_seconds


@contextmanager
def open_serial_session(
    port: str,
    link_factory: Callable[[str], SerialLink] = SerialLink,
) -> Iterator[SerialLink]:
    link = link_factory(port)
    link.open()
    try:
        yield link
    finally:
        link.close()


class DashboardRequestHandler(BaseHTTPRequestHandler):
    server_version = "SentryCellDashboard/1.0"

    def _send_headers(
        self,
        status: int,
        content_type: str,
        content_length: int,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(content_length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()

    def _send_json(self, payload: dict, send_body: bool) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._send_headers(200, "application/json; charset=utf-8", len(body))
        if send_body:
            self.wfile.write(body)

    def _send_static(self, route: str, send_body: bool) -> None:
        static_routes = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"),
            "/dashboard.js": (
                "dashboard.js",
                "text/javascript; charset=utf-8",
            ),
        }
        asset = static_routes.get(route)
        if asset is None:
            self.send_error(404, "Not found")
            return

        filename, content_type = asset
        asset_path = self.server.static_directory / filename
        try:
            body = asset_path.read_bytes()
        except OSError:
            self.send_error(404, "Not found")
            return

        self._send_headers(200, content_type, len(body))
        if send_body:
            self.wfile.write(body)

    def _dispatch(self, send_body: bool) -> None:
        route = unquote(urlsplit(self.path).path)
        if ".." in route.split("/"):
            self.send_error(404, "Not found")
            return

        if route == "/api/status":
            self._send_json(
                self.server.dashboard_store.status_payload(), send_body
            )
            return
        if route == "/api/history":
            self._send_json(
                self.server.dashboard_store.history_payload(), send_body
            )
            return

        self._send_static(route, send_body)

    def do_GET(self) -> None:
        self._dispatch(send_body=True)

    def do_HEAD(self) -> None:
        self._dispatch(send_body=False)

    def log_message(self, format_string: str, *arguments) -> None:
        return


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        dashboard_store: DashboardStore,
        static_directory: Optional[Path] = None,
    ) -> None:
        self.dashboard_store = dashboard_store
        self.static_directory = (
            Path(__file__).resolve().with_name("dashboard_static")
            if static_directory is None
            else static_directory.resolve()
        )
        super().__init__(server_address, DashboardRequestHandler)


def create_http_server(
    host: str,
    port: int,
    store: DashboardStore,
    static_directory: Optional[Path] = None,
) -> DashboardHTTPServer:
    return DashboardHTTPServer(
        (host, port),
        dashboard_store=store,
        static_directory=static_directory,
    )


def validate_dashboard_options(host: str, port: int) -> None:
    if not host:
        raise ValueError("--dashboard-host must not be empty")
    if not 1 <= port <= 65535:
        raise ValueError("--dashboard-port must be in range 1..65535")


def run_dashboard(
    serial_port: str,
    host: str,
    http_port: int,
    read_frame: ReadFrameFunction,
) -> None:
    validate_dashboard_options(host, http_port)
    store = DashboardStore()
    http_server = create_http_server(host, http_port, store)
    poller: Optional[DashboardPoller] = None

    try:
        with open_serial_session(serial_port) as link:
            time.sleep(2.2)
            poller = DashboardPoller(
                link=link,
                store=store,
                read_frame=read_frame,
            )

            print("SENTRY-CELL UNO Dashboard")
            print(f"Serial: {serial_port}")
            print(f"Dashboard: http://{host}:{http_port}")
            print()
            print("Press Ctrl+C to stop.")
            poller.start()

            try:
                http_server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
            finally:
                poller.stop()
                poller.join(timeout=2.5)
    finally:
        http_server.server_close()
