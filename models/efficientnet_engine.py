import os
import time
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Global Model Singleton
EFFICIENTNET_MODEL = None
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ImageNet Preprocessing Transformations
TRANSFORMS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

class DeepShieldEfficientNet(nn.Module):
    """
    Research-Grade EfficientNet-B0 Binary Classification & Feature Extractor Architecture.
    """
    def __init__(self):
        super(DeepShieldEfficientNet, self).__init__()
        # Load Pretrained EfficientNet-B0 backbone
        base_model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        self.features = base_model.features
        self.avgpool = base_model.avgpool
        
        # Binary Classifier Head for AI Synthetic vs Real Detection
        in_features = base_model.classifier[1].in_features
        self.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(256, 2)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        out = self.classifier(x)
        return out

def get_efficientnet_model():
    """Initializes and returns global singleton EfficientNet-B0 model."""
    global EFFICIENTNET_MODEL
    if EFFICIENTNET_MODEL is None:
        model = DeepShieldEfficientNet()
        model.eval()
        model.to(DEVICE)
        EFFICIENTNET_MODEL = model
        print(f"EfficientNet-B0 Deep Learning Model initialized on device: {DEVICE}")
    return EFFICIENTNET_MODEL

def predict_deep_learning(image_path):
    """
    Runs EfficientNet-B0 deep learning inference on an input image.
    Returns prediction probabilities, AI confidence, and inference latency.
    """
    start_time = time.time()
    model = get_efficientnet_model()
    
    try:
        img = Image.open(image_path).convert('RGB')
        tensor_img = TRANSFORMS(img).unsqueeze(0).to(DEVICE)
        
        with torch.no_grad():
            outputs = model(tensor_img)
            probabilities = torch.softmax(outputs, dim=1)[0]
            
            # Index 1 = AI Synthetic Probability, Index 0 = Real Image Probability
            ai_prob = float(probabilities[1].item())
            real_prob = float(probabilities[0].item())
            
        inference_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
        
        return {
            "ai_prob": ai_prob,
            "real_prob": real_prob,
            "inference_time_ms": inference_time
        }
    except Exception as e:
        print("EfficientNet Prediction Error:", e)
        return {
            "ai_prob": 0.5,
            "real_prob": 0.5,
            "inference_time_ms": round((time.time() - start_time) * 1000, 2)
        }
