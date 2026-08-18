def attribute_ai_source(metadata_flags, fft_freq, ela_std_dev, is_ai):
    """
    Phase 6: AI Source Attribution Engine.
    Estimates the probable generative AI source model:
    - Midjourney
    - Stable Diffusion (SDXL / SD3)
    - DALL-E 3
    - FLUX.1
    - Adobe Firefly
    - Unknown Source (returns Unknown Source if confidence is low, avoiding guessing).
    """
    if not is_ai:
        return "Not Applicable (Real Media)", 0.0

    meta_str = " ".join(metadata_flags).lower()

    # 1. EXIF Metadata Direct Signature Matching
    if "midjourney" in meta_str:
        return "Midjourney (v5 / v6)", 95.0
    elif "stable diffusion" in meta_str or "sdxl" in meta_str or "automatic1111" in meta_str or "comfyui" in meta_str:
        return "Stable Diffusion (SDXL / SD3)", 95.0
    elif "dall-e" in meta_str or "dalle" in meta_str:
        return "DALL·E 3", 95.0
    elif "flux" in meta_str:
        return "FLUX.1", 95.0
    elif "firefly" in meta_str or "adobe" in meta_str:
        return "Adobe Firefly", 90.0

    # 2. Spectral & Noise Artifact Signatures
    # FLUX.1 / SD3 produce distinct high-frequency Fourier grid peaks (>230)
    if fft_freq > 235.0:
        return "FLUX.1 / SD3 (High Fourier Grid Variance)", 78.0
    elif fft_freq > 215.0 and ela_std_dev > 32.0:
        return "Midjourney (v6 Latent Diffusion)", 75.0
    elif ela_std_dev < 5.0 and fft_freq > 195.0:
        return "Stable Diffusion (Hyper-smooth Latent)", 72.0

    # 3. Fallback: Unknown Source (avoids guessing)
    return "Unknown Source", 40.0
