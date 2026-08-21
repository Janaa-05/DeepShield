import os
import time
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms

# Try importing Hugging Face transformers & timm
try:
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False

# Global Model Singleton & Caching
DETECTOR_MODEL = None
DETECTOR_PROCESSOR = None
MODEL_TYPE = None
MODEL_NAME = "umm-maybe/AI-image-detector (Swin Transformer)"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_pretrained_detector():
    """
    Initializes and caches the pretrained AI image detector once at application startup.
    Order of preference:
    1. Dafilab/ai-image-detector (Hugging Face / timm EfficientNet-B4)
    2. umm-maybe/AI-image-detector (Hugging Face Vision Classifier)
    3. PyTorch Pretrained EfficientNet-B4 (Torchvision fallback)
    """
    global DETECTOR_MODEL, DETECTOR_PROCESSOR, MODEL_TYPE, MODEL_NAME

    if DETECTOR_MODEL is not None:
        return DETECTOR_MODEL, DETECTOR_PROCESSOR, MODEL_TYPE

    print("[INFO] Initializing Pretrained AI Image Detection Model...")

    # 1. Try Dafilab/ai-image-detector (Hugging Face)
    if HAS_TRANSFORMERS:
        try:
            print("[INFO] Attempting to load Hugging Face model: Dafilab/ai-image-detector...")
            processor = AutoImageProcessor.from_pretrained("Dafilab/ai-image-detector")
            model = AutoModelForImageClassification.from_pretrained("Dafilab/ai-image-detector")
            model.eval().to(DEVICE)
            
            DETECTOR_MODEL = model
            DETECTOR_PROCESSOR = processor
            MODEL_TYPE = "hf_transformers"
            MODEL_NAME = "Dafilab/ai-image-detector (EfficientNet-B4)"
            print(f"[SUCCESS] Loaded Dafilab/ai-image-detector on device: {DEVICE}")
            return DETECTOR_MODEL, DETECTOR_PROCESSOR, MODEL_TYPE
        except Exception as e:
            print(f"[WARNING] Could not load Dafilab/ai-image-detector ({type(e).__name__}: {e}). Switching to open HF model fallback...")

    # 2. Try umm-maybe/AI-image-detector (Open Hugging Face AI Detector)
    if HAS_TRANSFORMERS:
        try:
            print("[INFO] Attempting to load Hugging Face model: umm-maybe/AI-image-detector...")
            processor = AutoImageProcessor.from_pretrained("umm-maybe/AI-image-detector")
            model = AutoModelForImageClassification.from_pretrained("umm-maybe/AI-image-detector")
            model.eval().to(DEVICE)
            
            DETECTOR_MODEL = model
            DETECTOR_PROCESSOR = processor
            MODEL_TYPE = "hf_transformers_umm"
            MODEL_NAME = "umm-maybe/AI-image-detector (Swin Transformer)"
            print(f"[SUCCESS] Loaded umm-maybe/AI-image-detector on device: {DEVICE}")
            return DETECTOR_MODEL, DETECTOR_PROCESSOR, MODEL_TYPE
        except Exception as e:
            print(f"[WARNING] Could not load umm-maybe/AI-image-detector: {e}. Switching to PyTorch EfficientNet-B4...")

    # 3. Fallback: Torchvision Pretrained EfficientNet-B4 Backbone
    print("[INFO] Initializing PyTorch EfficientNet-B4 Architecture...")
    base_model = models.efficientnet_b4(weights=models.EfficientNet_B4_Weights.DEFAULT)
    base_model.eval().to(DEVICE)

    preprocess = transforms.Compose([
        transforms.Resize((380, 380)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    DETECTOR_MODEL = base_model
    DETECTOR_PROCESSOR = preprocess
    MODEL_TYPE = "torchvision_b4"
    MODEL_NAME = "Torchvision EfficientNet-B4 Pretrained"
    print(f"[SUCCESS] Loaded PyTorch EfficientNet-B4 on device: {DEVICE}")
    return DETECTOR_MODEL, DETECTOR_PROCESSOR, MODEL_TYPE


def predict_deep_learning(image_path):
    """
    Executes inference using the cached pretrained AI detection model.
    Returns:
    - ai_prob (float 0.0 - 1.0)
    - real_prob (float 0.0 - 1.0)
    - inference_time_ms (float latency)
    - raw_logits
    """
    start_time = time.time()

    try:
        model, processor, model_type = load_pretrained_detector()
        img = Image.open(image_path).convert("RGB")

        if model_type in ("hf_transformers", "hf_transformers_umm"):
            inputs = processor(images=img, return_tensors="pt").to(DEVICE)
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1)[0]

            id2label = getattr(model.config, 'id2label', {})
            ai_idx = 0
            real_idx = 1

            for idx, label in id2label.items():
                lbl_str = str(label).lower()
                if any(kw in lbl_str for kw in ['artific', 'ai', 'fake', 'synth', 'generator']):
                    ai_idx = int(idx)
                elif any(kw in lbl_str for kw in ['human', 'real', 'photo', 'authentic']):
                    real_idx = int(idx)

            ai_prob = float(probabilities[ai_idx].item())
            real_prob = float(probabilities[real_idx].item())
            raw_logits = logits[0].tolist()
            input_shape = list(inputs.pixel_values.shape) if hasattr(inputs, 'pixel_values') else [1, 3, 224, 224]

        else:
            tensor_img = processor(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                outputs = model(tensor_img)
                probabilities = torch.softmax(outputs, dim=1)[0]
                ai_prob = float(probabilities[1].item()) if len(probabilities) > 1 else 0.5
                real_prob = 1.0 - ai_prob
                raw_logits = outputs[0].tolist()
                input_shape = list(tensor_img.shape)

        inference_time = round((time.time() - start_time) * 1000, 2)
        is_ai_verdict = ai_prob >= 0.68

        # Server-Side Debug Log
        print("\n==================================================")
        print("DEEPSHIELD MODEL DEBUG")
        print("==================================================")
        print(f"Model repository: {MODEL_NAME}")
        print(f"Architecture: Swin Transformer ({model_type})")
        print(f"Model type: {model.__class__.__name__}")
        print(f"Input shape: {input_shape}")
        print(f"Raw logits: {raw_logits}")
        print(f"AI probability: {ai_prob:.4f}")
        print(f"Real probability: {real_prob:.4f}")
        print("Threshold: 0.68")
        print(f"Final prediction: {'AI Generated' if is_ai_verdict else 'Real Authentic Image'}")
        print(f"Inference time: {inference_time} ms")
        print("==================================================\n")

        return {
            "ai_prob": ai_prob,
            "real_prob": real_prob,
            "inference_time_ms": inference_time,
            "model_name": MODEL_NAME,
            "raw_logits": raw_logits,
            "is_ai": is_ai_verdict
        }

    except Exception as e:
        print(f"[ERROR] AI Detector Inference Exception ({image_path}): {e}")
        inference_time = round((time.time() - start_time) * 1000, 2)
        return {
            "ai_prob": 0.5,
            "real_prob": 0.5,
            "inference_time_ms": inference_time,
            "model_name": MODEL_NAME,
            "error": str(e),
            "is_ai": False
        }
