import os
import sys
import time
import json
import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from models.efficientnet_engine import predict_deep_learning

def create_synthetic_test_dataset(dataset_dir):
    """Generates synthetic benchmark test dataset if custom test image folder is not provided."""
    real_dir = os.path.join(dataset_dir, "test", "real")
    ai_dir = os.path.join(dataset_dir, "test", "ai")
    os.makedirs(real_dir, exist_ok=True)
    os.makedirs(ai_dir, exist_ok=True)

    # Generate test images if empty
    if not os.listdir(real_dir):
        for i in range(10):
            img = Image.fromarray(np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8))
            img.save(os.path.join(real_dir, f"real_test_{i+1}.jpg"))
    if not os.listdir(ai_dir):
        for i in range(10):
            img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
            img.save(os.path.join(ai_dir, f"ai_test_{i+1}.jpg"))

    return real_dir, ai_dir

def evaluate():
    print("==================================================")
    print("DEEPSHIELD PRETRAINED AI DETECTOR EVALUATION SUITE")
    print("==================================================")

    dataset_dir = os.path.join(PROJECT_ROOT, "dataset")
    real_dir, ai_dir = create_synthetic_test_dataset(dataset_dir)

    real_files = [os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    ai_files = [os.path.join(ai_dir, f) for f in os.listdir(ai_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    y_true = []
    y_pred = []
    y_scores = []
    latencies = []

    print(f"Evaluating {len(real_files)} Real images and {len(ai_files)} AI images...")

    for filepath in real_files:
        res = predict_deep_learning(filepath)
        ai_prob = res['ai_prob']
        pred_label = 1 if ai_prob >= 0.5 else 0
        y_true.append(0)
        y_pred.append(pred_label)
        y_scores.append(ai_prob)
        latencies.append(res['inference_time_ms'])

    for filepath in ai_files:
        res = predict_deep_learning(filepath)
        ai_prob = res['ai_prob']
        pred_label = 1 if ai_prob >= 0.5 else 0
        y_true.append(1)
        y_pred.append(pred_label)
        y_scores.append(ai_prob)
        latencies.append(res['inference_time_ms'])

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    try:
        auc = float(roc_auc_score(y_true, y_scores))
    except Exception:
        auc = 0.5

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)
    avg_latency = float(np.mean(latencies)) if latencies else 0.0

    eval_results = {
        "model_architecture": "Pretrained AI Image Detector (Hugging Face / EfficientNet-B4)",
        "benchmark_dataset": f"DeepShield Test Benchmark ({len(real_files)} Real / {len(ai_files)} AI)",
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "avg_inference_time_ms": round(avg_latency, 2),
        "confusion_matrix": {
            "true_positive_ai": int(tp),
            "false_negative_real": int(fn),
            "false_positive_ai": int(fp),
            "true_negative_real": int(tn)
        },
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    out_path = os.path.join(PROJECT_ROOT, "models", "evaluation_results.json")
    with open(out_path, "w") as f:
        json.dump(eval_results, f, indent=4)

    print("\n--- EVALUATION RESULTS ---")
    print(json.dumps(eval_results, indent=4))
    print(f"\nSaved evaluation metrics to {out_path}")

if __name__ == "__main__":
    evaluate()
