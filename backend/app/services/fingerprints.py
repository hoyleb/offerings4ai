import hashlib
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def generate_idea_fingerprint(
    title: str,
    problem: str,
    proposed_idea: str,
    why_ai_benefits: str,
) -> str:
    payload = "||".join(
        part.strip().lower() for part in [title, problem, proposed_idea, why_ai_benefits]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(TOKEN_RE.findall(left.lower()))
    right_tokens = set(TOKEN_RE.findall(right.lower()))
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def keyword_profile(text: str) -> dict[str, int]:
    return dict(Counter(TOKEN_RE.findall(text.lower())).most_common(20))
