"""
Train a lightweight LCD vs non-LCD classifier using HOG + SVM.
No deep learning framework required — OpenCV + sklearn only.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import cv2
import numpy as np
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "datasets"
LCD_DIR = DATASET_ROOT / "bp_images"
CLEAN_DIR = DATASET_ROOT / "bp_clean"
MODEL_DIR = ROOT / "backend" / "app" / "services" / "ocr"
MODEL_PATH = MODEL_DIR / "lcd_classifier.pkl"

IMG_SIZE = (128, 128)


def extract_features(img_bgr: np.ndarray) -> np.ndarray:
    """Extract HOG + color features from BGR image."""
    img = cv2.resize(img_bgr, IMG_SIZE)

    # --- HOG features (captures edge/texture differences) ---
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hog = cv2.HOGDescriptor(
        _winSize=(128, 128),
        _blockSize=(16, 16),
        _blockStride=(8, 8),
        _cellSize=(8, 8),
        _nbins=9,
    )
    hog_feat = hog.compute(gray).flatten()

    # --- Color features (LCD = dark bg, clean = various) ---
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Mean & std per channel (BGR + HSV), 6 values
    color_feat = []
    for ch in cv2.split(img):
        color_feat.extend([np.mean(ch), np.std(ch)])
    for ch in cv2.split(hsv):
        color_feat.extend([np.mean(ch), np.std(ch)])

    # --- Brightness features (LCD typically darker) ---
    gray_flat = gray.flatten()
    brightness_feat = [
        np.percentile(gray_flat, 10),
        np.percentile(gray_flat, 50),
        np.percentile(gray_flat, 90),
        np.mean(gray),
    ]

    return np.concatenate([hog_feat, np.array(color_feat), np.array(brightness_feat)])


def load_dataset() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load all images, label LCD=1, non-LCD=0."""
    features = []
    labels = []
    filenames = []

    # LCD images (positive class)
    for p in sorted(LCD_DIR.glob("*.png")):
        img = cv2.imread(str(p))
        if img is None:
            print(f"  [WARN] cannot read {p}")
            continue
        features.append(extract_features(img))
        labels.append(1)
        filenames.append(f"LCD/{p.name}")

    # Clean/non-LCD images (negative class)
    for p in sorted(CLEAN_DIR.glob("*.png")):
        img = cv2.imread(str(p))
        if img is None:
            print(f"  [WARN] cannot read {p}")
            continue
        features.append(extract_features(img))
        labels.append(0)
        filenames.append(f"CLEAN/{p.name}")

    return np.array(features), np.array(labels), filenames


def main():
    print("Loading dataset...")
    X, y, filenames = load_dataset()
    print(f"  Total: {len(y)} images  (LCD={sum(y)}, Clean={len(y)-sum(y)})")

    # Normalize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train SVM with RBF kernel
    model = SVC(kernel="rbf", C=10.0, gamma="scale", probability=True, random_state=42)

    # Cross-validation (leave-one-out since dataset is small)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")
    print(f"  5-fold CV accuracy: {scores.mean():.1%} (+/- {scores.std():.1%})")

    # Train on full dataset
    model.fit(X_scaled, y)
    train_acc = model.score(X_scaled, y)
    print(f"  Training accuracy: {train_acc:.1%}")

    # Detailed per-sample prediction
    print("\nPer-sample predictions:")
    probs = model.predict_proba(X_scaled)
    for fname, true_label, prob in zip(filenames, y, probs):
        pred_label = int(prob[1] > 0.5)
        status = "OK" if pred_label == true_label else "XX"
        print(f"  [{status}] {fname:30s}  LCD_score={prob[1]:.4f}  true={true_label}")

    # Save model + scaler
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {"model": model, "scaler": scaler, "img_size": IMG_SIZE}
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"\nModel saved to {MODEL_PATH}")
    print(f"  Feature dim: {X.shape[1]}")


if __name__ == "__main__":
    main()
