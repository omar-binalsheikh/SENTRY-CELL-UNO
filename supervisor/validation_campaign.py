import hashlib
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

if __package__:
    from .protocol import (
        CpuLoadStatus,
        JitterStatus,
        OverrunStatus,
        RuntimeMemoryStatus,
        TimingStatus,
        calculate_scheduled_task_utilization,
        ticks_to_microseconds,
    )
else:
    from protocol import (
        CpuLoadStatus,
        JitterStatus,
        OverrunStatus,
        RuntimeMemoryStatus,
        TimingStatus,
        calculate_scheduled_task_utilization,
        ticks_to_microseconds,
    )


@dataclass(frozen=True)
class BuildEvidence:
    elf_sha256: str
    hex_sha256: str
    map_sha256: str
    text_bytes: int
    data_bytes: int
    bss_bytes: int
    dec_bytes: int
    flash_bytes: int
    static_sram_bytes: int


class ValidationCampaignError(ValueError):
    """Raised when validation-campaign evidence cannot be produced safely."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _parse_avr_size(output: str) -> tuple[int, int, int, int]:
    rows = [line.split() for line in output.splitlines() if line.strip()]

    for index, row in enumerate(rows):
        if row[:4] != ["text", "data", "bss", "dec"]:
            continue
        if index + 1 >= len(rows) or len(rows[index + 1]) < 4:
            break

        values = rows[index + 1]
        try:
            text_bytes = int(values[0], 10)
            data_bytes = int(values[1], 10)
            bss_bytes = int(values[2], 10)
            dec_bytes = int(values[3], 10)
        except ValueError as error:
            raise ValidationCampaignError(
                "avr-size returned non-decimal size fields"
            ) from error

        if dec_bytes != (text_bytes + data_bytes + bss_bytes):
            raise ValidationCampaignError(
                "avr-size dec field does not equal text + data + bss"
            )

        return text_bytes, data_bytes, bss_bytes, dec_bytes

    raise ValidationCampaignError("unable to parse avr-size output")


def collect_build_evidence(
    repository_root: Optional[Path] = None,
    avr_size_command: str = "avr-size",
) -> BuildEvidence:
    root = repository_root or _repository_root()
    elf_path = root / "build" / "sentry-cell-uno.elf"
    hex_path = root / "build" / "sentry-cell-uno.hex"
    map_path = root / "build" / "sentry-cell-uno.map"

    for artifact_path in (elf_path, hex_path, map_path):
        if not artifact_path.is_file():
            raise ValidationCampaignError(
                f"required build artifact is missing: {artifact_path}"
            )

    try:
        completed = subprocess.run(
            (avr_size_command, str(elf_path)),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ValidationCampaignError(
            f"unable to execute {avr_size_command}: {error}"
        ) from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "no diagnostic output"
        raise ValidationCampaignError(
            f"{avr_size_command} failed: {detail}"
        )

    text_bytes, data_bytes, bss_bytes, dec_bytes = _parse_avr_size(
        completed.stdout
    )

    return BuildEvidence(
        elf_sha256=_sha256_file(elf_path),
        hex_sha256=_sha256_file(hex_path),
        map_sha256=_sha256_file(map_path),
        text_bytes=text_bytes,
        data_bytes=data_bytes,
        bss_bytes=bss_bytes,
        dec_bytes=dec_bytes,
        flash_bytes=text_bytes + data_bytes,
        static_sram_bytes=data_bytes + bss_bytes,
    )


def measurement_report_path(
    timestamp: datetime,
    repository_root: Optional[Path] = None,
) -> Path:
    root = repository_root or _repository_root()
    measurements = root / "measurements"
    stem = f"val_req_027_campaign_{timestamp.strftime('%Y-%m-%d_%H%M%S')}"

    for collision_index in range(10000):
        suffix = "" if collision_index == 0 else f"_{collision_index:02d}"
        candidate = measurements / f"{stem}{suffix}.txt"
        if not candidate.exists():
            return candidate

    raise ValidationCampaignError(
        f"unable to select a unique measurement report path in: {measurements}"
    )


def format_validation_report(
    timestamp: datetime,
    build: BuildEvidence,
    timing: TimingStatus,
    jitter: JitterStatus,
    runtime_memory: RuntimeMemoryStatus,
    cpu_load: CpuLoadStatus,
    overruns: OverrunStatus,
) -> str:
    utilization = calculate_scheduled_task_utilization(
        cpu_load.busy_ticks,
        cpu_load.elapsed_ms,
    )

    return "\n".join(
        (
            "Final validation measurement campaign",
            "",
            f"Host date/time: {timestamp.astimezone().isoformat()}",
            "",
            "Build evidence:",
            f"ELF SHA-256: {build.elf_sha256}",
            f"HEX SHA-256: {build.hex_sha256}",
            f"Map SHA-256: {build.map_sha256}",
            f"avr-size text: {build.text_bytes} bytes",
            f"avr-size data: {build.data_bytes} bytes",
            f"avr-size bss: {build.bss_bytes} bytes",
            f"avr-size dec: {build.dec_bytes} bytes",
            f"Flash bytes: {build.flash_bytes}",
            f"Static SRAM bytes: {build.static_sram_bytes}",
            "",
            "Scenario:",
            "IDLE       : 5 s",
            "ACTIVE     : 10 s",
            "SAFE_STATE : 5 s",
            "Host-timed instructions only; FSM states are not automatically "
            "detected.",
            "",
            "observed execution-time maxima:",
            f"Actuator: {timing.actuator_ticks} ticks = "
            f"{ticks_to_microseconds(timing.actuator_ticks):g} us",
            f"Control: {timing.control_ticks} ticks = "
            f"{ticks_to_microseconds(timing.control_ticks):g} us",
            f"Sensor/Safety: {timing.sensor_safety_ticks} ticks = "
            f"{ticks_to_microseconds(timing.sensor_safety_ticks):g} us",
            f"Communication: {timing.communication_ticks} ticks = "
            f"{ticks_to_microseconds(timing.communication_ticks):g} us",
            "",
            "observed maximum jitter at 1 ms measurement resolution:",
            f"Actuator: {jitter.actuator_ms} ms",
            f"Control: {jitter.control_ms} ms",
            f"Sensor/Safety: {jitter.sensor_safety_ms} ms",
            f"Communication: {jitter.communication_ms} ms",
            "",
            "observed minimum free SRAM watermark:",
            f"Painted region: {runtime_memory.painted_bytes} bytes",
            f"Used painted: {runtime_memory.used_painted_bytes} bytes",
            f"Minimum free observed: {runtime_memory.min_free_bytes} bytes",
            "",
            "observed scheduled-task CPU utilization:",
            f"Busy ticks: {cpu_load.busy_ticks}",
            f"Elapsed firmware time: {cpu_load.elapsed_ms} ms",
            f"Utilization: {utilization:.1f} %",
            "Scheduled-task CPU utilization excludes ISR and scheduler "
            "overhead.",
            "",
            "observed execution overruns:",
            f"Actuator: {overruns.actuator}",
            f"Control: {overruns.control}",
            f"Sensor/Safety: {overruns.sensor_safety}",
            f"Communication: {overruns.communication}",
            "",
        )
    )


def write_measurement_report(path: Path, report: str) -> None:
    if not path.parent.is_dir():
        raise ValidationCampaignError(
            f"measurement directory is missing: {path.parent}"
        )

    try:
        with path.open("x", encoding="utf-8") as report_file:
            report_file.write(report)
    except FileExistsError as error:
        raise ValidationCampaignError(
            f"measurement report already exists and was not overwritten: {path}"
        ) from error
    except OSError as error:
        raise ValidationCampaignError(
            f"unable to create measurement report {path}: {error}"
        ) from error
