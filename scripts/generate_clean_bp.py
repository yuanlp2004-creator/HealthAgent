"""
Generate clean printed-digit BP images (non-seven-segment LCD).
These represent smartphone app screens, computer displays, and printed labels
where traditional OCR should work well.
"""
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

OUT_DIR = Path("datasets/bp_clean")
LABELS = OUT_DIR / "labels.json"
IMG_W, IMG_H = 800, 600

TEST_CASES = [
    (118, 76, 72, "smartphone_dark", "手机App深色模式截图"),
    (132, 85, 68, "smartphone_light", "手机App浅色模式截图"),
    (145, 92, 80, "computer_dashboard", "电脑端看板截图"),
    (110, 65, 58, "printed_label", "打印的体检标签"),
    (155, 98, 88, "tablet_app", "平板App测量结果页"),
    (125, 80, 75, "medical_device_dotmatrix", "医用点阵屏设备"),
    (138, 87, 93, "smartphone_dark", "手机App深色-运动后测量"),
    (102, 60, 62, "computer_dashboard", "电脑端历史记录页"),
    (148, 95, 84, "printed_label", "药房自助机打印小票"),
    (128, 78, 70, "tablet_app", "平板App周报摘要"),
]

STYLES = {
    "smartphone_dark": {
        "bg": (30, 30, 35),
        "card_bg": (50, 50, 58),
        "fg": (240, 240, 245),
        "accent": (80, 160, 255),
        "secondary": (160, 160, 170),
        "danger": (255, 80, 80),
    },
    "smartphone_light": {
        "bg": (240, 242, 245),
        "card_bg": (255, 255, 255),
        "fg": (25, 25, 30),
        "accent": (60, 140, 240),
        "secondary": (140, 140, 150),
        "danger": (230, 60, 60),
    },
    "computer_dashboard": {
        "bg": (245, 247, 250),
        "card_bg": (255, 255, 255),
        "fg": (20, 25, 35),
        "accent": (40, 120, 220),
        "secondary": (130, 135, 145),
        "danger": (220, 50, 50),
    },
    "printed_label": {
        "bg": (252, 250, 245),
        "card_bg": (255, 253, 248),
        "fg": (15, 15, 15),
        "accent": (30, 30, 30),
        "secondary": (100, 100, 100),
        "danger": (180, 30, 30),
    },
    "tablet_app": {
        "bg": (20, 25, 40),
        "card_bg": (35, 40, 55),
        "fg": (220, 225, 240),
        "accent": (100, 200, 150),
        "secondary": (140, 145, 165),
        "danger": (255, 100, 100),
    },
    "medical_device_dotmatrix": {
        "bg": (10, 15, 10),
        "card_bg": (15, 20, 15),
        "fg": (180, 220, 180),
        "accent": (220, 240, 100),
        "secondary": (100, 140, 100),
        "danger": (240, 180, 60),
    },
}


def get_font(size):
    paths = [
        f"C:/Windows/Fonts/msyh.ttc",
        f"C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def add_noise(img, intensity=5):
    arr = np.array(img).astype("int16")
    noise = np.random.normal(0, intensity, arr.shape).astype("int16")
    arr = np.clip(arr + noise, 0, 255).astype("uint8")
    return Image.fromarray(arr)


def apply_camera_effect(img):
    """Subtle camera effects — much milder than LCD photos."""
    effects = []
    if random.random() < 0.5:
        arr = np.array(img).astype("int16")
        noise = np.random.normal(0, random.uniform(2, 6), arr.shape).astype("int16")
        arr = np.clip(arr + noise, 0, 255).astype("uint8")
        img = Image.fromarray(arr)
        effects.append("noise")
    if random.random() < 0.3:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))
        effects.append("blur")
    if random.random() < 0.3:
        factor = random.uniform(0.8, 1.25)
        img = ImageEnhance.Brightness(img).enhance(factor)
        effects.append("brightness")
    return img, effects


def draw_card(draw, x, y, w, h, style):
    """Rounded card with shadow."""
    shadow_off = 3
    draw.rounded_rectangle(
        [x + shadow_off, y + shadow_off, x + w + shadow_off, y + h + shadow_off],
        radius=12, fill=(0, 0, 0, 40) if hasattr(draw, 'rounded_rectangle') else None
    )
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=style["card_bg"],
                           outline=style["secondary"], width=1)


def generate_image(index, systolic, diastolic, heart_rate, style_name, desc):
    """Generate a clean, standard-font BP display image."""
    style = STYLES[style_name]
    img = Image.new("RGB", (IMG_W, IMG_H), style["bg"])
    draw = ImageDraw.Draw(img, "RGBA" if hasattr(ImageDraw.Draw(img), 'rounded_rectangle') else "RGB")

    title_font = get_font(28)
    big_font = get_font(64)
    mid_font = get_font(36)
    small_font = get_font(20)
    tiny_font = get_font(16)

    # Header bar (phone-style)
    header_h = 44
    draw.rectangle([0, 0, IMG_W, header_h], fill=style["card_bg"])
    draw.text((20, 10), "HealthAgent", fill=style["accent"], font=title_font)
    draw.text((IMG_W - 80, 12), f"{random.randint(9,22):02d}:{random.randint(0,59):02d}", fill=style["secondary"], font=small_font)

    # Title
    title_y = header_h + 25
    draw.text((30, title_y), "血压测量结果", fill=style["fg"], font=title_font)
    draw.text((30, title_y + 35), "Blood Pressure Reading", fill=style["secondary"], font=tiny_font)

    # Main card
    card_x, card_y = 40, title_y + 75
    card_w, card_h = IMG_W - 80, 320

    if hasattr(draw, 'rounded_rectangle'):
        draw_card(draw, card_x, card_y, card_w, card_h, style)
    else:
        draw.rectangle([card_x, card_y, card_x + card_w, card_y + card_h],
                       fill=style["card_bg"], outline=style["secondary"], width=1)

    # SYS
    sys_x = card_x + 60
    sys_y = card_y + 40
    draw.text((sys_x, sys_y), "收缩压 SYS", fill=style["secondary"], font=small_font)
    draw.text((sys_x, sys_y + 30), str(systolic), fill=style["fg"], font=big_font)
    draw.text((sys_x + len(str(systolic)) * 38 + 10, sys_y + 52), "mmHg", fill=style["secondary"], font=mid_font)

    # Divider
    div_y = sys_y + 115
    draw.line([(card_x + 40, div_y), (card_x + card_w - 40, div_y)], fill=style["secondary"], width=1)

    # DIA
    dia_y = div_y + 20
    draw.text((sys_x, dia_y), "舒张压 DIA", fill=style["secondary"], font=small_font)
    draw.text((sys_x, dia_y + 30), str(diastolic), fill=style["fg"], font=big_font)
    draw.text((sys_x + len(str(diastolic)) * 38 + 10, dia_y + 52), "mmHg", fill=style["secondary"], font=mid_font)

    # HR on the right side
    hr_x = card_x + card_w - 200
    hr_y = card_y + 60
    draw.text((hr_x, hr_y), "心率", fill=style["secondary"], font=small_font)
    draw.text((hr_x, hr_y + 30), str(heart_rate), fill=style["danger"], font=big_font)
    draw.text((hr_x + len(str(heart_rate)) * 38 + 10, hr_y + 52), "bpm", fill=style["secondary"], font=mid_font)

    # Heart icon
    heart_x = hr_x - 45
    draw.text((heart_x, hr_y + 28), "♥", fill=style["danger"], font=ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 48)
              if Path("C:/Windows/Fonts/segoeui.ttf").exists() else mid_font)

    # Bottom info
    info_y = card_y + card_h + 20
    draw.text((30, info_y), f"测量时间: 2026-05-0{random.randint(1,5)} {random.randint(8,22):02d}:{random.randint(0,59):02d}", fill=style["secondary"], font=small_font)
    draw.text((30, info_y + 30), f"设备: HAG-{random.randint(100,999)} | 用户: 张**", fill=style["secondary"], font=small_font)

    # Bottom nav bar (phone-style)
    nav_y = IMG_H - 50
    draw.rectangle([0, nav_y, IMG_W, IMG_H], fill=style["card_bg"])
    nav_items = ["首页", "测量", "趋势", "我的"]
    for i, item in enumerate(nav_items):
        cx = IMG_W * (i + 0.5) / 4
        color = style["accent"] if i == 1 else style["secondary"]
        draw.text((cx - 20, nav_y + 15), item, fill=color, font=small_font)

    # Apply subtle camera effect
    img, effects = apply_camera_effect(img)

    # Save
    fname = f"clean_{index + 1:03d}.png"
    out_path = OUT_DIR / fname
    img.save(out_path, "PNG")
    return fname, effects


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    new_labels = []
    for i, (sys_val, dia_val, hr_val, style_name, desc) in enumerate(TEST_CASES):
        fname, effects = generate_image(i, sys_val, dia_val, hr_val, style_name, desc)
        entry = {
            "file": fname,
            "systolic": sys_val,
            "diastolic": dia_val,
            "heart_rate": hr_val,
            "source": "synthetic_clean",
            "note": f"{desc} | style={style_name} | effects={effects}",
        }
        new_labels.append(entry)
        print(f"  Generated {fname}: {sys_val}/{dia_val}/{hr_val} ({style_name})")

    with open(LABELS, "w", encoding="utf-8") as f:
        json.dump(new_labels, f, ensure_ascii=False, indent=2)
    print(f"\nDone. {len(new_labels)} entries in labels.json.")


if __name__ == "__main__":
    main()
