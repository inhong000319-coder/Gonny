"""Korean topic/subject/object/conjunction particle resolution.

Shared by note_generator.py (place-name-driven note sentences) and
service.py (the closed-day exclusion message) - anywhere a sentence needs
to pick 은/는, 이/가, 을/를, 와/과 based on whether the preceding word ends
in a batchim (final consonant), which can't be known until the actual
Korean place name is substituted in.

Usage: write the ambiguous choice literally as one of the markers below
(e.g. "{name}은(는)") in the template/f-string, then call
resolve_particles() on the fully-formatted sentence. This is the same
convention destination data already uses for its own note_templates (see
scripts/merge_jeju_places.py, scripts/apply_jeju_place_text.py).

Only ever resolves a marker immediately preceded by a Hangul syllable,
ASCII letter, or digit - a marker with nothing to attach to (stray
template text, or preceded by punctuation) is left as-is rather than
guessed at.
"""

from __future__ import annotations

import re

_PARTICLE_CHOICES: dict[str, tuple[str, str]] = {
    # marker: (final-consonant form, no-final-consonant form)
    "은(는)": ("은", "는"),
    "이(가)": ("이", "가"),
    "을(를)": ("을", "를"),
    "와(과)": ("과", "와"),
}


def has_final_consonant(word: str) -> bool:
    if not word:
        return False
    last_char = word[-1]
    if "가" <= last_char <= "힣":
        return (ord(last_char) - ord("가")) % 28 != 0
    return False


def resolve_particles(text: str) -> str:
    resolved = text
    for marker, (consonant_form, vowel_form) in _PARTICLE_CHOICES.items():
        pattern = re.compile(rf"([가-힣A-Za-z0-9]+){re.escape(marker)}")
        resolved = pattern.sub(
            lambda match, consonant_form=consonant_form, vowel_form=vowel_form: (
                f"{match.group(1)}{consonant_form if has_final_consonant(match.group(1)) else vowel_form}"
            ),
            resolved,
        )
    return resolved
