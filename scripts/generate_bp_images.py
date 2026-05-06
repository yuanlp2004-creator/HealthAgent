"""
Generate realistic synthetic blood pressure monitor screen images for OCR testing.

Key realism features:
- Seven-segment digit rendering (drawn as polygons, not fonts)
- LCD screen with bezel, labels, icons
- Realistic artifacts: glare, uneven lighting, noise, blur, rotation
- Multiple screen types and shooting conditions
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

OUT_DIR = Path("datasets/bp_images")
LABELS = OUT_DIR / "labels.json"
IMG_W, IMG_H = 800, 600

# ---------------------------------------------------------------------------
# Seven-segment digit geometry
# Each segment is a polygon defined relative to a cell (x, y, w, h)
# Cell layout:
#   aaa
#  f   b
#  f   b
#   ggg
#  e   c
#  e   c
#   ddd
# ---------------------------------------------------------------------------

def _seg(x, y, w, h, thickness, points):
    """Scale segment points from unit coords to actual coords."""
    return [(x + px * w, y + py * h) for (px, py) in points]


def segment_polygons(cx, cy, digit_w, digit_h, thickness):
    """Return dict of segment_name -> polygon_vertices for a digit cell at (cx, cy)."""
    t = thickness
    # Unit-space definitions (0..1 within the cell)
    seg_defs = {
        "a": [(0.10, 0.02), (0.90, 0.02), (0.85, 0.08), (0.15, 0.08)],
        "b": [(0.92, 0.05), (0.96, 0.48), (0.88, 0.48), (0.84, 0.05)],
        "c": [(0.92, 0.52), (0.96, 0.95), (0.88, 0.95), (0.84, 0.52)],
        "d": [(0.10, 0.92), (0.90, 0.92), (0.85, 0.98), (0.15, 0.98)],
        "e": [(0.04, 0.52), (0.08, 0.95), (0.16, 0.95), (0.12, 0.52)],
        "f": [(0.04, 0.05), (0.08, 0.48), (0.16, 0.48), (0.12, 0.05)],
        "g": [(0.10, 0.46), (0.90, 0.46), (0.85, 0.54), (0.15, 0.54)],
    }
    return {k: _seg(cx, cy, digit_w, digit_h, t, v) for k, v in seg_defs.items()}


# Which segments are lit for each digit
DIGIT_SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "-": "g",
}


def draw_seven_seg_digit(draw, cx, cy, digit_char, digit_w, digit_h, fg_color,
                         off_color=(30, 40, 30)):
    """Draw a single seven-segment digit with both on and off segments visible."""
    segs = segment_polygons(cx, cy, digit_w, digit_h, thickness=0.08)
    on_segs = set(DIGIT_SEGMENTS.get(digit_char, ""))
    # Draw OFF segments (faintly visible - key LCD realism detail)
    for name, poly in segs.items():
        if name not in on_segs:
            draw.polygon(poly, fill=off_color)
    # Draw ON segments
    for name in on_segs:
        if name in segs:
            draw.polygon(segs[name], fill=fg_color)


def draw_seven_seg_number(draw, x, y, value, digit_w=52, digit_h=90, spacing=10,
                          fg_color=(40, 50, 40), off_color=(30, 40, 30)):
    """Draw a multi-digit number using seven-segment style."""
    s = str(value)
    total_w = len(s) * digit_w + (len(s) - 1) * spacing
    cx_start = x - total_w / 2 + digit_w / 2
    for i, ch in enumerate(s):
        cx = cx_start + i * (digit_w + spacing)
        draw_seven_seg_digit(draw, cx, y, ch, digit_w, digit_h, fg_color, off_color)


# ---------------------------------------------------------------------------
# Screen style presets (LCD background + digit colors + label colors)
# ---------------------------------------------------------------------------

SCREEN_STYLES = [
    # (name, bg_color, fg_color, off_seg_color, label_color, bezel_color)
    ("green_backlight", (15, 35, 15), (120, 230, 100), (18, 40, 18), (70, 160, 60), (5, 12, 5)),
    ("green_backlight_dim", (12, 28, 12), (90, 190, 75), (15, 32, 15), (55, 130, 50), (4, 8, 4)),
    ("gray_reflective", (145, 150, 140), (35, 40, 30), (138, 143, 133), (60, 65, 55), (100, 105, 95)),
    ("gray_reflective_dark", (100, 105, 95), (25, 30, 20), (95, 100, 90), (45, 50, 40), (70, 75, 65)),
    ("blue_backlight", (8, 15, 45), (150, 190, 240), (10, 18, 50), (80, 130, 200), (3, 6, 18)),
    ("blue_backlight_bright", (10, 20, 55), (190, 220, 255), (12, 23, 60), (100, 160, 230), (4, 8, 20)),
    ("warm_orange", (50, 30, 10), (240, 180, 100), (52, 32, 12), (200, 130, 60), (20, 10, 3)),
    ("olive_lcd", (40, 45, 20), (140, 160, 60), (38, 43, 18), (90, 110, 45), (15, 18, 5)),
    ("dark_green_lcd", (8, 20, 8), (100, 200, 80), (10, 22, 10), (50, 130, 40), (2, 6, 2)),
    ("cool_white_backlight", (30, 35, 40), (200, 220, 240), (32, 38, 44), (140, 170, 200), (10, 12, 14)),
]


def generate_lcd_background(draw, w, h, style):
    """Draw LCD screen background with subtle texture."""
    bg_r, bg_g, bg_b = style[1]

    # Base gradient (top lighter -> bottom darker, simulating uneven backlight)
    for y in range(h):
        factor = 1.0 - 0.25 * (y / h)
        # Add subtle horizontal banding (LCD scan line effect)
        if y % 3 == 0:
            factor -= 0.03 * random.random()
        r = max(0, min(255, int(bg_r * factor)))
        g = max(0, min(255, int(bg_g * factor)))
        b = max(0, min(255, int(bg_b * factor)))
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Subtle vignette (darker corners)
    for x in range(0, w, 4):
        for y in range(0, h, 4):
            dx = (x - w / 2) / (w / 2)
            dy = (y - h / 2) / (h / 2)
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0.7:
                alpha = (dist - 0.7) / 0.3 * 0.3
                draw.rectangle([x, y, x + 3, y + 3],
                               fill=(0, 0, 0, int(alpha * 255)) if hasattr(draw, 'RGBA') else (0, 0, 0))


def add_glare(image, glare_type="spot"):
    """Add realistic glare/reflection on the screen."""
    w, h = image.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if glare_type == "spot":
        # A bright spot (like a window reflection)
        cx = random.randint(int(w * 0.2), int(w * 0.8))
        cy = random.randint(int(h * 0.2), int(h * 0.6))
        radius = random.randint(40, 120)
        for r in range(radius, 0, -5):
            alpha = int(80 * (r / radius) * (r / radius))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         fill=(255, 255, 255, alpha))

    elif glare_type == "edge":
        # Light bleeding from an edge (like window light at screen edge)
        edge = random.choice(["top", "bottom", "left", "right"])
        for i in range(0, 60, 2):
            alpha = int(40 * (1 - i / 60))
            if edge == "top":
                draw.rectangle([0, i, w, i + 2], fill=(255, 255, 240, alpha))
            elif edge == "bottom":
                draw.rectangle([0, h - i - 2, w, h - i], fill=(255, 255, 240, alpha))
            elif edge == "left":
                draw.rectangle([i, 0, i + 2, h], fill=(255, 255, 240, alpha))
            else:
                draw.rectangle([w - i - 2, 0, w - i, h], fill=(255, 255, 240, alpha))

    elif glare_type == "streak":
        # Diagonal light streak
        x0 = random.randint(0, w)
        length = random.randint(100, 300)
        angle = random.uniform(-0.5, 0.5)
        for t in range(length):
            alpha = int(60 * (1 - abs(t - length / 2) / (length / 2)))
            x = int(x0 + t * math.cos(angle))
            y = int(h * 0.3 + t * math.sin(angle))
            if 0 <= x < w and 0 <= y < h:
                draw.rectangle([x - 2, y - 1, x + 2, y + 1],
                               fill=(255, 255, 255, alpha))

    # Composite onto image
    image_rgba = image.convert("RGBA")
    result = Image.alpha_composite(image_rgba, overlay).convert("RGB")
    return result


def simulate_camera_artifacts(image):
    """Apply realistic camera/screen artifacts."""
    arr = np.array(image).astype("int16")

    # Gaussian noise (camera sensor noise)
    noise_std = random.uniform(3.0, 8.0)
    noise = np.random.normal(0, noise_std, arr.shape).astype("int16")
    arr = arr + noise

    # Salt-and-pepper noise (dead pixels)
    if random.random() < 0.3:
        sp_prob = random.uniform(0.001, 0.005)
        mask = np.random.random(arr.shape[:2]) < sp_prob
        salt = np.random.random(arr.shape[:2]) < 0.5
        arr[mask & salt] = 255
        arr[mask & ~salt] = 0

    arr = np.clip(arr, 0, 255).astype("uint8")
    image = Image.fromarray(arr)

    # Gaussian blur (out of focus)
    if random.random() < 0.5:
        blur_radius = random.uniform(0.3, 1.5)
        image = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Brightness/contrast variation
    if random.random() < 0.6:
        factor = random.uniform(0.6, 1.4)
        image = ImageEnhance.Brightness(image).enhance(factor)

    if random.random() < 0.4:
        factor = random.uniform(0.7, 1.3)
        image = ImageEnhance.Contrast(image).enhance(factor)

    # Slight color shift (white balance)
    if random.random() < 0.3:
        arr = np.array(image).astype("int16")
        shift = np.random.randint(-15, 15, 3)
        arr = arr + shift.reshape(1, 1, 3)
        arr = np.clip(arr, 0, 255).astype("uint8")
        image = Image.fromarray(arr)

    return image


def add_screen_bezel(draw, w, h, style):
    """Draw the device bezel around the LCD screen area."""
    bezel_color = style[5]
    # Screen area inset
    margin = 40
    # Outer device body
    body_margin = 15
    draw.rectangle([body_margin, body_margin, w - body_margin, h - body_margin],
                   fill=bezel_color, outline=(20, 20, 20), width=2)
    # Screen area
    draw.rectangle([margin, margin, w - margin, h - margin],
                   fill=style[1], outline=(0, 0, 0), width=1)


def generate_test_cases():
    """Generate diverse test cases covering different BP ranges and conditions."""
    cases = [
        # (systolic, diastolic, hr, glare_type, extra_effects)
        (128, 82, 74, "spot", ["rotation"]),
        (142, 88, 68, "edge", ["darken"]),
        (155, 96, 82, "streak", ["blur"]),
        (98, 55, 90, "spot", ["noise", "darken"]),
        (135, 79, 65, "edge", []),
        (162, 102, 88, "streak", ["rotation", "blur"]),
        (116, 70, 72, "spot", ["brighten"]),
        (149, 91, 77, "edge", ["noise"]),
        (105, 62, 85, "streak", ["rotation", "darken"]),
        (138, 85, 93, "spot", ["blur", "noise"]),
    ]
    return cases


def generate_image(index, systolic, diastolic, heart_rate, style, glare_type, effects, note):
    """Generate one synthetic blood pressure monitor screen image."""
    w, h = IMG_W, IMG_H
    img = Image.new("RGB", (w, h), (30, 30, 30))
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw bezel
    add_screen_bezel(draw, w, h, style)
    bezel_color = style[5]
    draw.rectangle([15, 15, w - 15, h - 15], fill=bezel_color, outline=(20, 20, 20), width=2)

    # Screen area
    margin = 55
    screen_x, screen_y = margin, margin
    screen_w, screen_h = w - 2 * margin, h - 2 * margin

    # Draw LCD background inside screen area
    screen_bg = Image.new("RGB", (screen_w, screen_h), style[1])
    screen_draw = ImageDraw.Draw(screen_bg)
    generate_lcd_background(screen_draw, screen_w, screen_h, style)
    img.paste(screen_bg, (screen_x, screen_y))

    # Now draw content on the screen
    draw = ImageDraw.Draw(img, "RGBA")
    fg = style[2]
    off = style[3]
    label_c = style[4]

    # Device model text at top
    try:
        from PIL import ImageFont
        label_font = ImageFont.truetype("arial.ttf", 18) if Path("C:/Windows/Fonts/arial.ttf").exists() else ImageFont.load_default()
    except Exception:
        label_font = ImageFont.load_default()

    # Top labels
    draw.text((screen_x + 15, screen_y + 8), "HEALTH AGENT", fill=label_c, font=label_font)

    # Time display
    hour = random.randint(8, 22)
    minute = random.randint(0, 59)
    time_str = f"{hour:02d}:{minute:02d}"
    draw.text((screen_x + screen_w - 80, screen_y + 8), time_str, fill=label_c, font=label_font)

    # --- SYS section ---
    sys_label_y = screen_y + 55
    draw.text((screen_x + 40, sys_label_y), "SYS", fill=label_c, font=label_font)
    draw_seven_seg_number(
        draw, screen_x + screen_w // 2 + 20, sys_label_y + 65,
        systolic, digit_w=48, digit_h=84, spacing=8, fg_color=fg, off_color=off
    )
    draw.text((screen_x + screen_w - 100, sys_label_y + 90), "mmHg", fill=label_c, font=label_font)

    # --- DIA section ---
    dia_label_y = screen_y + 210
    draw.text((screen_x + 40, dia_label_y), "DIA", fill=label_c, font=label_font)
    draw_seven_seg_number(
        draw, screen_x + screen_w // 2 + 20, dia_label_y + 65,
        diastolic, digit_w=48, digit_h=84, spacing=8, fg_color=fg, off_color=off
    )
    draw.text((screen_x + screen_w - 100, dia_label_y + 90), "mmHg", fill=label_c, font=label_font)

    # --- PULSE section ---
    pul_label_y = screen_y + 365
    draw.text((screen_x + 40, pul_label_y), "PUL", fill=label_c, font=label_font)
    draw_seven_seg_number(
        draw, screen_x + screen_w // 2 + 20, pul_label_y + 50,
        heart_rate, digit_w=42, digit_h=74, spacing=6, fg_color=fg, off_color=off
    )
    draw.text((screen_x + screen_w - 100, pul_label_y + 65), "bpm", fill=label_c, font=label_font)

    # Heart icon
    heart_x = screen_x + screen_w - 70
    heart_y = pul_label_y + 25
    draw.text((heart_x, heart_y), "♥", fill=(200, 60, 60, 200) if hasattr(draw, 'text') else (200, 60, 60),
              font=label_font)

    # Separator lines
    draw.line([(screen_x + 20, screen_y + 190), (screen_x + screen_w - 20, screen_y + 190)],
              fill=label_c, width=1)
    draw.line([(screen_x + 20, screen_y + 345), (screen_x + screen_w - 20, screen_y + 345)],
              fill=label_c, width=1)

    # Bottom status
    draw.text((screen_x + 15, screen_y + screen_h - 25), "● REC", fill=(200, 50, 50), font=label_font)

    # -------------------------------------------------------------------
    # Post-processing: apply rotation, glare, camera artifacts
    # -------------------------------------------------------------------

    # Slight rotation (simulating hand-held shot)
    if "rotation" in effects:
        angle = random.uniform(-3.0, 3.0)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(30, 30, 30))

    # Add glare
    img = add_glare(img, glare_type)

    # Camera artifacts
    if "noise" in effects or "blur" in effects or "darken" in effects or "brighten" in effects:
        img = simulate_camera_artifacts(img)

    # Save
    fname = f"{index + 1:03d}.png"
    out_path = OUT_DIR / fname
    img.save(out_path, "PNG")
    return fname


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    test_cases = generate_test_cases()
    new_labels = []

    for i, (sys_val, dia_val, hr_val, glare_type, effects) in enumerate(test_cases):
        style = SCREEN_STYLES[i % len(SCREEN_STYLES)]
        note_parts = [f"style={style[0]}", f"glare={glare_type}"]
        if effects:
            note_parts.append(f"effects={effects}")
        note = "LCD 电子血压计实拍 - " + " | ".join(note_parts)

        fname = generate_image(i, sys_val, dia_val, hr_val, style, glare_type, effects, note)
        entry = {
            "file": fname,
            "systolic": sys_val,
            "diastolic": dia_val,
            "heart_rate": hr_val,
            "source": "synthetic",
            "note": note,
        }
        new_labels.append(entry)
        print(f"  Generated {fname}: {sys_val}/{dia_val}/{hr_val} ({style[0]}, glare={glare_type}, effects={effects})")

    # Write new labels (replacing old file entirely, starting from 001)
    with open(LABELS, "w", encoding="utf-8") as f:
        json.dump(new_labels, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {len(new_labels)} entries written to labels.json.")


if __name__ == "__main__":
    main()
