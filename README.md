# DeepShield — Production AI Image Forensics & Deepfake Detection Platform

DeepShield is an enterprise-grade AI forensic system designed for detecting synthetic AI media, GAN artifacts, diffusion patterns, and image tampering using PyTorch EfficientNet-B0 deep learning and an 8-module multi-signal physical forensic suite.

---

## 🌟 Key Architecture & Features

* **Deep Learning Engine**: PyTorch EfficientNet-B0 (`torchvision.models.efficientnet_b0`) initialized as an in-memory singleton.
* **Explainable AI (Grad-CAM)**: Generates spatial feature saliency maps overlaid with JET colormap.
* **8 Parallel Forensic Modules**:
  1. Error Level Analysis (ELA)
  2. 2D Fourier Spectrum (FFT)
  3. Laplacian Noise Floor Variance
  4. Tenengrad Gradient Sharpness Metric
  5. JPEG 8x8 Block Discontinuity Ratio
  6. Canny Edge Texture Density
  7. RGB Color Histogram Entropy
  8. EXIF Provenance & Metadata Signals
* **Parallel Execution Engine**: `concurrent.futures.ThreadPoolExecutor` runs forensic modules concurrently for low latency.
* **Weighted Authenticity Score Gauge**: Unified $0\% - 100\%$ score rating.
* **REST API Endpoint (`/api/analyze`)**: HTTP POST endpoint returning JSON detection payloads.
* **Batch Multi-Image Upload (`/batch-upload`)**: Upload and process multiple files concurrently.
* **PDF Audit Report Generator**: ReportLab PDF document compilation (`/report/<id>`).
* **SQLite Persistence**: Thread-safe database with Write-Ahead Logging (WAL) and indexing.

---

## 🚀 Quick Start Guide

### 1. Installation & Setup
```bash
# Clone repository
git clone https://github.com/your-org/DeepShield.git
cd DeepShield

# Activate Virtual Environment & Install Dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Launch Development Server
```bash
python app.py
```
App will start on `http://127.0.0.1:5000`.

---

## 📡 REST API Documentation

### Analyze Image Endpoint (`/api/analyze`)

- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Payload Field**: `image` (binary file)

#### Example cURL Request:
```bash
curl -X POST http://127.0.0.1:5000/api/analyze \
  -F "image=@/path/to/sample_image.jpg"
```

#### Example JSON Response Payload:
```json
{
  "status": "success",
  "scan_id": 1,
  "filename": "sample_image.jpg",
  "prediction": "Real Authentic Image",
  "confidence": "60.0%",
  "authenticity_score": 60.0,
  "source_attribution": "Not Applicable (Real Media)",
  "inference_time_ms": 42.5,
  "is_ai": false,
  "gradcam_url": "/static/reports/gradcam_sample_image.jpg",
  "forensic_summary": {
    "ela_std_dev": 3.31,
    "fft_high_freq": 120.22,
    "noise_var": 107.9,
    "tenengrad_sharpness": 321.09,
    "jpeg_block_ratio": 1.04,
    "canny_edge_density_pct": 7.82,
    "rgb_channel_entropy": 7.45,
    "metadata_flags": [
      "No camera EXIF metadata present (Compressed or Web media)"
    ]
  }
}
```

---

## 📦 Batch Upload Workflow (`/batch-upload`)

1. Navigate to `http://127.0.0.1:5000/batch-upload`.
2. Select multiple images via file dialog.
3. DeepShield processes each image in parallel threads via `ThreadPoolExecutor`.
4. Review the batch summary table with predictions, confidence scores, authenticity scores, and PDF report download links.
