"""
Utility helpers for parsing evaluation blocks returned by Claude.
"""

from __future__ import annotations

import re


SCORE_PATTERN = re.compile(r"Score:\s*([1-5])", re.IGNORECASE)


def parse_evaluation_scores(text: str) -> dict:
    """
    Extract integer scores for cleanliness, communication, and efficiency
    from the interviewer feedback text.
    """
    scores = {"code_cleanliness": None, "communication": None, "efficiency": None, "raw": text}
    if not text:
        return scores

    cc = re.search(r"Code\s*Cleanliness[\s\S]*?Score:\s*([1-5])", text, re.IGNORECASE)
    com = re.search(r"Communication[\s\S]*?Score:\s*([1-5])", text, re.IGNORECASE)
    eff = re.search(r"Efficiency[\s\S]*?Score:\s*([1-5])", text, re.IGNORECASE)

    if cc:
        scores["code_cleanliness"] = int(cc.group(1))
    if com:
        scores["communication"] = int(com.group(1))
    if eff:
        scores["efficiency"] = int(eff.group(1))
    return scores


__all__ = ["parse_evaluation_scores"]
