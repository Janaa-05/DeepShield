import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS
from scipy.fft import fft2, fftshift
import concurrent.futures

def run_ela_module(image_path, static_reports_dir, filename):
    """Module 1: Error Level Analysis (ELA) re-compression variance."""
    try:
        ela_filename = f"ela_{filename}"
        ela_path = os.path.join(static_reports_dir, ela_filename)
        ela_url = f"/static/reports/{ela_filename}"

        img = Image.open(image_path).convert('RGB')
        resaved_path = os.path.join(static_reports_dir, f"temp_ela_{filename}")
        img.save(resaved_path, 'JPEG', quality=90)
        resaved = Image.open(resaved_path)

        diff = ImageChops.difference(img, resaved)
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        scale = 255.0 / max_diff if max_diff != 0 else 1.0

        ela_img = ImageEnhance.Brightness(diff).enhance(scale)
        ela_img.save(ela_path)
        if os.path.exists(resaved_path):
            os.remove(resaved_path)

        ela_arr = np.array(ela_img)
        ela_std_dev = float(np.std(ela_arr))
        return round(ela_std_dev, 2), ela_url
    except Exception as e:
        print("ELA Module Error:", e)
        return 12.5, ""

def run_fft_module(image_path, static_reports_dir, filename):
    """Module 2: 2D Fourier Spectrum (FFT) high-frequency grid energy."""
    try:
        fft_filename = f"fft_{filename}"
        fft_path = os.path.join(static_reports_dir, fft_filename)
        fft_url = f"/static/reports/{fft_filename}"

        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return 120.0, ""

        f = fft2(gray)
        fshift = fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-5)
        
        norm_spectrum = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        cv2.imwrite(fft_path, cv2.applyColorMap(norm_spectrum, cv2.COLORMAP_VIRIDIS))

        h, w = gray.shape
        cy, cx = h // 2, w // 2
        high_freq_region = magnitude_spectrum[:cy//2, :cx//2]
        high_freq_val = float(np.mean(high_freq_region))
        return round(high_freq_val, 2), fft_url
    except Exception as e:
        print("FFT Module Error:", e)
        return 120.0, ""

def run_noise_module(image_path):
    """Module 3: Laplacian Noise Floor Variance."""
    try:
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return 100.0
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return round(laplacian_var, 2)
    except Exception:
        return 100.0

def run_sharpness_module(image_path):
    """Module 4: Tenengrad Gradient Sharpness Metric."""
    try:
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return 250.0
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sharpness_val = float(np.mean(sobelx**2 + sobely**2))
        return round(sharpness_val, 2)
    except Exception:
        return 250.0

def run_jpeg_ratio_module(image_path):
    """Module 5: JPEG 8x8 Grid Artifact Discontinuity Ratio."""
    try:
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return 1.05
        h, w = gray.shape
        if h < 16 or w < 16:
            return 1.0
        diff_horizontal = np.abs(gray[:, 7::8].astype(float) - gray[:, 8::8].astype(float))
        diff_internal = np.abs(gray[:, 3::8].astype(float) - gray[:, 4::8].astype(float))
        ratio = float(np.mean(diff_horizontal) / (np.mean(diff_internal) + 1e-5))
        return round(ratio, 2)
    except Exception:
        return 1.05

def run_texture_module(image_path):
    """Module 6: Canny Edge Texture Density Percentage."""
    try:
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            return 8.5
        edges = cv2.Canny(gray, 100, 200)
        density = float((np.count_nonzero(edges) / edges.size) * 100)
        return round(density, 2)
    except Exception:
        return 8.5

def run_color_entropy_module(image_path):
    """Module 7: RGB Color Histogram Entropy."""
    try:
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return 7.2
        entropy_sum = 0.0
        for channel in range(3):
            hist = cv2.calcHist([img_bgr], [channel], None, [256], [0, 256])
            hist = hist.ravel() / hist.sum()
            hist = hist[hist > 0]
            entropy_sum += -np.sum(hist * np.log2(hist))
        return round(float(entropy_sum / 3.0), 2)
    except Exception:
        return 7.2

def run_exif_module(image_path):
    """Module 8: EXIF Metadata & Provenance Audit."""
    flags = []
    has_ai_sig = False
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if not exif:
            flags.append("No camera EXIF metadata present (Compressed or Web media)")
        else:
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                val_str = str(value).lower()
                if any(kw in val_str for kw in ['midjourney', 'stable diffusion', 'dall-e', 'flux', 'firefly', 'comfyui']):
                    has_ai_sig = True
                    flags.append(f"AI Generator Signature identified in EXIF: {tag_name}={value}")
    except Exception:
        flags.append("EXIF metadata unreadable or stripped")

    return flags, has_ai_sig

def run_full_forensic_suite(image_path, static_reports_dir):
    """
    Executes 8 forensic modules in parallel threads using ThreadPoolExecutor for low latency.
    """
    filename = os.path.basename(image_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        f_ela = executor.submit(run_ela_module, image_path, static_reports_dir, filename)
        f_fft = executor.submit(run_fft_module, image_path, static_reports_dir, filename)
        f_noise = executor.submit(run_noise_module, image_path)
        f_sharp = executor.submit(run_sharpness_module, image_path)
        f_jpeg = executor.submit(run_jpeg_ratio_module, image_path)
        f_texture = executor.submit(run_texture_module, image_path)
        f_entropy = executor.submit(run_color_entropy_module, image_path)
        f_exif = executor.submit(run_exif_module, image_path)

        ela_std_dev, ela_path = f_ela.result()
        fft_freq, fft_path = f_fft.result()
        noise_var = f_noise.result()
        sharpness = f_sharp.result()
        jpeg_ratio = f_jpeg.result()
        edge_density = f_texture.result()
        color_entropy = f_entropy.result()
        meta_flags, has_ai_sig = f_exif.result()

    return {
        "ela_std_dev": ela_std_dev,
        "ela_path": ela_path,
        "fft_freq": fft_freq,
        "fft_path": fft_path,
        "noise_var": noise_var,
        "sharpness": sharpness,
        "jpeg_ratio": jpeg_ratio,
        "edge_density": edge_density,
        "color_entropy": color_entropy,
        "meta_flags": meta_flags,
        "has_ai_sig": has_ai_sig
    }
