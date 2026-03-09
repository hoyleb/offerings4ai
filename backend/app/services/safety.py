from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.schemas import IdeaCreate


@dataclass(frozen=True)
class SafetySignal:
    label: str
    weight: int
    pattern: re.Pattern[str]
    message: str


@dataclass
class SafetyScanResult:
    risk_score: int
    matches: list[str]

    @property
    def blocked(self) -> bool:
        return self.risk_score >= 4


SAFETY_SIGNALS = (
    SafetySignal(
        label="instruction_override",
        weight=4,
        pattern=re.compile(
            r"(?is)\b(ignore|override|disregard|forget|bypass)\b.{0,40}"
            r"\b(previous|prior|system|developer|safety|policy|instructions?)\b"
        ),
        message="tries to override evaluator or system instructions",
    ),
    SafetySignal(
        label="role_assignment",
        weight=3,
        pattern=re.compile(
            r"(?is)\b(you are|act as|pretend to be)\b.{0,60}"
            r"\b(agent|assistant|system|reviewer|evaluator)\b"
        ),
        message="contains role-assignment phrasing directed at the reader",
    ),
    SafetySignal(
        label="payment_manipulation",
        weight=3,
        pattern=re.compile(
            r"(?is)\b(pay|send|transfer|wire)\b.{0,50}"
            r"\b(wallet|reward|funds|money|payment|payout)\b"
        ),
        message="requests direct payment or payout manipulation",
    ),
    SafetySignal(
        label="tool_or_navigation_request",
        weight=2,
        pattern=re.compile(
            r"(?is)\b(click|open|visit|browse|navigate|call)\b.{0,50}"
            r"\b(tool|browser|url|link|endpoint|function|api)\b"
        ),
        message="attempts to drive tools, browsing, or API calls",
    ),
    SafetySignal(
        label="prompt_exfiltration",
        weight=3,
        pattern=re.compile(
            r"(?is)\b(reveal|print|show|dump|return)\b.{0,50}"
            r"\b(system prompt|developer prompt|hidden instructions|chain of thought)\b"
        ),
        message="asks for hidden prompt or reasoning disclosure",
    ),
    SafetySignal(
        label="meta_prompt_markup",
        weight=2,
        pattern=re.compile(
            r"(?is)(<system>|role\s*:\s*system|role\s*:\s*developer|"
            r"json-rpc|tool_call|function_call)"
        ),
        message=("includes prompt-markup or tool-call framing common in injection " "attempts"),
    ),
)


def scan_submission(payload: IdeaCreate) -> SafetyScanResult:
    """Purpose: Detect prompt-injection style content in a structured idea submission.

    Args:
        payload: Incoming idea submission payload.

    Returns:
        SafetyScanResult with aggregate risk score and human-readable matches.
    """

    combined_text = "\n\n".join(
        [payload.title, payload.problem, payload.proposed_idea, payload.why_ai_benefits]
    )
    matches: list[str] = []
    score = 0
    for signal in SAFETY_SIGNALS:
        if signal.pattern.search(combined_text):
            score += signal.weight
            matches.append(signal.message)
    return SafetyScanResult(risk_score=score, matches=matches)


def enforce_safe_submission(payload: IdeaCreate) -> None:
    """Purpose: Block unsafe submissions before they enter the public evaluation pool.

    Args:
        payload: Incoming idea submission payload.

    Returns:
        None.

    Raises:
        HTTPException: Raised when the submission appears to contain prompt-injection
            or payout-manipulation content.
    """

    result = scan_submission(payload)
    if not result.blocked:
        return

    detail = (
        "Submission rejected because it appears to contain prompt-injection "
        "or payout-manipulation instructions: "
        f"{'; '.join(result.matches)}. Rephrase the idea as descriptive "
        "content rather than instructions to the evaluator."
    )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )
