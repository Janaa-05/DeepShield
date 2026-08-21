def calculate_authenticity_score(ai_prob, ela_std, fft_freq, noise_var, has_ai_sig):
    """
    Phase 5: Authenticity Score Calculation.
    Authenticity Score is directly proportional to Real Probability (real_prob = 1.0 - ai_prob).
    Primary ML classification threshold (0.68) determines AI vs Real verdict.
    Forensic signals (ELA, FFT, Noise) act as supporting evidence without overriding the ML model.
    """
    real_prob = 1.0 - ai_prob
    authenticity_score = round(real_prob * 100.0, 1)
    is_real = ai_prob < 0.68

    if is_real:
        label = "Likely Real"
        verdict_text = f"Authenticity Score: {authenticity_score}% (Likely Real)"
    else:
        label = "Likely AI Generated"
        verdict_text = f"Authenticity Score: {authenticity_score}% (Likely AI Generated)"

    explanation = (
        f"Primary classification by Swin Transformer (umm-maybe/AI-image-detector) at 0.68 threshold. "
        f"AI Probability: {round(ai_prob * 100.0, 1)}%, Real Probability: {round(real_prob * 100.0, 1)}%. "
        f"Supporting evidence: ELA std ({ela_std}), FFT freq ({fft_freq}), Noise var ({noise_var})."
    )

    return {
        "authenticity_score": authenticity_score,
        "label": label,
        "verdict_text": verdict_text,
        "is_real": is_real,
        "explanation": explanation
    }
