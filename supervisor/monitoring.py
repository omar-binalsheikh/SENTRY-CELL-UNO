import csv
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Optional, TextIO, Type


CSV_COLUMNS = (
    "timestamp",
    "sequence",
    "uart_rx_overflow",
    "parser_timeouts",
    "crc_errors",
)


@dataclass(frozen=True)
class CommHealthSample:
    timestamp: str
    sequence: int
    uart_rx_overflow: int
    parser_timeouts: int
    crc_errors: int


def validate_monitor_options(samples: int, interval_s: float) -> None:
    if samples <= 0:
        raise ValueError("--samples must be greater than zero")
    if interval_s <= 0.0:
        raise ValueError("--interval must be greater than zero")


def next_sequence(sequence: int) -> int:
    if not 0 <= sequence <= 0xFF:
        raise ValueError("sequence must be in range 0..255")
    return (sequence + 1) & 0xFF


class CsvLogger:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.DictWriter] = None

    def open(self) -> None:
        if self._file is not None:
            raise RuntimeError("CSV logger is already open")

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

    def write(self, sample: CommHealthSample) -> None:
        if self._writer is None or self._file is None:
            raise RuntimeError("CSV logger is not open")

        self._writer.writerow(
            {
                "timestamp": sample.timestamp,
                "sequence": sample.sequence,
                "uart_rx_overflow": sample.uart_rx_overflow,
                "parser_timeouts": sample.parser_timeouts,
                "crc_errors": sample.crc_errors,
            }
        )
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            file_handle = self._file
            self._file = None
            self._writer = None
            file_handle.close()

    def __enter__(self) -> "CsvLogger":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()
