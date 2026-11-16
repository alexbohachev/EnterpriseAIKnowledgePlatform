"""Conservative deterministic Stage 5 guards (NOT a full prompt-injection/PII solution).

Design: treat all retrieved PDF text as untrusted. Never let text become a tool
call, system instruction or authorization decision. Regex patterns are best effort.
"""
from __future__ import annotations
import re

class UnsafeInput(ValueError):
    pass

class UnsafeModelOutput(ValueError):
    pass

# Do not include originals in logs or exceptions.
_EMAIL = re.compile(r"(?<![\w@])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w@])")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30}\b", flags=re.I)
_JAILBREAK = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts)\b"),
    re.compile(r"(?i)\b(disregard|override)\s+(your|the|all)\s+(system|developer)\s+(instructions|rules|prompt)\b"),
    re.compile(r"(?i)\b(reveal|print|show)\s+(your|the)\s+(hidden\s+)?(system|developer)\s+prompt\b"),
    re.compile(r"(?i)\bexfiltrat(e|ion)\b"),
    re.compile(r"(?i)\b(do not|don.t)\s+(follow|obey)\s+(your|the)\s+(rules|instructions)\b"),
    re.compile(r"(?i)(ігноруй|игнорируй)\s+(всі|все|усі|предыдущие|попередні)\s+(інструкції|инструкции|правила)"),
]
_SOURCE_TAG = re.compile(r"\[S(\d{1,3})\]")


def redact_pii(text: str) -> str:
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _IBAN.sub("[REDACTED_IBAN]", text)
    return _PHONE.sub("[REDACTED_PHONE]", text)


def guard_question(question: str) -> str:
    question = question.strip()
    if not question or len(question) > 4000:
        raise UnsafeInput("Invalid question size")
    if any(pattern.search(question) for pattern in _JAILBREAK):
        raise UnsafeInput("Request violates input policy")
    # Incoming personal identifiers should not reach embeddings or model calls.
    return redact_pii(question)


def sanitize_excerpts(excerpts: list[dict], max_total: int = 12000) -> list[dict]:
    budget = max_total
    sanitized = []
    for e in excerpts:
        # Block directives even when embedded in long paragraphs; this can remove
        # legitimate quoted security examples; it is intentionally conservative.
        kept = []
        for line in e['text'].splitlines():
            if any(pattern.search(line) for pattern in _JAILBREAK):
                kept.append("[UNTRUSTED_INSTRUCTION_REMOVED]")
            else:
                kept.append(line)
        clean = redact_pii("\n".join(kept))[:budget]
        if not clean.strip():
            clean = "[EMPTY_EXCERPT]"
        budget -= len(clean)
        sanitized.append({**e, 'text': clean})
        if budget <= 0:
            break
    return sanitized


def validate_answer(answer: str, source_count: int, max_chars: int = 4500) -> str:
    if not isinstance(answer, str) or not answer.strip() or len(answer) > max_chars:
        raise UnsafeModelOutput("Invalid model output length")
    if source_count > 0:
        cited = [int(n) for n in _SOURCE_TAG.findall(answer)]
        if not cited or any(n < 1 or n > source_count for n in cited):
            raise UnsafeModelOutput("Model output has missing or invalid source references")
    return redact_pii(answer.strip())
