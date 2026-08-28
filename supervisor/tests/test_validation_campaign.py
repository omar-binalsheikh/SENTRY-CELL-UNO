import hashlib
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from supervisor import main as supervisor_main
from supervisor.protocol import (
    TYPE_CPU_LOAD_STATUS,
    TYPE_GET_CPU_LOAD_STATUS,
    TYPE_GET_JITTER_STATUS,
    TYPE_GET_OVERRUN_STATUS,
    TYPE_GET_RUNTIME_MEMORY_STATUS,
    TYPE_GET_TIMING_STATUS,
    TYPE_JITTER_STATUS,
    TYPE_OVERRUN_STATUS,
    TYPE_RUNTIME_MEMORY_STATUS,
    TYPE_TIMING_STATUS,
    CpuLoadStatus,
    Frame,
    JitterStatus,
    OverrunStatus,
    RuntimeMemoryStatus,
    TimingStatus,
    decode_frame,
)
from supervisor.validation_campaign import (
    BuildEvidence,
    ValidationCampaignError,
    collect_build_evidence,
    format_validation_report,
    measurement_report_path,
    write_measurement_report,
)


def _u16_payload(*values: int) -> bytes:
    return b"".join(value.to_bytes(2, "little") for value in values)


def _u32_payload(*values: int) -> bytes:
    return b"".join(value.to_bytes(4, "little") for value in values)


def _build_evidence() -> BuildEvidence:
    return BuildEvidence(
        elf_sha256="11" * 32,
        hex_sha256="22" * 32,
        map_sha256="33" * 32,
        text_bytes=6886,
        data_bytes=10,
        bss_bytes=280,
        dec_bytes=7176,
        flash_bytes=6896,
        static_sram_bytes=290,
    )


class BuildEvidenceTests(unittest.TestCase):
    def test_hashes_are_calculated_from_actual_artifact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            build = root / "build"
            build.mkdir()
            artifact_data = {
                "sentry-cell-uno.elf": b"test elf bytes",
                "sentry-cell-uno.hex": b":0100000000FF\n",
                "sentry-cell-uno.map": b"test map bytes",
            }
            for name, data in artifact_data.items():
                (build / name).write_bytes(data)

            avr_size_result = subprocess.CompletedProcess(
                args=("avr-size", str(build / "sentry-cell-uno.elf")),
                returncode=0,
                stdout=(
                    "   text\t   data\t    bss\t    dec\t    hex\tfilename\n"
                    "   6886\t     10\t    280\t   7176\t   1c08\ttest.elf\n"
                ),
                stderr="",
            )

            with mock.patch(
                "supervisor.validation_campaign.subprocess.run",
                return_value=avr_size_result,
            ):
                evidence = collect_build_evidence(root)

            self.assertEqual(
                evidence.elf_sha256,
                hashlib.sha256(artifact_data["sentry-cell-uno.elf"])
                .hexdigest(),
            )
            self.assertEqual(
                evidence.hex_sha256,
                hashlib.sha256(artifact_data["sentry-cell-uno.hex"])
                .hexdigest(),
            )
            self.assertEqual(
                evidence.map_sha256,
                hashlib.sha256(artifact_data["sentry-cell-uno.map"])
                .hexdigest(),
            )
            self.assertEqual(evidence.flash_bytes, 6896)
            self.assertEqual(evidence.static_sram_bytes, 290)

    def test_missing_build_artifact_fails_before_avr_size(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            build = root / "build"
            build.mkdir()
            (build / "sentry-cell-uno.elf").write_bytes(b"elf")
            (build / "sentry-cell-uno.hex").write_bytes(b"hex")

            with mock.patch(
                "supervisor.validation_campaign.subprocess.run"
            ) as run:
                with self.assertRaisesRegex(
                    ValidationCampaignError,
                    "required build artifact is missing",
                ):
                    collect_build_evidence(root)

            run.assert_not_called()


class ValidationReportTests(unittest.TestCase):
    def test_report_contains_required_observational_wording(self) -> None:
        report = format_validation_report(
            datetime(2026, 8, 27, 20, 30, tzinfo=timezone.utc),
            _build_evidence(),
            TimingStatus(15, 20, 441, 302),
            JitterStatus(0, 1, 2, 3),
            RuntimeMemoryStatus(1722, 1750, 28),
            CpuLoadStatus(640000, 20000),
            OverrunStatus(0, 0, 1, 0),
        )

        required_phrases = (
            "Final validation measurement campaign",
            "observed execution-time maxima",
            "observed maximum jitter at 1 ms measurement resolution",
            "observed minimum free SRAM watermark",
            "observed scheduled-task CPU utilization",
            "observed execution overruns",
            "Scheduled-task CPU utilization excludes ISR and scheduler "
            "overhead.",
            "Host-timed instructions only; FSM states are not automatically "
            "detected.",
            "ELF SHA-256: " + ("11" * 32),
            "Flash bytes: 6896",
            "Static SRAM bytes: 290",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, report)

        forbidden_phrases = (
            "guaranteed WCET",
            "zero physical jitter",
            "total MCU CPU load",
            "guaranteed minimum free SRAM",
        )
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, report)


class EvidencePathTests(unittest.TestCase):
    timestamp = datetime(2026, 8, 28, 22, 15, 30, tzinfo=timezone.utc)

    @staticmethod
    def _root(temporary_directory: str) -> Path:
        root = Path(temporary_directory)
        (root / "measurements").mkdir()
        return root

    def test_fresh_path_uses_timestamped_campaign_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)

            path = measurement_report_path(self.timestamp, root)

            self.assertEqual(
                path.name,
                "val_req_027_campaign_2026-08-28_221530.txt",
            )

    def test_current_build_index_is_never_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)

            path = measurement_report_path(self.timestamp, root)

            self.assertNotEqual(path.name, "val_req_027_current_build.txt")

    def test_canonical_campaign_name_is_not_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)
            canonical = (
                root
                / "measurements"
                / "val_req_027_campaign_2026-08-27_202840.txt"
            )
            canonical.write_text("canonical evidence", encoding="utf-8")
            timestamp = datetime(
                2026,
                8,
                27,
                20,
                28,
                40,
                tzinfo=timezone.utc,
            )

            path = measurement_report_path(timestamp, root)

            self.assertEqual(
                path.name,
                "val_req_027_campaign_2026-08-27_202840_01.txt",
            )
            self.assertEqual(
                canonical.read_text(encoding="utf-8"),
                "canonical evidence",
            )

    def test_existing_campaign_selects_unique_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)
            existing = (
                root
                / "measurements"
                / "val_req_027_campaign_2026-08-28_221530.txt"
            )
            existing.write_text("existing evidence", encoding="utf-8")

            path = measurement_report_path(self.timestamp, root)

            self.assertEqual(
                path.name,
                "val_req_027_campaign_2026-08-28_221530_01.txt",
            )
            self.assertEqual(
                existing.read_text(encoding="utf-8"),
                "existing evidence",
            )

    def test_collision_suffixes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)
            measurements = root / "measurements"
            (measurements / "val_req_027_campaign_2026-08-28_221530.txt").touch()
            (measurements / "val_req_027_campaign_2026-08-28_221530_01.txt").touch()

            path = measurement_report_path(self.timestamp, root)

            self.assertEqual(
                path.name,
                "val_req_027_campaign_2026-08-28_221530_02.txt",
            )

    def test_exclusive_write_refuses_to_overwrite_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)
            existing = root / "measurements" / "existing.txt"
            existing.write_text("preserve me", encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationCampaignError,
                "already exists and was not overwritten",
            ):
                write_measurement_report(existing, "replacement")

            self.assertEqual(
                existing.read_text(encoding="utf-8"),
                "preserve me",
            )

    def test_new_report_preserves_index_and_canonical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self._root(temporary_directory)
            measurements = root / "measurements"
            index = measurements / "val_req_027_current_build.txt"
            canonical = (
                measurements
                / "val_req_027_campaign_2026-08-27_202840.txt"
            )
            index.write_text("traceability index", encoding="utf-8")
            canonical.write_text("canonical campaign", encoding="utf-8")

            path = measurement_report_path(self.timestamp, root)
            write_measurement_report(path, "new campaign")

            self.assertEqual(
                index.read_text(encoding="utf-8"),
                "traceability index",
            )
            self.assertEqual(
                canonical.read_text(encoding="utf-8"),
                "canonical campaign",
            )
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "new campaign",
            )


class SingleSessionCampaignTests(unittest.TestCase):
    class FakeSerialLink:
        instances = []

        def __init__(self, port: str) -> None:
            self.port = port
            self.enter_count = 0
            self.exit_count = 0
            self.is_open = False
            self.writes = []
            self.__class__.instances.append(self)

        def __enter__(self):
            self.enter_count += 1
            self.is_open = True
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            self.exit_count += 1
            self.is_open = False

        def write(self, data: bytes) -> None:
            if not self.is_open:
                raise AssertionError("request sent outside the serial session")
            self.writes.append(data)

    def setUp(self) -> None:
        self.FakeSerialLink.instances = []

    def test_campaign_uses_one_connection_for_all_five_queries(self) -> None:
        responses = (
            Frame(TYPE_TIMING_STATUS, 0x80, _u16_payload(15, 20, 441, 302)),
            Frame(TYPE_JITTER_STATUS, 0x81, _u16_payload(0, 1, 2, 3)),
            Frame(
                TYPE_RUNTIME_MEMORY_STATUS,
                0x82,
                _u16_payload(1722, 1750, 28),
            ),
            Frame(TYPE_CPU_LOAD_STATUS, 0x83, _u32_payload(640000, 20000)),
            Frame(TYPE_OVERRUN_STATUS, 0x84, _u16_payload(0, 0, 1, 0)),
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "measurements" / "report.txt"
            report_path.parent.mkdir()

            output = io.StringIO()

            with (
                mock.patch.object(
                    supervisor_main,
                    "SerialLink",
                    self.FakeSerialLink,
                ),
                mock.patch.object(
                    supervisor_main,
                    "collect_build_evidence",
                    return_value=_build_evidence(),
                ),
                mock.patch.object(
                    supervisor_main,
                    "read_protocol_frame",
                    side_effect=responses,
                ),
                mock.patch.object(supervisor_main.time, "sleep") as sleep,
                mock.patch.object(
                    supervisor_main,
                    "measurement_report_path",
                    return_value=report_path,
                ),
                redirect_stdout(output),
            ):
                supervisor_main.run_validation_profile("/dev/cu.test")

            self.assertEqual(len(self.FakeSerialLink.instances), 1)
            link = self.FakeSerialLink.instances[0]
            self.assertEqual(link.enter_count, 1)
            self.assertEqual(link.exit_count, 1)
            self.assertEqual(len(link.writes), 5)
            self.assertEqual(
                [decode_frame(data).frame_type for data in link.writes],
                [
                    TYPE_GET_TIMING_STATUS,
                    TYPE_GET_JITTER_STATUS,
                    TYPE_GET_RUNTIME_MEMORY_STATUS,
                    TYPE_GET_CPU_LOAD_STATUS,
                    TYPE_GET_OVERRUN_STATUS,
                ],
            )
            self.assertEqual(
                [decode_frame(data).sequence for data in link.writes],
                [0x80, 0x81, 0x82, 0x83, 0x84],
            )
            self.assertEqual(
                [call.args[0] for call in sleep.call_args_list],
                [2.2, 5.0, 10.0, 5.0],
            )
            self.assertTrue(report_path.is_file())
            self.assertIn(
                "observed execution-time maxima",
                report_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                f"Measurement report written: {report_path}",
                output.getvalue(),
            )

    def test_cli_exposes_validation_profile_mode(self) -> None:
        arguments = supervisor_main.parse_args(
            ("--port", "/dev/cu.test", "--validation-profile")
        )

        self.assertTrue(arguments.validation_profile)

    def test_missing_artifact_is_reported_without_opening_serial(self) -> None:
        error_output = io.StringIO()

        with (
            mock.patch.object(
                supervisor_main,
                "collect_build_evidence",
                side_effect=ValidationCampaignError(
                    "required build artifact is missing: test.elf"
                ),
            ),
            mock.patch.object(supervisor_main, "SerialLink") as serial_link,
            redirect_stderr(error_output),
        ):
            result = supervisor_main.main(
                ("--port", "/dev/cu.test", "--validation-profile")
            )

        self.assertEqual(result, 1)
        serial_link.assert_not_called()
        self.assertIn(
            "required build artifact is missing",
            error_output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
