import csv
import tempfile
import unittest
from pathlib import Path

from supervisor.fault_injection import (
    CSV_COLUMNS,
    FaultInjectionCsvLogger,
    SaturatedCounterError,
    build_fault_result,
    require_counter_increment_capacity,
)


class FaultInjectionResultTests(unittest.TestCase):
    def test_passes_when_counter_increases_and_recovery_succeeds(self) -> None:
        result = build_fault_result(
            "FI-COM-001", "crc_errors", 3, 4, True
        )

        self.assertTrue(result.counter_incremented)
        self.assertTrue(result.passed)

    def test_fails_when_counter_does_not_increase(self) -> None:
        result = build_fault_result(
            "FI-COM-001", "crc_errors", 3, 3, True
        )

        self.assertFalse(result.counter_incremented)
        self.assertFalse(result.passed)

    def test_fails_when_recovery_ping_fails(self) -> None:
        result = build_fault_result(
            "FI-COM-002", "parser_timeouts", 8, 9, False
        )

        self.assertTrue(result.counter_incremented)
        self.assertFalse(result.passed)

    def test_detects_saturated_counter(self) -> None:
        require_counter_increment_capacity("CRC errors", 254)

        with self.assertRaises(SaturatedCounterError):
            require_counter_increment_capacity("CRC errors", 255)


class FaultInjectionCsvTests(unittest.TestCase):
    def _read_written_rows(self):
        first = build_fault_result(
            "FI-COM-001", "crc_errors", 10, 11, True
        )
        second = build_fault_result(
            "FI-COM-002", "parser_timeouts", 20, 20, False
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = (
                Path(temporary_directory) / "nested" / "faults.csv"
            )
            with FaultInjectionCsvLogger(str(csv_path)) as csv_logger:
                csv_logger.write("2026-08-25T12:00:00+02:00", first)
                csv_logger.write("2026-08-25T12:00:01+02:00", second)

            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                return list(csv.reader(csv_file))

    def test_csv_header_is_exact(self) -> None:
        rows = self._read_written_rows()

        self.assertEqual(rows[0], list(CSV_COLUMNS))

    def test_csv_contains_two_results(self) -> None:
        rows = self._read_written_rows()

        self.assertEqual(len(rows) - 1, 2)

    def test_csv_preserves_all_values_exactly(self) -> None:
        rows = self._read_written_rows()

        self.assertEqual(
            rows[1],
            [
                "2026-08-25T12:00:00+02:00",
                "FI-COM-001",
                "crc_errors",
                "10",
                "11",
                "true",
                "true",
                "PASS",
            ],
        )
        self.assertEqual(
            rows[2],
            [
                "2026-08-25T12:00:01+02:00",
                "FI-COM-002",
                "parser_timeouts",
                "20",
                "20",
                "false",
                "false",
                "FAIL",
            ],
        )


if __name__ == "__main__":
    unittest.main()
