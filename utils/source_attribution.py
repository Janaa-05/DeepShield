def attribute_ai_source(metadata_flags, fft_freq, ela_std_dev, is_ai):
    """
    Phase 6: AI Source Attribution Engine.
    Examines EXIF metadata signatures or returns Experimental / Heuristic attribution.
    Does not claim unsupported generator models from binary AI classifiers.
    """
    if not is_ai:
        return "Not Applicable (Real Media)", 0.0

    meta_str = " ".join(metadata_flags).lower()

    # 1. EXIF Metadata Direct Signature Matching
    if "midjourney" in meta_str:
        return "Midjourney (EXIF Signature)", 95.0
    elif "stable diffusion" in meta_str or "sdxl" in meta_str or "automatic1111" in meta_str or "comfyui" in meta_str:
        return "Stable Diffusion (EXIF Signature)", 95.0
    elif "dall-e" in meta_str or "dalle" in meta_str:
        return "DALL·E 3 (EXIF Signature)", 95.0
    elif "flux" in meta_str:
        return "FLUX.1 (EXIF Signature)", 95.0
    elif "firefly" in meta_str or "adobe" in meta_str:
        return "Adobe Firefly (EXIF Signature)", 90.0

    # 2. Heuristic Non-Deterministic Attribution
    return "Not Determined (Experimental / Heuristic)", 50.0
