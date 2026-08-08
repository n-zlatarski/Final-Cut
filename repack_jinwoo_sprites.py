"""Repack generated Jinwoo sprite sheets onto a strict 256x256 frame grid.

The image generator lays out sprite centers on an approximate visual grid,
which is not identical to slicing the final PNG into equal-width/equal-height
cells.  This utility measures the actual sprite lattice from opaque dark
character pixels, partitions the source sheet between those measured centers,
and translates each logical frame onto an exact fixed-size cell.

Inputs are expected to have transparency already (chroma removal is performed
before this script is run).  The operation is lossless apart from pixels that
would fall outside their own 256x256 destination cell.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def _axis_centers(weights: np.ndarray, groups: int, total: int) -> np.ndarray:
    """Return weighted 1-D cluster centers, initialized to an even grid."""
    positions = np.arange(total, dtype=np.float64)
    centers = np.linspace(total / (2 * groups), total - total / (2 * groups), groups)

    for _ in range(40):
        labels = np.abs(positions[:, None] - centers[None, :]).argmin(axis=1)
        updated = centers.copy()
        for index in range(groups):
            selected = labels == index
            group_weights = weights[selected].astype(np.float64)
            weight_sum = group_weights.sum()
            if weight_sum:
                updated[index] = (
                    positions[selected] * group_weights
                ).sum() / weight_sum

        if np.max(np.abs(updated - centers)) < 0.01:
            centers = updated
            break
        centers = updated

    return centers


def _boundaries(centers: np.ndarray, limit: int) -> list[int]:
    return [0] + [
        int(round((centers[i] + centers[i + 1]) / 2))
        for i in range(len(centers) - 1)
    ] + [limit]


def repack(source: Path, destination: Path, cols: int, rows: int, cell: int) -> None:
    image = Image.open(source).convert("RGBA")
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3]

    # Coat, hair, pants and contact-shadow pixels form a reliable lattice and
    # intentionally ignore bright red/blue attack trails when measuring it.
    luminance = (
        pixels[:, :, 0].astype(np.uint16) * 3
        + pixels[:, :, 1].astype(np.uint16) * 6
        + pixels[:, :, 2].astype(np.uint16)
    ) // 10
    anchor_mask = (alpha > 80) & (luminance < 115)

    x_centers = _axis_centers(anchor_mask.sum(axis=0), cols, image.width)
    y_centers = _axis_centers(anchor_mask.sum(axis=1), rows, image.height)
    x_bounds = _boundaries(x_centers, image.width)
    y_bounds = _boundaries(y_centers, image.height)

    output = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            x0, x1 = x_bounds[col], x_bounds[col + 1]
            y0, y1 = y_bounds[row], y_bounds[row + 1]
            frame = image.crop((x0, y0, x1, y1))

            dest_x = col * cell + round(cell / 2 - (x_centers[col] - x0))
            dest_y = row * cell + round(cell / 2 - (y_centers[row] - y0))
            output.alpha_composite(frame, (dest_x, dest_y))

    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination)

    x_text = ", ".join(f"{value:.1f}" for value in x_centers)
    y_text = ", ".join(f"{value:.1f}" for value in y_centers)
    print(f"{source.name}: x=[{x_text}] y=[{y_text}] -> {destination}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("cols", type=int)
    parser.add_argument("rows", type=int)
    parser.add_argument("--cell", type=int, default=256)
    args = parser.parse_args()
    repack(args.source, args.destination, args.cols, args.rows, args.cell)


if __name__ == "__main__":
    main()
