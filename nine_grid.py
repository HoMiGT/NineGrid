#!/usr/bin/env python3
"""将 9 张图片合成为带间隙和外边框的 3x3 九宫格。"""

from __future__ import annotations

import argparse
import math
import re
import statistics
from pathlib import Path

from PIL import Image, ImageColor, ImageOps


def positive_or_zero(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("数值不能小于 0")
    return number


def parse_individual_crop(value: str) -> tuple[int, int, int]:
    """解析形如 2:30,10 的单图裁剪参数。"""
    try:
        index_text, coordinates = value.split(":", 1)
        x_text, y_text = coordinates.split(",", 1)
        index = int(index_text)
        x = int(x_text)
        y = int(y_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "格式应为 图片序号:X,Y，例如 2:30,10"
        ) from exc

    if not 1 <= index <= 9:
        raise argparse.ArgumentTypeError("图片序号必须在 1 到 9 之间")
    if x < 0 or y < 0:
        raise argparse.ArgumentTypeError("裁剪坐标不能小于 0")
    return index - 1, x, y


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "把 9 张图片合成为 3x3 九宫格。默认自动计算合适的正方形单格尺寸；"
            "尺寸不足的图片会先等比放大，再从每张图片各自的指定坐标开始裁剪。"
        )
    )
    parser.add_argument(
        "images",
        nargs="*",
        type=Path,
        help="按排列顺序提供 9 张图片；使用 --source 且目录内正好有 9 张时可省略",
    )
    parser.add_argument(
        "-s",
        "--source",
        type=Path,
        help="图片源目录；未提供图片名时，自动读取目录内的 9 张图片",
    )
    parser.add_argument("-o", "--output", type=Path, default=Path("nine_grid.jpg"), help="输出文件，默认 nine_grid.jpg")
    parser.add_argument(
        "-r",
        "--reference",
        default=None,
        metavar="序号或文件名",
        help=(
            "指定标准尺寸图片，可填写 1-9 的图片序号或文件名/路径；"
            "例如 -r 3 或 -r 3.jpg；省略时自动计算正方形尺寸"
        ),
    )
    parser.add_argument("--crop-x", type=positive_or_zero, default=0, help="裁剪起点 X，默认 0")
    parser.add_argument("--crop-y", type=positive_or_zero, default=0, help="裁剪起点 Y，默认 0")
    parser.add_argument(
        "--crop",
        action="append",
        type=parse_individual_crop,
        default=[],
        metavar="序号:X,Y",
        help=(
            "单独设置某张图片的裁剪起点，可重复使用；"
            "例如 --crop 2:30,10 --crop 5:0,80。未指定时使用全局起点"
        ),
    )
    parser.add_argument(
        "--gap",
        type=positive_or_zero,
        default=None,
        help="图片间隙像素；默认约为单格短边的 2.5%%",
    )
    parser.add_argument(
        "--border",
        type=positive_or_zero,
        default=None,
        help="大图外边框像素；默认约为单格短边的 6%%",
    )
    parser.add_argument("--background", default="#FFFFFF", help="间隙和边框颜色，默认 #FFFFFF")
    parser.add_argument("--quality", type=int, choices=range(1, 101), default=95, metavar="1-100", help="JPEG质量，默认95")
    return parser.parse_args()


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def natural_sort_key(path: Path) -> list[tuple[int, object]]:
    """让 2.jpg 排在 10.jpg 之前。"""
    return [
        (1, int(part)) if part.isdigit() else (0, part)
        for part in re.split(r"(\d+)", path.name.lower())
    ]


def resolve_images(images: list[Path], source: Path | None) -> list[Path]:
    """根据位置参数和源目录得到最终的 9 张图片路径。"""
    if source is not None:
        if not source.is_dir():
            raise NotADirectoryError(f"图片源目录不存在或不是目录：{source}")

        if images:
            resolved = [path if path.is_absolute() else source / path for path in images]
        else:
            resolved = sorted(
                (
                    path
                    for path in source.iterdir()
                    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
                ),
                key=natural_sort_key,
            )
    else:
        resolved = images

    if len(resolved) != 9:
        raise ValueError(
            f"必须提供或找到正好 9 张图片，当前数量：{len(resolved)}。"
            "如果源目录中图片较多，请在命令中明确写出需要的 9 个文件名。"
        )
    return resolved


def resolve_reference(reference: str, images: list[Path], source: Path | None) -> Path:
    """通过 1-9 序号或文件名/路径确定标准尺寸图片。"""
    if reference.isdigit():
        index = int(reference)
        if not 1 <= index <= 9:
            raise ValueError("标准图片序号必须在 1 到 9 之间")
        return images[index - 1]

    reference_path = Path(reference)
    if source is not None and not reference_path.is_absolute():
        reference_path = source / reference_path
    if not reference_path.is_file():
        raise FileNotFoundError(f"找不到标准尺寸图片：{reference_path}")
    return reference_path


def read_oriented_size(path: Path) -> tuple[int, int]:
    """读取应用 EXIF 方向校正后的图片尺寸。"""
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).size


def calculate_auto_square_size(images: list[Path]) -> tuple[int, int]:
    """以 9 张图片短边的中位数计算稳健、美观的正方形单格尺寸。"""
    short_sides = [min(read_oriented_size(path)) for path in images]
    side = max(1, round(statistics.median(short_sides)))
    return side, side


def open_normalized(path: Path, background: tuple[int, int, int]) -> Image.Image:
    """读取图片，应用 EXIF 方向校正，并将透明区域铺到背景色上。"""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode in ("RGBA", "LA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            base = Image.new("RGBA", rgba.size, (*background, 255))
            return Image.alpha_composite(base, rgba).convert("RGB")
        return image.convert("RGB")


def resize_then_crop(
    image: Image.Image,
    target_size: tuple[int, int],
    crop_x: int,
    crop_y: int,
) -> Image.Image:
    """仅在尺寸不足时等比放大，随后按给定起点裁剪到标准尺寸。"""
    """按裁剪范围需要等比放大，随后从给定起点裁剪到标准尺寸。"""
    target_w, target_h = target_size
    source_w, source_h = image.size

    if source_w < target_w or source_h < target_h:
        scale = max(target_w / source_w, target_h / source_h)
    # 裁剪起点不为 (0, 0) 时，图片不仅要覆盖标准尺寸，还必须为偏移量
    # 留出足够空间。例如目标宽 500、crop_x=30，则放大后至少需要 530 宽。
    required_w = target_w + crop_x
    required_h = target_h + crop_y
    if source_w < required_w or source_h < required_h:
        scale = max(required_w / source_w, required_h / source_h)
        new_size = (math.ceil(source_w * scale), math.ceil(source_h * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    max_x = image.width - target_w
    max_y = image.height - target_h
    if crop_x > max_x or crop_y > max_y:
        raise ValueError(
            f"裁剪起点 ({crop_x}, {crop_y}) 超出可用范围；"
            f"当前图片允许的最大起点为 ({max_x}, {max_y})"
        )

    return image.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))


def save_image(image: Image.Image, output: Path, quality: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = output.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        image.save(output, quality=quality, optimize=True, subsampling=0)
    elif suffix == ".png":
        image.save(output, optimize=True)
    elif suffix == ".webp":
        image.save(output, quality=quality, method=6)
    else:
        raise ValueError("输出格式仅支持 .jpg、.jpeg、.png 或 .webp")


def main() -> None:
    args = parse_args()

    images = resolve_images(args.images, args.source)
    reference_path = (
        resolve_reference(args.reference, images, args.source)
        if args.reference is not None
        else None
    )

    missing = [str(path) for path in images if not path.is_file()]
    if missing:
        raise FileNotFoundError("找不到以下图片：\n" + "\n".join(missing))

    background = ImageColor.getrgb(args.background)
    if len(background) != 3:
        raise ValueError("背景颜色必须是 RGB 颜色，例如 #FFFFFF、black 或 rgb(20,20,20)")

    if reference_path is None:
        tile_size = calculate_auto_square_size(images)
        size_mode = "自动正方形"
    else:
        reference = open_normalized(reference_path, background)
        tile_size = reference.size
        size_mode = f"标准图片 {reference_path}"
    short_side = min(tile_size)
    gap = args.gap if args.gap is not None else max(4, round(short_side * 0.025))
    border = args.border if args.border is not None else max(8, round(short_side * 0.06))

    canvas_w = border * 2 + tile_size[0] * 3 + gap * 2
    canvas_h = border * 2 + tile_size[1] * 3 + gap * 2
    canvas = Image.new("RGB", (canvas_w, canvas_h), background)

    # 所有图片默认使用全局坐标；--crop 可按图片序号覆盖。
    crop_points = [(args.crop_x, args.crop_y) for _ in range(9)]
    for image_index, crop_x, crop_y in args.crop:
        crop_points[image_index] = (crop_x, crop_y)

    for index, path in enumerate(images):
        image = open_normalized(path, background)
        crop_x, crop_y = crop_points[index]
        try:
            tile = resize_then_crop(image, tile_size, crop_x, crop_y)
        except ValueError as exc:
            raise ValueError(f"第 {index + 1} 张图片 {path}：{exc}") from exc
        row, column = divmod(index, 3)
        left = border + column * (tile_size[0] + gap)
        top = border + row * (tile_size[1] + gap)
        canvas.paste(tile, (left, top))

    save_image(canvas, args.output, args.quality)
    print(f"已生成：{args.output.resolve()}")
    print(
        f"尺寸模式：{size_mode}；单格尺寸：{tile_size[0]}x{tile_size[1]}，"
        f"间隙：{gap}px，边框：{border}px"
    )


if __name__ == "__main__":
    main()