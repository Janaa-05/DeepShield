def calculate_authenticity_score(ai_prob, ela_std, fft_freq, noise_var, has_ai_sig):
    """
    Phase 5: Unified Authenticity Score Calculation (0% to 100%).
    
    Formula Weighting:
    - EfficientNet Deep Learning Confidence: 45%
    - Error Level Analysis (ELA) Variance: 15%
    - 2D Fourier Spectrum (FFT) Grid Energy: 15%
    - Noise Floor Variance: 15%
    - Metadata Provenance Signals: 10%
    
    Returns:
    - authenticity_score: Percentage (0-100%) indicating likelihood of REAL authenticity.
    - label: "Likely Real" or "Likely AI Generated"
    - explanation: Diagnostic breakdown.
    """
    # 1. Deep Learning Base Real Score (0 - 100)
    dl_real_score = (1.0 - ai_prob) * 100.0

    # 2. ELA Score (ELA 10-25 is normal real; <6 or >35 is AI anomaly)
    if 10.0 <= ela_std <= 25.0:
        ela_score = 90.0
    elif ela_std < 6.0 or ela_std > 35.0:
        ela_score = 15.0
    else:
        ela_score = 60.0

    # 3. FFT Score (FFT < 195 is normal real; >210 is AI grid noise)
    if fft_freq < 195.0:
        fft_score = 92.0
    elif fft_freq > 215.0:
        fft_score = 10.0
    else:
        fft_score = 55.0

    # 4. Noise Score (Noise > 80 is normal sensor noise; <30 is hyper-smooth AI)
    if noise_var > 80.0:
        noise_score = 90.0
    elif noise_var < 30.0:
        noise_score = 20.0
    else:
        noise_score = 60.0

    # 5. Metadata Score
    meta_score = 0.0 if has_ai_sig else 85.0

    # Weighted Sum
    authenticity_score = (
        (dl_real_score * 0.45) +
        (ela_score * 0.15) +
        (fft_score * 0.15) +
        (noise_score * 0.15) +
        (meta_score * 0.10)
    )

    authenticity_score = round(max(1.0, min(99.0, authenticity_score)), 1)
    is_real = authenticity_score >= 50.0

    if is_real:
        label = "Likely Real"
        verdict_text = f"Authenticity Score: {authenticity_score}% (Likely Real)"
    else:
        label = "Likely AI Generated"
        verdict_text = f"Authenticity Score: {authenticity_score}% (Likely AI Generated)"

    explanation = (
        f"Score synthesized from EfficientNet Deep Learning ({round(dl_real_score, 1)}%), "
        f"ELA re-compression ({round(ela_score, 1)}%), Fourier spectral noise ({round(fft_score, 1)}%), "
        f"and noise floor variance ({round(noise_score, 1)}%)."
    )

    return {
        "authenticity_score": authenticity_score,
        "label": label,
        "verdict_text": verdict_text,
        "is_real": is_real,
        "explanation": explanation
    }
