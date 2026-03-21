"""Composite risk scoring — combines all signal layers into a single score."""


def composite_risk(deepfake_score: float, gemini: dict) -> dict:
    """Compute weighted risk score from all signal layers.

    Args:
        deepfake_score: 0.0-1.0 fake probability from wav2vec2
        gemini: dict with escalation_score (0-100) and phrase_flags (list)

    Returns:
        {"score": float 0-1, "level": "high"|"medium"|"low"}
    """
    acoustic = deepfake_score * 0.40
    emotional = gemini.get("escalation_score", 0) / 100 * 0.35
    linguistic = min(len(gemini.get("phrase_flags", [])), 5) / 5 * 0.25
    total = min(acoustic + emotional + linguistic, 1.0)

    if total > 0.7:
        level = "high"
    elif total > 0.4:
        level = "medium"
    else:
        level = "low"

    return {
        "score": round(total, 4),
        "level": level,
        "breakdown": {
            "acoustic": round(acoustic, 4),
            "emotional": round(emotional, 4),
            "linguistic": round(linguistic, 4),
        },
    }
