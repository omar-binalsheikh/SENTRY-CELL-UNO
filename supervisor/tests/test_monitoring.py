import csv
import tempfile
import unittest
from pathlib import Path

from supervisor.monitoring import (
    CSV_COLUMNS,
    CommHealthSample,
    CsvLogger,
    next_sequence,
    validate_monitor_options,
)


class MonitorOptionTests(unittest.TestCase):
    def test_samples_must_be_positive(self) -> None:
        for samples in (0, -1):
            with self.subTest(samples=samples):
                with self.assertRaises(ValueError):
                    validate_monitor_options(samples, 0.5)

    def test_interval_must_be_positive(self) -> None:
        for interval_s in (0.0, -0.5):
            with self.subTest(interval_s=interval_s):
                with self.assertRaises(ValueError):
                    validate_monitor_options(5, interval_s)

    def test_sequence_increment_and_wrap(self) -> None:
        self.assertEqual(next_sequence(0x40), 0x41)
        self.assertEqual(next_sequence(0xFF), 0x00)


class CsvLoggerTests(unittest.TestCase):
    def test_creation_header_and_exact_multiple_samples(self) -> None:
        expected_samples = (
            CommHealthSample(
                timestamp="2026-08-25T12:00:00+02:00",
                sequence=0x40,
                uart_rx_overflow=1,
                parser_timeouts=2,
                crc_errors=3,
            ),
            CommHealthSample(
                timestamp="2026-08-25T12:00:00.500000+02:00",
                sequence=0x41,
                uart_rx_overflow=4,
                parser_timeouts=5,
                crc_errors=6,
            ),
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "nested" / "comm_health.csv"

            with CsvLogger(str(csv_path)) as csv_logger:
                for sample in expected_samples:
                    csv_logger.write(sample)

            self.assertTrue(csv_path.is_file())

            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.reader(csv_file))

            self.assertEqual(rows[0], list(CSV_COLUMNS))
            self.assertEqual(len(rows), 3)
            self.assertEqual(
                rows[1],
                ["2026-08-25T12:00:00+02:00", "64", "1", "2", "3"],
            )
            self.assertEqual(
                rows[2],
                [
                    "2026-08-25T12:00:00.500000+02:00",
                    "65",
                    "4",
                    "5",
                    "6",
                ],
            )


if __name__ == "__main__":
    unittest.main()
