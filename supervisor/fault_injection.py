import csv
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Optional, TextIO, Type


CSV_COLUMNS = (
    "timestamp",
    "fault_id",
    "counter_name",
    "before",
    "after",
    "counter_incremented",
    "recovery_ping",
    "result",
)


class SaturatedCounterError(ValueError):
    """Raised when a saturated uint8 counter cannot prove an increment."""


@dataclass(frozen=True)
class FaultInjectionResult:
    fault_id: str
    counter_name: str
    before: int
    after: int
    counter_incremented: bool
    recovery_ping: bool

    @property
    def passed(self) -> bool:
        return self.counter_incremented and self.recovery_ping


def require_counter_increment_capacity(counter_name: str, before: int) -> None:
    if before == 0xFF:
        raise SaturatedCounterError(
            f"{counter_name} counter is saturated at 255; "
            "an increment cannot be demonstrated"
        )


def build_fault_result(
    fault_id: str,
    counter_name: str,
    before: int,
    after: int,
    recovery_ping: bool,
) -> FaultInjectionResult:
    return FaultInjectionResult(
        fault_id=fault_id,
        counter_name=counter_name,
        before=before,
        after=after,
        counter_incremented=after > before,
        recovery_ping=recovery_ping,
    )


class FaultInjectionCsvLogger:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.DictWriter] = None

    def open(self) -> None:
        if self._file is not None:
            raise RuntimeError("fault-injection CSV logger is already open")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file = self.path.open("w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(
                self._file,
                fieldnames=CSV_COLUMNS,
                lineterminator="\n",
            )
            self._writer.writeheader()
            self._file.flush()
        except Exception:
            self.close()
            raise

    def write(self, timestamp: str, result: FaultInjectionResult) -> None:
        if self._writer is None or self._file is None:
            raise RuntimeError("fault-injection CSV logger is not open")

        self._writer.writerow(
            {
                "timestamp": timestamp,
                "fault_id": result.fault_id,
                "counter_name": result.counter_name,
                "before": result.before,
                "after": result.after,
                "counter_incremented": str(result.counter_incremented).lower(),
                "recovery_ping": str(result.recovery_ping).lower(),
                "result": "PASS" if result.passed else "FAIL",
            }
        )
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            file_handle = self._file
            self._file = None
            self._writer = None
            file_handle.close()

    def __enter__(self) -> "FaultInjectionCsvLogger":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()
