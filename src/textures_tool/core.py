from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image


DEFAULT_CONFIG = {
    "mode": "pad",
    "rounding": "up",
    "background": [0, 0, 0, 0],
    "resample": "lanczos",
    "anchor": "center",
    "limit_smaller": False,
    "only_shrink": False,
    "overwrite": False,
    "suffix": "_pot",
    "output_dir": "",
    "file_types": [".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"],
}

RESAMPLE_MAP = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


@dataclass
class ProcessResult:
    source: Path
    target: Path
    original_size: tuple[int, int]
    final_size: tuple[int, int]
    action: str


@dataclass
class ProcessFailure:
    source: Path
    error: str


def next_power_of_two(value: int, rounding: str) -> int:
    if value <= 1:
        return 1

    lower = 1 << (value.bit_length() - 1)
    upper = 1 << value.bit_length() if value != lower else lower

    if rounding == "up":
        return upper
    if rounding == "down":
        return lower
    if rounding == "nearest":
        return lower if (value - lower) <= (upper - value) else upper
    raise ValueError(f"Unsupported rounding mode: {rounding}")


def compute_target_size(width: int, height: int, config: dict) -> tuple[int, int]:
    target_width = next_power_of_two(width, config["rounding"])
    target_height = next_power_of_two(height, config["rounding"])

    if config["mode"] == "pad" or config["limit_smaller"]:
        target_width = max(target_width, width)
        target_height = max(target_height, height)

    if config["only_shrink"]:
        target_width = min(target_width, width)
        target_height = min(target_height, height)

    return target_width, target_height


def compute_anchor_offset(
    canvas_size: tuple[int, int], content_size: tuple[int, int], anchor: str
) -> tuple[int, int]:
    canvas_width, canvas_height = canvas_size
    content_width, content_height = content_size

    horizontal = {
        "left": 0,
        "center": (canvas_width - content_width) // 2,
        "right": canvas_width - content_width,
    }
    vertical = {
        "top": 0,
        "center": (canvas_height - content_height) // 2,
        "bottom": canvas_height - content_height,
    }

    normalized = anchor.lower()
    if normalized == "center":
        return horizontal["center"], vertical["center"]
    if normalized == "top_left":
        return horizontal["left"], vertical["top"]
    if normalized == "top":
        return horizontal["center"], vertical["top"]
    if normalized == "top_right":
        return horizontal["right"], vertical["top"]
    if normalized == "left":
        return horizontal["left"], vertical["center"]
    if normalized == "right":
        return horizontal["right"], vertical["center"]
    if normalized == "bottom_left":
        return horizontal["left"], vertical["bottom"]
    if normalized == "bottom":
        return horizontal["center"], vertical["bottom"]
    if normalized == "bottom_right":
        return horizontal["right"], vertical["bottom"]
    raise ValueError(f"Unsupported anchor: {anchor}")


def load_config(config_path: Path | None) -> dict:
    config = dict(DEFAULT_CONFIG)
    if config_path:
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        config.update(loaded)
    return config


def is_supported_image(path: Path, file_types: Iterable[str]) -> bool:
    allowed = {extension.lower() for extension in file_types}
    return path.is_file() and path.suffix.lower() in allowed


def should_ignore_path(path: Path, file_types: Iterable[str]) -> bool:
    if not path.is_file():
        return False

    if path.suffix.lower() == ".meta":
        return True

    return not is_supported_image(path, file_types)


def gather_images(inputs: Iterable[str], file_types: Iterable[str]) -> list[Path]:
    files: list[Path] = []

    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if is_supported_image(path, file_types):
            files.append(path)
        elif path.is_dir():
            files.extend(
                candidate
                for candidate in path.rglob("*")
                if not should_ignore_path(candidate, file_types)
            )

    return sorted(set(files))


def should_skip_file(source: Path, config: dict) -> bool:
    return bool(config["suffix"]) and source.stem.endswith(config["suffix"])


def build_output_path(source: Path, config: dict) -> Path:
    if config["overwrite"]:
        return source

    output_dir = Path(config["output_dir"]).expanduser() if config["output_dir"] else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{source.stem}{config['suffix']}{source.suffix}"


def convert_image_mode(image: Image.Image, background: list[int]) -> tuple[Image.Image, tuple[int, ...] | int]:
    if image.mode in ("RGBA", "LA"):
        return image.convert("RGBA"), tuple(background[:4])
    if image.mode == "P":
        return image.convert("RGBA"), tuple(background[:4])
    if image.mode in ("RGB", "CMYK"):
        return image.convert("RGB"), tuple(background[:3])
    return image.convert("RGBA"), tuple(background[:4])


def resize_with_padding(image: Image.Image, target_size: tuple[int, int], config: dict) -> Image.Image:
    prepared, bg_color = convert_image_mode(image, config["background"])
    canvas = Image.new(prepared.mode, target_size, bg_color)
    offset = compute_anchor_offset(target_size, prepared.size, config["anchor"])
    canvas.paste(prepared, offset, prepared if prepared.mode == "RGBA" else None)
    return canvas


def resize_with_scale(image: Image.Image, target_size: tuple[int, int], config: dict) -> Image.Image:
    prepared, _ = convert_image_mode(image, config["background"])
    return prepared.resize(target_size, RESAMPLE_MAP[config["resample"]])


def process_image(source: Path, config: dict) -> ProcessResult:
    with Image.open(source) as image:
        original_size = image.size
        target_size = compute_target_size(*original_size, config)

        if config["mode"] == "pad":
            if target_size == original_size:
                result = image.copy()
                action = "copied"
            else:
                result = resize_with_padding(image, target_size, config)
                action = "padded"
        elif config["mode"] == "scale":
            if target_size == original_size:
                result = image.copy()
                action = "copied"
            else:
                result = resize_with_scale(image, target_size, config)
                action = "scaled"
        else:
            raise ValueError(f"Unsupported mode: {config['mode']}")

        target_path = build_output_path(source, config)
        save_kwargs = {}
        if target_path.suffix.lower() in {".jpg", ".jpeg"} and result.mode == "RGBA":
            result = result.convert("RGB")
        if target_path.suffix.lower() == ".png":
            save_kwargs["compress_level"] = 2

        result.save(target_path, **save_kwargs)

    return ProcessResult(
        source=source,
        target=target_path,
        original_size=original_size,
        final_size=target_size,
        action=action,
    )


def process_batch(
    inputs: list[str],
    config: dict,
    output_dir: str | None = None,
    progress_callback: Callable[[str, object], None] | None = None,
) -> tuple[list[ProcessResult], list[ProcessFailure]]:
    runtime_config = dict(DEFAULT_CONFIG)
    runtime_config.update(config)

    if output_dir is not None:
        runtime_config["output_dir"] = output_dir

    files = gather_images(inputs, runtime_config["file_types"])
    if not files:
        raise ValueError("No supported images found.")

    results: list[ProcessResult] = []
    failures: list[ProcessFailure] = []

    for index, file_path in enumerate(files, start=1):
        if progress_callback:
            progress_callback("scan", {"index": index, "total": len(files), "path": file_path})

        if should_skip_file(file_path, runtime_config) and not runtime_config["overwrite"]:
            if progress_callback:
                progress_callback("skipped", {"index": index, "total": len(files), "path": file_path})
            continue

        try:
            result = process_image(file_path, runtime_config)
            results.append(result)
            if progress_callback:
                progress_callback("processed", result)
        except Exception as exc:  # noqa: BLE001
            failure = ProcessFailure(source=file_path, error=str(exc))
            failures.append(failure)
            if progress_callback:
                progress_callback("failed", failure)

    return results, failures


def print_summary(results: list[ProcessResult]) -> None:
    print("")
    print("Processed files:")
    for item in results:
        print(
            f"- {item.source.name}: {item.original_size[0]}x{item.original_size[1]} "
            f"-> {item.final_size[0]}x{item.final_size[1]} [{item.action}]"
        )
        print(f"  Output: {item.target}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch convert images to power-of-two dimensions for UI and texture workflows."
    )
    parser.add_argument("inputs", nargs="+", help="One or more files or directories. Directories are scanned recursively.")
    parser.add_argument("--config", type=Path, default=None, help="Path to a JSON config file. See config/config.example.json.")
    parser.add_argument("--mode", choices=["pad", "scale"], help="Override processing mode. pad keeps content size and pads canvas. scale resizes content.")
    parser.add_argument("--rounding", choices=["nearest", "up", "down"], help="Override power-of-two rounding rule.")
    parser.add_argument("--output-dir", type=str, help="Write processed files into this directory instead of next to the originals.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite source files.")
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    config = load_config(args.config)

    if args.mode:
        config["mode"] = args.mode
    if args.rounding:
        config["rounding"] = args.rounding
    if args.output_dir:
        config["output_dir"] = args.output_dir
    if args.overwrite:
        config["overwrite"] = True

    try:
        results, failures = process_batch(args.inputs, config)
    except ValueError as exc:
        print(str(exc))
        return 1

    for failure in failures:
        print(f"Failed: {failure.source} -> {failure.error}")

    files = gather_images(args.inputs, config["file_types"])
    for file_path in files:
        if should_skip_file(file_path, config) and not config["overwrite"]:
            print(f"Skipped generated file: {file_path}")

    if not results:
        print("No images were processed successfully.")
        return 1

    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
