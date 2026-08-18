import os
import hashlib
import urllib.request
from models.efficientnet_engine import predict_deep_learning
from utils.forensics import run_full_forensic_suite
from utils.gradcam import generate_gradcam_visualization
from utils.authenticity_score import calculate_authenticity_score
from utils.source_attribution import attribute_ai_source
from utils.db import log_scan, get_scan_by_id, get_recent_scans, clear_scans
from utils.pdf_generator import build_pdf_report

def calculate_file_hash(file_path):
    """Calculates SHA-256 hash of image file for duplicate detection."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def download_image_from_url(url, save_path):
    """Downloads image from URL with User-Agent header."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=12) as response, open(save_path, 'wb') as out_file:
        out_file.write(response.read())

def analyze_image(image_path, static_reports_dir):
    """
    Master research forensic pipeline execution:
    1. SHA-256 Hashing & Preprocessing
    2. PyTorch EfficientNet-B0 Deep Learning Inference
    3. 8-Module Multi-Signal Forensic Extraction (ELA, FFT, Noise, EXIF, etc.)
    4. Grad-CAM Spatial Activation Saliency Map Generation
    5. Weighted 0-100% Authenticity Score Calculation
    6. AI Generative Source Attribution
    7. Database Logging via SQLite Context Managers
    """
    filename = os.path.basename(image_path)
    file_hash = calculate_file_hash(image_path)

    # 1. PyTorch EfficientNet-B0 Deep Learning Inference
    dl_result = predict_deep_learning(image_path)
    ai_prob = dl_result['ai_prob']
    inference_time = dl_result['inference_time_ms']

    # 2. Run 8 Forensic Signal Modules
    forensic_results = run_full_forensic_suite(image_path, static_reports_dir)

    # 3. Grad-CAM Spatial Heatmap Saliency
    gradcam_url, gradcam_explanation = generate_gradcam_visualization(
        image_path,
        static_reports_dir,
        forensic_results['ela_std_dev'],
        forensic_results['fft_freq']
    )

    # 4. Unified Authenticity Score Calculation
    auth_data = calculate_authenticity_score(
        ai_prob=ai_prob,
        ela_std=forensic_results['ela_std_dev'],
        fft_freq=forensic_results['fft_freq'],
        noise_var=forensic_results['noise_var'],
        has_ai_sig=forensic_results['has_ai_sig']
    )

    is_ai = not auth_data['is_real']
    result_label = "AI Generated / Synthetic" if is_ai else "Real Authentic Image"
    confidence_str = f"{auth_data['authenticity_score']}%"

    # 5. AI Source Attribution
    source_attribution, source_confidence = attribute_ai_source(
        forensic_results['meta_flags'],
        forensic_results['fft_freq'],
        forensic_results['ela_std_dev'],
        is_ai
    )

    # 6. SQLite Database Record Logging
    scan_id = log_scan(
        filename=filename,
        file_hash=file_hash,
        result=result_label,
        confidence=confidence_str,
        auth_score=auth_data['authenticity_score'],
        source_attr=source_attribution,
        inf_time=inference_time,
        is_ai=is_ai,
        ela_std=forensic_results['ela_std_dev'],
        fft_freq=forensic_results['fft_freq'],
        noise_var=forensic_results['noise_var'],
        sharpness=forensic_results['sharpness'],
        gradcam_path=gradcam_url,
        ela_path=forensic_results['ela_path'],
        fft_path=forensic_results['fft_path']
    )

    return {
        "scan_id": scan_id,
        "file_hash": file_hash,
        "filename": filename,
        "result": result_label,
        "confidence": confidence_str,
        "authenticity_score": auth_data['authenticity_score'],
        "authenticity_label": auth_data['label'],
        "authenticity_explanation": auth_data['explanation'],
        "source_attribution": source_attribution,
        "inference_time_ms": inference_time,
        "is_ai": is_ai,
        "gradcam_url": gradcam_url,
        "gradcam_explanation": gradcam_explanation,
        "ela_url": forensic_results['ela_path'],
        "fft_url": forensic_results['fft_path'],
        "ela_std_dev": forensic_results['ela_std_dev'],
        "fft_freq": forensic_results['fft_freq'],
        "noise_var": forensic_results['noise_var'],
        "jpeg_ratio": forensic_results['jpeg_ratio'],
        "edge_density": forensic_results['edge_density'],
        "color_entropy": forensic_results['color_entropy'],
        "sharpness": forensic_results['sharpness'],
        "metadata_flags": forensic_results['meta_flags']
    }

def generate_pdf_for_scan(scan_id, uploads_dir, reports_dir):
    """Fetches scan record and generates PDF research audit report."""
    scan = get_scan_by_id(scan_id)
    if not scan:
        return None

    pdf_filename = f"deepshield_report_{scan_id}.pdf"
    pdf_path = os.path.join(reports_dir, pdf_filename)

    scan_dict = dict(scan)
    scan_dict['abs_image_path'] = os.path.join(uploads_dir, scan_dict['filename'])
    if scan_dict.get('gradcam_path'):
        scan_dict['abs_gradcam_path'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), scan_dict['gradcam_path'].lstrip('/'))
    if scan_dict.get('ela_path'):
        scan_dict['abs_ela_path'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), scan_dict['ela_path'].lstrip('/'))

    build_pdf_report(scan_dict, pdf_path)
    return pdf_path
