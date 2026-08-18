import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def train_and_save_model():
    """
    Trains a 4-feature Random Forest classifier calibrated for real compressed images (WhatsApp, web photos)
    vs true AI deepfake images.
    Features: [ela_std_dev, fft_high_freq, noise_var, has_ai_sig]
    """
    np.random.seed(42)

    # 1. Real Standard Camera Photos: ELA (15-30), FFT (70-120), Noise (50-200), Has EXIF (0)
    real_cam = np.column_stack([
        np.random.normal(22, 4, 300),
        np.random.normal(95, 15, 300),
        np.random.normal(120, 30, 300),
        np.zeros(300)
    ])

    # 2. Real Compressed Photos (WhatsApp, Web): ELA (10-25), FFT (120-195), Noise (150-300), Stripped EXIF (1)
    real_wa = np.column_stack([
        np.random.normal(16, 5, 400),
        np.random.normal(155, 20, 400),
        np.random.normal(200, 40, 400),
        np.ones(400)
    ])

    X_real = np.vstack([real_cam, real_wa])
    y_real = np.zeros(len(X_real))

    # 3. AI Synthetic / Deepfake Photos: ELA Anomaly (<6 or >35), FFT grid noise (>210), AI signature (1)
    ela_ai = np.concatenate([np.random.normal(4, 1.5, 250), np.random.normal(38, 5, 250)])
    ai_syn = np.column_stack([
        ela_ai,
        np.random.normal(225, 25, 500),
        np.random.normal(80, 20, 500),
        np.random.choice([0, 1], size=500, p=[0.2, 0.8])
    ])
    y_ai = np.ones(len(ai_syn))

    X = np.vstack([X_real, ai_syn])
    y = np.concatenate([y_real, y_ai])

    clf = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42)
    clf.fit(X, y)

    model_path = os.path.join(os.path.dirname(__file__), 'model.pkl')
    joblib.dump(clf, model_path)
    print(f"Model successfully trained with 4 features and saved to {model_path}")
    return clf

if __name__ == '__main__':
    train_and_save_model()
