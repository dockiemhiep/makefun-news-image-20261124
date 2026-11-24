#!/usr/bin/env python3
"""Generate entry.png (1024x1024 newspaper front page) for make.fun news-image-20261124."""

from __future__ import annotations

import math
import os
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

# Canvas & palette
CANVAS_SIZE = (1024, 1024)
BG_COLOR = "#F7F3E8"
INK_COLOR = "#111111"
ACCENT_COLOR = "#A31621"
PANEL_BG = "#F7F3E8"

# Fonts (single Arial sans family)
FONT_BOLD_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"

# Exact verified copy (do not alter or add news text)
MASTHEAD_TITLE = "THE WORLD IN ONE PICTURE"
MASTHEAD_DATE = "TUESDAY \u00b7 24 NOVEMBER 2026"
FOOTER_TEXT = (
    "ALSO TODAY \u2014 COP31 FALLOUT: ERDOGAN SAYS TALKS LAID GROUNDWORK \u00b7 "
    "LISBON MARCHES AGAINST LIVING COSTS \u00b7 "
    "INDONESIA FACTORY FIRE SEARCH GOES ON"
)

PANELS = [
    {
        "tag": "TECH",
        "headline": "HUANG BACK AT NVIDIA AS SHARES SOAR 31%",
        "subline": "Board reinstates CEO 11 days after exit; Trump pressed for return",
        "motif": "chip_arrow",
    },
    {
        "tag": "WAR",
        "headline": "UKRAINE SINKS RUSSIAN WARSHIP OFF LIBYA",
        "subline": "Seven sea drones hit corvette Merkury; cargo ship Angara struck",
        "motif": "sinking_ship",
    },
    {
        "tag": "EUROPE",
        "headline": "EU UNVEILS 22ND SANCTIONS PACKAGE",
        "subline": "60 banks off SWIFT; Russian flag banned at EU sports events",
        "motif": "eu_gavel",
    },
    {
        "tag": "SPORT",
        "headline": "KIWIS BAT OUT DRAW AFTER INDIA'S 720",
        "subline": "Mitchell and Phillips defy India; Pant's 128 sets record total",
        "motif": "cricket",
    },
]


def measure_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont
) -> tuple[int, int, tuple[int, int, int, int]]:
    """Return (width, height, bbox) for text rendered at (0, 0)."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Word-wrap text using draw.textbbox so every line fits within max_width."""
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        cand_w, _, _ = measure_text(draw, candidate, font)
        if cand_w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    for line in lines:
        line_w, _, _ = measure_text(draw, line, font)
        if line_w > max_width:
            raise ValueError(
                f"Wrapped line overflows max_width ({line_w} > {max_width}): {line!r}"
            )
    return lines


def wrap_text_prefer_separator(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    separator: str = "\u00b7",
) -> list[str]:
    """Wrap text with wrap_text, preferring a break after separator if line count stays minimal."""
    greedy = wrap_text(draw, text, font, max_width)
    if len(greedy) != 2:
        return greedy

    words = text.split()
    best_pair: list[str] | None = None
    best_diff: int | None = None
    for idx, word in enumerate(words[:-1]):
        if word != separator:
            continue
        first = " ".join(words[: idx + 1])
        second = " ".join(words[idx + 1 :])
        w1, _, _ = measure_text(draw, first, font)
        w2, _, _ = measure_text(draw, second, font)
        if w1 <= max_width and w2 <= max_width:
            diff = abs(w1 - w2)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_pair = [first, second]
    return best_pair if best_pair is not None else greedy


def draw_text_exact(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> tuple[int, int]:
    """Draw text with visual top-left anchored precisely at (x, y); return (w, h)."""
    w, h, bbox = measure_text(draw, text, font)
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=fill)
    return w, h


def draw_wrapped_block(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    fill: str,
    line_step: int,
    max_width: int,
    center: bool = False,
) -> int:
    """Draw wrapped lines starting at visual y, returning bottom visual y."""
    if not lines:
        return y
    cur_y = y
    bottom_y = y
    for idx, line in enumerate(lines):
        w, h, bbox = measure_text(draw, line, font)
        if w > max_width:
            raise ValueError(f"Line width {w} exceeds max_width {max_width}: {line!r}")
        draw_x = x + (max_width - w) / 2.0 if center else float(x)
        draw.text((draw_x - bbox[0], cur_y - bbox[1]), line, font=font, fill=fill)
        bottom_y = cur_y + h
        if idx < len(lines) - 1:
            cur_y += line_step
    return bottom_y


def render_supersampled_motif(
    width: int,
    height: int,
    drawer: Callable[[ImageDraw.ImageDraw, int, int, int], None],
    scale: int = 4,
) -> Image.Image:
    """Render flat Pillow shapes at 4x scale and downsample cleanly with LANCZOS."""
    hi = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(hi)
    drawer(d, width * scale, height * scale, scale)
    return hi.resize((width, height), Image.Resampling.LANCZOS)


def draw_motif_chip_arrow(d: ImageDraw.ImageDraw, w: int, h: int, s: int) -> None:
    """Panel 1 motif: computer chip with pins on all 4 sides + bold upward arrow."""
    cy = h // 2
    chip_cx = int(w * 0.36)
    chip_half = 33 * s
    pin_len = 13 * s
    pin_w = max(1, int(3.5 * s))

    # Pins on all four sides (5 per side)
    offsets = [-22 * s, -11 * s, 0, 11 * s, 22 * s]
    for off in offsets:
        # Top pins
        d.rectangle(
            [
                chip_cx + off - pin_w // 2,
                cy - chip_half - pin_len,
                chip_cx + off + pin_w // 2,
                cy - chip_half + 2 * s,
            ],
            fill=INK_COLOR,
        )
        # Bottom pins
        d.rectangle(
            [
                chip_cx + off - pin_w // 2,
                cy + chip_half - 2 * s,
                chip_cx + off + pin_w // 2,
                cy + chip_half + pin_len,
            ],
            fill=INK_COLOR,
        )
        # Left pins
        d.rectangle(
            [
                chip_cx - chip_half - pin_len,
                cy + off - pin_w // 2,
                chip_cx - chip_half + 2 * s,
                cy + off + pin_w // 2,
            ],
            fill=INK_COLOR,
        )
        # Right pins
        d.rectangle(
            [
                chip_cx + chip_half - 2 * s,
                cy + off - pin_w // 2,
                chip_cx + chip_half + pin_len,
                cy + off + pin_w // 2,
            ],
            fill=INK_COLOR,
        )

    # Outer chip body (filled square)
    d.rounded_rectangle(
        [chip_cx - chip_half, cy - chip_half, chip_cx + chip_half, cy + chip_half],
        radius=6 * s,
        fill=INK_COLOR,
    )
    # Recessed inner circuit frame
    inner = 22 * s
    d.rounded_rectangle(
        [chip_cx - inner, cy - inner, chip_cx + inner, cy + inner],
        radius=3 * s,
        outline=BG_COLOR,
        width=3 * s,
    )
    # Deep-red silicon die core
    core = 11 * s
    d.rectangle(
        [chip_cx - core, cy - core, chip_cx + core, cy + core],
        fill=ACCENT_COLOR,
    )

    # Bold upward arrow beside the chip
    arrow_cx = int(w * 0.675)
    top_y = cy - 46 * s
    bot_y = cy + 39 * s
    head_base_y = cy - 8 * s
    head_half_w = 36 * s
    shaft_half_w = 15 * s

    arrow_poly = [
        (arrow_cx, top_y),
        (arrow_cx + head_half_w, head_base_y),
        (arrow_cx + shaft_half_w, head_base_y),
        (arrow_cx + shaft_half_w, bot_y),
        (arrow_cx - shaft_half_w, bot_y),
        (arrow_cx - shaft_half_w, head_base_y),
        (arrow_cx - head_half_w, head_base_y),
    ]
    d.polygon(arrow_poly, fill=ACCENT_COLOR)

    # Crisp baseline aligned flush with the bottom of the chip pins (cy + 46)
    d.rectangle(
        [arrow_cx - 34 * s, cy + 43 * s, arrow_cx + 34 * s, cy + 46 * s],
        fill=INK_COLOR,
    )


def _rotate_points(
    pts: list[tuple[float, float]], cx: float, cy: float, angle_deg: float
) -> list[tuple[float, float]]:
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    out = []
    for px, py in pts:
        dx, dy = px - cx, py - cy
        out.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return out


def draw_motif_sinking_ship(d: ImageDraw.ImageDraw, w: int, h: int, s: int) -> None:
    """Panel 2 motif: tilted sinking warship half-submerged in waves + drone boat."""
    water_y = int(h * 0.68)

    # Tilted sinking warship silhouette (bow pitched upward-left, stern submerged)
    pivot_x = w * 0.37
    pivot_y = water_y + 6 * s
    angle = 25.0  # tilts left side up, right stern down into the water

    # Warship hull (in local horizontal coords before tilt)
    hull_local = [
        (pivot_x - 95 * s, pivot_y - 16 * s),  # sharp bow tip
        (pivot_x + 88 * s, pivot_y - 14 * s),  # stern deck
        (pivot_x + 76 * s, pivot_y + 22 * s),  # lower stern
        (pivot_x - 68 * s, pivot_y + 22 * s),  # lower bow
    ]
    # Bridge / superstructure
    bridge_local = [
        (pivot_x - 30 * s, pivot_y - 15 * s),
        (pivot_x - 22 * s, pivot_y - 40 * s),
        (pivot_x + 12 * s, pivot_y - 40 * s),
        (pivot_x + 22 * s, pivot_y - 15 * s),
    ]
    # Funnel / aft structure
    aft_local = [
        (pivot_x + 26 * s, pivot_y - 15 * s),
        (pivot_x + 30 * s, pivot_y - 31 * s),
        (pivot_x + 48 * s, pivot_y - 31 * s),
        (pivot_x + 52 * s, pivot_y - 15 * s),
    ]
    # Forward naval gun turret
    turret_local = [
        (pivot_x - 66 * s, pivot_y - 16 * s),
        (pivot_x - 62 * s, pivot_y - 26 * s),
        (pivot_x - 45 * s, pivot_y - 26 * s),
        (pivot_x - 42 * s, pivot_y - 16 * s),
    ]
    # Mast + radar crossbar
    mast_pts = _rotate_points(
        [(pivot_x - 4 * s, pivot_y - 40 * s), (pivot_x - 4 * s, pivot_y - 62 * s)],
        pivot_x,
        pivot_y,
        angle,
    )
    radar_pts = _rotate_points(
        [(pivot_x - 16 * s, pivot_y - 54 * s), (pivot_x + 8 * s, pivot_y - 54 * s)],
        pivot_x,
        pivot_y,
        angle,
    )
    gun_pts = _rotate_points(
        [(pivot_x - 62 * s, pivot_y - 22 * s), (pivot_x - 82 * s, pivot_y - 29 * s)],
        pivot_x,
        pivot_y,
        angle,
    )

    d.polygon(_rotate_points(hull_local, pivot_x, pivot_y, angle), fill=INK_COLOR)
    d.polygon(_rotate_points(bridge_local, pivot_x, pivot_y, angle), fill=INK_COLOR)
    d.polygon(_rotate_points(aft_local, pivot_x, pivot_y, angle), fill=INK_COLOR)
    d.polygon(_rotate_points(turret_local, pivot_x, pivot_y, angle), fill=INK_COLOR)
    d.line(mast_pts, fill=INK_COLOR, width=4 * s)
    d.line(radar_pts, fill=INK_COLOR, width=3 * s)
    d.line(gun_pts, fill=INK_COLOR, width=3 * s)

    # Small deep-red strike burst erupting from the sinking stern near the waterline
    bx = pivot_x + 41 * s
    by = water_y - 5 * s
    burst_rays = [
        [(bx, by), (bx - 12 * s, by - 22 * s), (bx - 3 * s, by - 14 * s)],
        [(bx, by), (bx + 2 * s, by - 28 * s), (bx + 7 * s, by - 14 * s)],
        [(bx, by), (bx + 18 * s, by - 20 * s), (bx + 11 * s, by - 8 * s)],
    ]
    for ray in burst_rays:
        d.polygon(ray, fill=ACCENT_COLOR)

    # Mask below the top wave so the sinking stern is cleanly submerged
    wave_left = int(w * 0.08)
    wave_right = int(w * 0.92)
    step = 4 * s

    def wave_curve(y_base: float, amp: float, period: float, phase: float) -> list[tuple[float, float]]:
        pts = []
        x = wave_left
        while x <= wave_right:
            yy = y_base + math.sin((x - wave_left) / period * 2.0 * math.pi + phase) * amp
            pts.append((float(x), yy))
            x += step
        pts.append(
            (
                float(wave_right),
                y_base + math.sin((wave_right - wave_left) / period * 2.0 * math.pi + phase) * amp,
            )
        )
        return pts

    top_wave = wave_curve(water_y, 5.5 * s, 56 * s, 0.0)
    mask_poly = top_wave + [(float(wave_right), float(h)), (float(wave_left), float(h))]
    d.polygon(mask_poly, fill=BG_COLOR)

    # Small sea drone boat riding the wave surface on the right (low hull + antenna)
    drone_x1 = int(w * 0.675)
    drone_x2 = int(w * 0.855)
    drone_bot = water_y + 5 * s
    drone_top = water_y - 12 * s
    # Low sleek drone hull seated cleanly in the wave
    d.polygon(
        [
            (drone_x1 - 9 * s, drone_top + 5 * s),  # pointed bow facing ship
            (drone_x1 + 5 * s, drone_top),
            (drone_x2, drone_top),
            (drone_x2, drone_bot),
            (drone_x1, drone_bot),
        ],
        fill=INK_COLOR,
    )
    # Small low camera/sensor dome
    d.rectangle(
        [drone_x1 + 16 * s, drone_top - 6 * s, drone_x1 + 33 * s, drone_top + 1 * s],
        fill=ACCENT_COLOR,
    )
    # Antenna mast with signal tip
    ant_x = drone_x2 - 13 * s
    d.line([(ant_x, drone_top), (ant_x, drone_top - 26 * s)], fill=INK_COLOR, width=3 * s)
    r_tip = 4.5 * s
    d.ellipse(
        [ant_x - r_tip, drone_top - 26 * s - r_tip, ant_x + r_tip, drone_top - 26 * s + r_tip],
        fill=ACCENT_COLOR,
    )
    # Subtle drone wake streak to the right
    d.line(
        [(drone_x2 + 6 * s, water_y - 5 * s), (drone_x2 + 22 * s, water_y - 5 * s)],
        fill=INK_COLOR,
        width=2 * s,
    )

    # Mask below top wave again over drone lower hull so it sits naturally in the water
    d.polygon(mask_poly, fill=BG_COLOR)

    # Layered wavy water lines
    d.line(top_wave, fill=INK_COLOR, width=4 * s, joint="curve")
    mid_wave = wave_curve(water_y + 13 * s, 4.5 * s, 56 * s, 1.8)
    d.line(mid_wave, fill=INK_COLOR, width=3 * s, joint="curve")
    low_wave = wave_curve(water_y + 25 * s, 3.5 * s, 56 * s, 3.4)
    d.line(low_wave, fill=ACCENT_COLOR, width=2 * s, joint="curve")


def draw_motif_eu_gavel(d: ImageDraw.ImageDraw, w: int, h: int, s: int) -> None:
    """Panel 3 motif: circle of 12 stars/dots arranged in a ring around a gavel."""
    cx = w / 2.0
    cy = h / 2.0
    ring_r = 51.0 * s
    dot_r = 4.9 * s

    # 12 dots arranged evenly around a circle (EU ring)
    for i in range(12):
        theta = math.radians(-90 + i * 30)
        px = cx + ring_r * math.cos(theta)
        py = cy + ring_r * math.sin(theta)
        d.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r], fill=ACCENT_COLOR)

    # Gavel centered inside the ring (tilted head + handle + small sound block)
    gcx = cx - 4 * s
    gcy = cy - 4 * s
    angle = -38.0

    # Gavel head (rectangle + end-cap bands)
    head_w = 34 * s
    head_h = 16 * s
    head_local = [
        (gcx - head_w / 2, gcy - head_h / 2),
        (gcx + head_w / 2, gcy - head_h / 2),
        (gcx + head_w / 2, gcy + head_h / 2),
        (gcx - head_w / 2, gcy + head_h / 2),
    ]
    cap_w = 5 * s
    cap_h = 20 * s
    left_cap = [
        (gcx - head_w / 2 - cap_w, gcy - cap_h / 2),
        (gcx - head_w / 2, gcy - cap_h / 2),
        (gcx - head_w / 2, gcy + cap_h / 2),
        (gcx - head_w / 2 - cap_w, gcy + cap_h / 2),
    ]
    right_cap = [
        (gcx + head_w / 2, gcy - cap_h / 2),
        (gcx + head_w / 2 + cap_w, gcy - cap_h / 2),
        (gcx + head_w / 2 + cap_w, gcy + cap_h / 2),
        (gcx + head_w / 2, gcy + cap_h / 2),
    ]
    # Handle extending down-right from the head center
    handle_w = 7 * s
    handle_len = 36 * s
    handle_local = [
        (gcx - handle_w / 2, gcy + head_h / 2 - 2 * s),
        (gcx + handle_w / 2, gcy + head_h / 2 - 2 * s),
        (gcx + handle_w / 2 + 1 * s, gcy + head_h / 2 + handle_len),
        (gcx - handle_w / 2 - 1 * s, gcy + head_h / 2 + handle_len),
    ]

    d.polygon(_rotate_points(handle_local, gcx, gcy, angle), fill=INK_COLOR)
    d.polygon(_rotate_points(head_local, gcx, gcy, angle), fill=INK_COLOR)
    d.polygon(_rotate_points(left_cap, gcx, gcy, angle), fill=ACCENT_COLOR)
    d.polygon(_rotate_points(right_cap, gcx, gcy, angle), fill=ACCENT_COLOR)

    # Small strike block centered cleanly underneath the gavel
    block_y = cy + 23 * s
    d.rounded_rectangle(
        [cx - 21 * s, block_y, cx + 11 * s, block_y + 7 * s],
        radius=2 * s,
        fill=INK_COLOR,
    )


def draw_motif_cricket(d: ImageDraw.ImageDraw, w: int, h: int, s: int) -> None:
    """Panel 4 motif: cricket bat + cricket ball with curved seam + stumps trio."""
    cy = h // 2

    # 1. Cricket bat (left): upright rounded-rectangle blade + angled shoulders + grip handle
    bat_cx = int(w * 0.27)
    blade_w = 26 * s
    blade_top = cy - 14 * s
    blade_bot = cy + 48 * s
    handle_w = 7 * s
    handle_top = cy - 48 * s

    # Handle
    d.rounded_rectangle(
        [bat_cx - handle_w // 2, handle_top, bat_cx + handle_w // 2, blade_top + 4 * s],
        radius=3 * s,
        fill=ACCENT_COLOR,
    )
    # Grip stripes on handle
    for gy in range(handle_top + 6 * s, blade_top - 4 * s, 7 * s):
        d.line(
            [(bat_cx - handle_w // 2, gy), (bat_cx + handle_w // 2, gy)],
            fill=INK_COLOR,
            width=2 * s,
        )
    # Angled cricket-bat shoulders joining handle to blade
    d.polygon(
        [
            (bat_cx - handle_w // 2, blade_top - 4 * s),
            (bat_cx + handle_w // 2, blade_top - 4 * s),
            (bat_cx + blade_w // 2, blade_top + 4 * s),
            (bat_cx - blade_w // 2, blade_top + 4 * s),
        ],
        fill=INK_COLOR,
    )
    # Long rounded-rectangle blade
    d.rounded_rectangle(
        [bat_cx - blade_w // 2, blade_top, bat_cx + blade_w // 2, blade_bot],
        radius=6 * s,
        fill=INK_COLOR,
    )
    # Subtle center ridge line on the bat blade
    d.line(
        [(bat_cx, blade_top + 8 * s), (bat_cx, blade_bot - 10 * s)],
        fill=BG_COLOR,
        width=2 * s,
    )

    # 2. Cricket ball (center): filled deep-red circle with curved seam line
    ball_cx = int(w * 0.49)
    ball_cy = cy + 8 * s
    ball_r = 25 * s
    d.ellipse(
        [ball_cx - ball_r, ball_cy - ball_r, ball_cx + ball_r, ball_cy + ball_r],
        fill=ACCENT_COLOR,
    )
    # Curved double-stitch seam line across the ball
    seam_box_1 = [
        ball_cx - ball_r - 14 * s,
        ball_cy - ball_r - 2 * s,
        ball_cx + ball_r - 12 * s,
        ball_cy + ball_r + 2 * s,
    ]
    d.arc(seam_box_1, start=-56, end=56, fill=BG_COLOR, width=3 * s)
    seam_box_2 = [
        ball_cx - ball_r - 8 * s,
        ball_cy - ball_r - 2 * s,
        ball_cx + ball_r - 6 * s,
        ball_cy + ball_r + 2 * s,
    ]
    d.arc(seam_box_2, start=-52, end=52, fill=BG_COLOR, width=2 * s)
    # Crisp radial stitch ticks between the twin seam arcs
    arc_cx = ball_cx - 10 * s
    arc_rx = ball_r + 1 * s
    arc_ry = ball_r + 2 * s
    for deg in range(-42, 43, 14):
        rad = math.radians(deg)
        sx0 = arc_cx + (arc_rx - 3.5 * s) * math.cos(rad)
        sy0 = ball_cy + (arc_ry - 3.5 * s) * math.sin(rad)
        sx1 = arc_cx + (arc_rx + 3.5 * s) * math.cos(rad)
        sy1 = ball_cy + (arc_ry + 3.5 * s) * math.sin(rad)
        d.line([(sx0, sy0), (sx1, sy1)], fill=BG_COLOR, width=max(1, int(1.8 * s)))

    # 3. Stumps trio (right): three thin vertical lines + minimal bails & crease
    stump_cx = int(w * 0.72)
    stump_top = cy - 36 * s
    stump_bot = cy + 48 * s
    spacing = 16 * s
    stump_w = 5 * s

    for dx in (-spacing, 0, spacing):
        sx = stump_cx + dx
        d.line([(sx, stump_top), (sx, stump_bot)], fill=INK_COLOR, width=stump_w)

    # Two minimal bails atop the three stumps
    bail_y = stump_top - 4 * s
    d.line(
        [(stump_cx - spacing - 2 * s, bail_y), (stump_cx - 2 * s, bail_y)],
        fill=ACCENT_COLOR,
        width=4 * s,
    )
    d.line(
        [(stump_cx + 2 * s, bail_y), (stump_cx + spacing + 2 * s, bail_y)],
        fill=ACCENT_COLOR,
        width=4 * s,
    )
    # Crisp pitch baseline
    d.line(
        [(stump_cx - spacing - 16 * s, stump_bot + 1 * s), (stump_cx + spacing + 16 * s, stump_bot + 1 * s)],
        fill=INK_COLOR,
        width=3 * s,
    )


MOTIF_REGISTRY: dict[str, Callable[[ImageDraw.ImageDraw, int, int, int], None]] = {
    "chip_arrow": draw_motif_chip_arrow,
    "sinking_ship": draw_motif_sinking_ship,
    "eu_gavel": draw_motif_eu_gavel,
    "cricket": draw_motif_cricket,
}


def build_front_page() -> Image.Image:
    """Compose and return the 1024x1024 newspaper front page image."""
    img = Image.new("RGB", CANVAS_SIZE, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Load Arial font family
    font_masthead = ImageFont.truetype(FONT_BOLD_PATH, 64)
    font_date = ImageFont.truetype(FONT_BOLD_PATH, 30)
    font_tag = ImageFont.truetype(FONT_BOLD_PATH, 16)
    font_headline = ImageFont.truetype(FONT_BOLD_PATH, 44)
    font_subline = ImageFont.truetype(FONT_REG_PATH, 24)
    font_footer = ImageFont.truetype(FONT_REG_PATH, 22)

    # Outer layout geometry
    margin_x = 22
    content_w = CANVAS_SIZE[0] - 2 * margin_x  # 980px

    # --- Masthead ---
    title_w, title_h, _ = measure_text(draw, MASTHEAD_TITLE, font_masthead)
    if title_w > content_w:
        raise ValueError(f"Masthead title overflows: {title_w} > {content_w}")
    title_x = (CANVAS_SIZE[0] - title_w) / 2.0
    title_y = 20
    draw_text_exact(draw, title_x, title_y, MASTHEAD_TITLE, font_masthead, INK_COLOR)

    # Deep-red rule beneath masthead title (symmetrical 12px above and below)
    rule_y = title_y + title_h + 12
    rule_h = 4
    draw.rectangle([margin_x, rule_y, CANVAS_SIZE[0] - margin_x, rule_y + rule_h - 1], fill=ACCENT_COLOR)

    # Date line centered below deep-red rule
    date_w, date_h, _ = measure_text(draw, MASTHEAD_DATE, font_date)
    if date_w > content_w:
        raise ValueError(f"Masthead date overflows: {date_w} > {content_w}")
    date_x = (CANVAS_SIZE[0] - date_w) / 2.0
    date_y = rule_y + rule_h + 12
    draw_text_exact(draw, date_x, date_y, MASTHEAD_DATE, font_date, INK_COLOR)

    # --- Footer geometry (measured first so panels get exact remaining height) ---
    footer_pad_x = 2
    footer_max_w = content_w - 2 * footer_pad_x
    footer_lines = wrap_text_prefer_separator(draw, FOOTER_TEXT, font_footer, footer_max_w)
    footer_line_step = 28
    _, footer_line_h, _ = measure_text(draw, "Ag", font_footer)
    footer_text_h = (len(footer_lines) - 1) * footer_line_step + footer_line_h

    footer_bottom_margin = 20
    footer_top_pad = 12
    footer_rule_thickness = 3
    footer_text_y = CANVAS_SIZE[1] - footer_bottom_margin - footer_text_h
    footer_rule_y = footer_text_y - footer_top_pad - footer_rule_thickness

    draw.rectangle(
        [margin_x, footer_rule_y, CANVAS_SIZE[0] - margin_x, footer_rule_y + footer_rule_thickness - 1],
        fill=INK_COLOR,
    )
    footer_bottom = draw_wrapped_block(
        draw,
        margin_x + footer_pad_x,
        footer_text_y,
        footer_lines,
        font_footer,
        INK_COLOR,
        footer_line_step,
        footer_max_w,
        center=True,
    )
    if footer_bottom > CANVAS_SIZE[1] - 10:
        raise ValueError(f"Footer overflows bottom of canvas: {footer_bottom}")

    # --- 2x2 Panel Grid ---
    grid_top = date_y + date_h + 16
    grid_bottom = footer_rule_y - 14
    gutter_x = 14
    gutter_y = 14

    panel_w = (content_w - gutter_x) // 2  # 483px
    panel_h = (grid_bottom - grid_top - gutter_y) // 2

    # Recenter grid horizontally if odd pixel remains
    grid_left = (CANVAS_SIZE[0] - (2 * panel_w + gutter_x)) // 2

    for idx, panel in enumerate(PANELS):
        row = idx // 2
        col = idx % 2
        px0 = grid_left + col * (panel_w + gutter_x)
        py0 = grid_top + row * (panel_h + gutter_y)
        px1 = px0 + panel_w - 1
        py1 = py0 + panel_h - 1

        # Panel background + thin crisp black border
        draw.rectangle([px0, py0, px1, py1], fill=PANEL_BG, outline=INK_COLOR, width=2)

        inner_pad_x = 15
        inner_pad_top = 15
        inner_pad_bot = 10
        text_x = px0 + inner_pad_x
        text_max_w = panel_w - 2 * inner_pad_x

        # Deep-red category tag at top-left
        tag_text = panel["tag"]
        tag_w, tag_h, _ = measure_text(draw, tag_text, font_tag)
        tag_pad_x = 9
        tag_pad_y = 5
        tag_x0 = text_x
        tag_y0 = py0 + inner_pad_top
        tag_x1 = tag_x0 + tag_w + 2 * tag_pad_x
        tag_y1 = tag_y0 + tag_h + 2 * tag_pad_y
        draw.rectangle([tag_x0, tag_y0, tag_x1, tag_y1], fill=ACCENT_COLOR)
        draw_text_exact(
            draw,
            tag_x0 + tag_pad_x,
            tag_y0 + tag_pad_y,
            tag_text,
            font_tag,
            BG_COLOR,
        )

        # BIG bold headline (>= 44px, wrapped first to fit cleanly)
        headline_lines = wrap_text(draw, panel["headline"], font_headline, text_max_w)
        headline_y = tag_y1 + 12
        headline_step = 45
        _, cap_h, _ = measure_text(draw, "H", font_headline)
        headline_bottom = draw_wrapped_block(
            draw,
            text_x,
            headline_y,
            headline_lines,
            font_headline,
            INK_COLOR,
            headline_step,
            text_max_w,
        )
        # Align sub-line on a uniform horizontal rail across panels with equal line count
        uniform_headline_bot = headline_y + (len(headline_lines) - 1) * headline_step + cap_h
        sub_y = max(headline_bottom, uniform_headline_bot) + 14

        # Sub-line (24px regular Arial)
        sub_lines = wrap_text(draw, panel["subline"], font_subline, text_max_w)
        sub_step = 28
        _, sub_full_h, _ = measure_text(draw, "Ag", font_subline)
        sub_bottom = draw_wrapped_block(
            draw,
            text_x,
            sub_y,
            sub_lines,
            font_subline,
            INK_COLOR,
            sub_step,
            text_max_w,
        )
        uniform_sub_bot = sub_y + (len(sub_lines) - 1) * sub_step + sub_full_h

        # Remaining space for flat Pillow motif
        motif_top = max(sub_bottom, uniform_sub_bot) + 10
        motif_bot = py1 - inner_pad_bot
        motif_h = motif_bot - motif_top
        motif_w = text_max_w
        if motif_h < 70:
            raise ValueError(
                f"Panel {idx + 1} ({tag_text}) left insufficient motif height: {motif_h}px"
            )

        motif_img = render_supersampled_motif(
            motif_w, motif_h, MOTIF_REGISTRY[panel["motif"]], scale=4
        )
        img.paste(motif_img, (text_x, motif_top), motif_img)

    # Mandatory final dimension check
    if img.size != CANVAS_SIZE:
        raise AssertionError(f"Expected image size {CANVAS_SIZE}, got {img.size}")
    return img


def main() -> None:
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(repo_dir, "entry.png")

    img = build_front_page()
    assert img.size == (1024, 1024), f"Unexpected size: {img.size}"

    img.save(out_path, format="PNG", optimize=True)

    # Re-open and verify written file
    with Image.open(out_path) as check:
        assert check.size == (1024, 1024), f"Saved image size mismatch: {check.size}"
    byte_size = os.path.getsize(out_path)
    assert byte_size <= 1_048_576, f"entry.png too large: {byte_size} bytes"
    print(f"Wrote {out_path}: dimensions={img.size[0]}x{img.size[1]}, bytes={byte_size}")


if __name__ == "__main__":
    main()
