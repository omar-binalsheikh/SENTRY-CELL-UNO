import os
import select
import termios
import time
from types import TracebackType
from typing import Optional, Type


class SerialLinkError(Exception):
    """Base exception for serial-link failures."""


class SerialTimeoutError(SerialLinkError):
    """Raised when a serial read cannot complete before its deadline."""


# Recovery allows the MCU's 100 ms parser timeout plus one maximum 14-byte
# protocol response at 9600 baud, 8N1 (10 bits per byte) to reach the host.
RX_TIMEOUT_RECOVERY_SETTLE_SECONDS = 0.100 + (14 * 10 / 9600)


class SerialLink:
    def __init__(self, port: str) -> None:
        self.port = port
        self._fd: Optional[int] = None

    def open(self) -> None:
        if self._fd is not None:
            raise SerialLinkError("serial port is already open")

        fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            attributes = termios.tcgetattr(fd)
            attributes[0] = 0
            attributes[1] = 0
            attributes[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            attributes[3] = 0
            attributes[4] = termios.B9600
            attributes[5] = termios.B9600
            attributes[6][termios.VMIN] = 0
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
        except Exception:
            os.close(fd)
            raise

        self._fd = fd

    def close(self) -> None:
        if self._fd is not None:
            fd = self._fd
            self._fd = None
            os.close(fd)

    def _require_fd(self) -> int:
        if self._fd is None:
            raise SerialLinkError("serial port is not open")
        return self._fd

    def write(self, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise SerialLinkError("serial write data must be bytes")
        if not data:
            return

        fd = self._require_fd()
        written = os.write(fd, data)
        if written != len(data):
            raise SerialLinkError(
                f"partial serial write: wrote {written} of {len(data)} bytes"
            )
        termios.tcdrain(fd)

    def read_exact(self, size: int, timeout_s: float) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative")
        if timeout_s < 0.0:
            raise ValueError("timeout_s must be non-negative")
        if size == 0:
            return b""

        fd = self._require_fd()
        deadline = time.monotonic() + timeout_s
        received = bytearray()

        while len(received) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise SerialTimeoutError(
                    f"timed out waiting for {size} bytes "
                    f"(received {len(received)})"
                )

            readable, _, _ = select.select([fd], [], [], remaining)
            if not readable:
                raise SerialTimeoutError(
                    f"timed out waiting for {size} bytes "
                    f"(received {len(received)})"
                )

            try:
                chunk = os.read(fd, size - len(received))
            except BlockingIOError:
                continue

            if chunk:
                received.extend(chunk)

        return bytes(received)

    def recover_rx_after_timeout(self) -> None:
        """Discard a late response tail without closing or reopening the port."""
        fd = self._require_fd()
        time.sleep(RX_TIMEOUT_RECOVERY_SETTLE_SECONDS)
        termios.tcflush(fd, termios.TCIFLUSH)

    def __enter__(self) -> "SerialLink":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()
