"""
Unit tests for inject_context_repetition_at_attention_positions (CoRe).

Covers:
  A. Guard clauses  — empty/whitespace-only context, k clamping
  B. k == 2 path    — bookend-only (short + long prompts)
  C. short-prompt fallback — len(lines) < bounded_k → bookend-only
  D. k > 2 normal path — interior segmentation, marker numbering, recency echo
  E. Idempotency / marker content preservation
  F. Boundary at CORE_MINIMUM and CORE_MAXIMUM constants
"""

import pytest

from app.services.optimization.shared_prompt_techniques import (
    inject_context_repetition_at_attention_positions,
)
from app.services.optimization.optimizer_configuration import (
    CORE_MINIMUM_REPETITION_COUNT,  # 2
    CORE_MAXIMUM_REPETITION_COUNT,  # 5
)

CONTEXT = "Patient is on warfarin — bleeding risk HIGH."
CORE_MARKER_TEXT = "[CoRe — Critical Context Reminder]"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _count_occurrences(result: str, substring: str) -> int:
    return result.count(substring)


# ═════════════════════════════════════════════════════════════════════════════
# A. Guard clauses
# ═════════════════════════════════════════════════════════════════════════════

class TestGuardClauses:
    """CoRe must be a no-op when critical_context_to_repeat is empty."""

    def test_empty_string_context_returns_prompt_unchanged(self):
        prompt = "You are a helpful assistant. Do the task.\nReturn JSON."
        result = inject_context_repetition_at_attention_positions(prompt, "", k=3)
        assert result == prompt

    def test_whitespace_only_context_returns_prompt_unchanged(self):
        prompt = "Line one.\nLine two."
        result = inject_context_repetition_at_attention_positions(prompt, "   \n\t  ", k=3)
        assert result == prompt

    def test_none_like_empty_context_does_not_inject(self):
        prompt = "Perform extraction task."
        result = inject_context_repetition_at_attention_positions(prompt, "", k=5)
        assert CORE_MARKER_TEXT not in result


# Rename `k` parameter to `repetition_count_k` in call sites:
def inject_context_repetition_at_attention_positions(
    prompt_text, critical_context_to_repeat, k
):
    """Thin wrapper so tests pass a short `k=` kwarg."""
    from app.services.optimization.shared_prompt_techniques import (
        inject_context_repetition_at_attention_positions as _impl,
    )
    return _impl(
        prompt_text=prompt_text,
        critical_context_to_repeat=critical_context_to_repeat,
        repetition_count_k=k,
    )


# ═════════════════════════════════════════════════════════════════════════════
# B. k == 2 — bookend-only path (explicit and via clamping)
# ═════════════════════════════════════════════════════════════════════════════

class TestKEquals2:
    """k=2 must prepend and append the marker; no interior insertions."""

    def test_k2_injects_exactly_two_markers(self):
        prompt = "\n".join(f"Line {i}" for i in range(10))
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=2)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_k2_starts_with_marker(self):
        prompt = "Start line.\nEnd line."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=2)
        assert result.startswith("\n" + CORE_MARKER_TEXT)

    def test_k2_ends_with_context_text(self):
        prompt = "Start line.\nEnd line."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=2)
        # Result ends with the context string (after stripping trailing newline)
        assert CONTEXT in result.split(CORE_MARKER_TEXT)[-1]

    def test_k2_original_prompt_preserved_in_middle(self):
        prompt = "You are a doctor."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=2)
        assert prompt in result

    def test_k1_clamped_to_k2_bookend(self):
        """k=1 is below minimum (2); must be clamped to k=2."""
        prompt = "\n".join(f"Line {i}" for i in range(8))
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=1)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_k0_clamped_to_k2_bookend(self):
        """k=0 is below minimum; must be clamped."""
        prompt = "Short prompt."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=0)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_negative_k_clamped_to_k2(self):
        prompt = "Task description."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=-99)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2


# ═════════════════════════════════════════════════════════════════════════════
# C. Short-prompt fallback — len(lines) < bounded_k
#    When the prompt has FEWER lines than k, CoRe should fall back to bookend.
# ═════════════════════════════════════════════════════════════════════════════

class TestShortPromptFallback:
    """
    GAP.md P2-2: For short prompts, evenly-spaced interior repetition
    must NOT occur — function falls back to bookend-only.
    Tests verify: exactly 2 markers, correct positions, no interior clutter.
    """

    def test_single_line_prompt_k3_falls_back_to_bookend(self):
        """1 line < k=3: must degrade gracefully to prepend+append only."""
        prompt = "Extract all diagnoses."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_two_line_prompt_k3_falls_back_to_bookend(self):
        """2 lines < k=3: still not enough for interior split."""
        prompt = "Line one.\nLine two."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_two_line_prompt_k4_falls_back_to_bookend(self):
        """2 lines < k=4."""
        prompt = "Task.\nConstraints."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=4)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_three_line_prompt_k4_falls_back_to_bookend(self):
        """3 lines < k=4: still degenerate, bookend only."""
        prompt = "You are an expert.\nDo the task.\nReturn JSON."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=4)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_four_line_prompt_k5_falls_back_to_bookend(self):
        """4 lines < k=5: still degenerate."""
        prompt = "Line 1.\nLine 2.\nLine 3.\nLine 4."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=5)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_exactly_k_lines_takes_normal_interior_path(self):
        """
        Exactly `bounded_k` lines: the guard condition is `len(lines) < bounded_k`
        (strict less-than). So len(lines) == bounded_k does NOT trigger the
        fallback — it takes the normal interior segmentation path.
        """
        k = 4
        # 4 lines, k=4 → len(lines)==k → NOT < k → interior path
        prompt = "\n".join(f"Line {i}" for i in range(k))
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=k)
        # Interior path uses numbered markers, not the plain bookend marker
        assert f"[CoRe #{k}/{k} — Recency Echo]" in result

    def test_short_prompt_fallback_still_contains_original(self):
        """Original prompt text must be preserved after fallback."""
        prompt = "Short."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=5)
        assert "Short." in result

    def test_short_prompt_fallback_context_appears_twice(self):
        """CONTEXT string itself must appear twice (in both bookend markers)."""
        prompt = "Very short."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        assert _count_occurrences(result, CONTEXT) == 2

    def test_empty_prompt_k3_falls_back_gracefully(self):
        """Empty prompt is still augmented with bookend markers."""
        prompt = ""
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_single_line_no_interior_core_numbering(self):
        """
        Interior markers carry #n/k numbering. After a fallback there should be
        NO '#' numbered markers in the result.
        The bookend path produces the plain [CoRe — Critical Context Reminder]
        marker only, with no '#2/3' style numbering.
        """
        prompt = "Short task."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=4)
        # Interior-style markers: [CoRe #2/4] or [CoRe #2/4 — Recency Echo]
        assert "[CoRe #" not in result


# ═════════════════════════════════════════════════════════════════════════════
# D. k > 2 normal path — interior segmentation & marker numbering
# ═════════════════════════════════════════════════════════════════════════════

class TestKGreaterThan2NormalPath:
    """
    When len(lines) >= bounded_k and k > 2, CoRe must:
    - Insert (k-2) interior markers numbered #2/k … #(k-1)/k
    - Add final recency echo marker [CoRe #k/k — Recency Echo]
    - Preserve all original lines (no content dropped)
    """

    def _long_prompt(self, num_lines: int = 20) -> str:
        return "\n".join(f"Instruction line {i}: do something specific." for i in range(num_lines))

    def test_k3_produces_one_interior_and_one_recency_marker(self):
        """k=3: 1 interior (#2/3) + 1 recency (#3/3) = 2 special markers."""
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(20), CONTEXT, k=3
        )
        # Total unique CoRe marker types
        assert "[CoRe #2/3]" in result
        assert "[CoRe #3/3 — Recency Echo]" in result

    def test_k3_total_context_occurrences(self):
        """k=3: context text appears in 2 positions (interior + recency)."""
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(20), CORE_MARKER_TEXT, k=3
        )
        # The context itself contains the marker text — skip and use plain CONTEXT
        result2 = inject_context_repetition_at_attention_positions(
            self._long_prompt(20), CONTEXT, k=3
        )
        assert _count_occurrences(result2, CONTEXT) == 2  # interior + recency

    def test_k4_produces_correct_numbered_markers(self):
        """k=4: 2 interior (#2/4, #3/4) + 1 recency (#4/4)."""
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(30), CONTEXT, k=4
        )
        assert "[CoRe #2/4]" in result
        assert "[CoRe #3/4]" in result
        assert "[CoRe #4/4 — Recency Echo]" in result

    def test_k5_produces_correct_numbered_markers(self):
        """k=5: 3 interior (#2/5, #3/5, #4/5) + 1 recency (#5/5)."""
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(40), CONTEXT, k=5
        )
        assert "[CoRe #2/5]" in result
        assert "[CoRe #3/5]" in result
        assert "[CoRe #4/5]" in result
        assert "[CoRe #5/5 — Recency Echo]" in result

    def test_k3_all_original_lines_preserved(self):
        """No original lines should be dropped during interior splitting."""
        prompt = self._long_prompt(20)
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        for i in range(20):
            assert f"Instruction line {i}:" in result

    def test_k5_all_original_lines_preserved(self):
        prompt = self._long_prompt(40)
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=5)
        for i in range(40):
            assert f"Instruction line {i}:" in result

    def test_result_ends_with_recency_echo(self):
        """Result must end with the recency echo (trimmed)."""
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(25), CONTEXT, k=3
        )
        assert result.rstrip("\n").endswith(CONTEXT)

    def test_plain_core_marker_not_present_in_interior_mode(self):
        """
        In interior mode the bookend-style plain [CoRe — Critical Context Reminder]
        marker must NOT appear — only numbered markers are used.
        """
        result = inject_context_repetition_at_attention_positions(
            self._long_prompt(20), CONTEXT, k=3
        )
        assert CORE_MARKER_TEXT not in result


# ═════════════════════════════════════════════════════════════════════════════
# E. k clamping at CORE_MAXIMUM (5)
# ═════════════════════════════════════════════════════════════════════════════

class TestKClamping:
    """k must be clamped to [CORE_MINIMUM, CORE_MAXIMUM]."""

    def test_k_above_max_clamped_to_max(self):
        """k=99 should behave identically to k=5."""
        prompt = "\n".join(f"Line {i}" for i in range(50))
        result_99 = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=99)
        result_max = inject_context_repetition_at_attention_positions(
            prompt, CONTEXT, k=CORE_MAXIMUM_REPETITION_COUNT
        )
        assert result_99 == result_max

    def test_k_at_minimum_produces_bookend(self):
        """k == CORE_MINIMUM_REPETITION_COUNT (2) takes bookend path."""
        prompt = "\n".join(f"Line {i}" for i in range(15))
        result = inject_context_repetition_at_attention_positions(
            prompt, CONTEXT, k=CORE_MINIMUM_REPETITION_COUNT
        )
        assert _count_occurrences(result, CORE_MARKER_TEXT) == 2

    def test_k_at_maximum_produces_correct_markers(self):
        """k == CORE_MAXIMUM_REPETITION_COUNT (5) produces 5/5 recency echo."""
        prompt = "\n".join(f"Line {i}" for i in range(50))
        result = inject_context_repetition_at_attention_positions(
            prompt, CONTEXT, k=CORE_MAXIMUM_REPETITION_COUNT
        )
        assert f"[CoRe #{CORE_MAXIMUM_REPETITION_COUNT}/{CORE_MAXIMUM_REPETITION_COUNT} — Recency Echo]" in result


# ═════════════════════════════════════════════════════════════════════════════
# F. Whitespace / leading-newline handling
# ═════════════════════════════════════════════════════════════════════════════

class TestWhitespaceHandling:
    """Critical context should be stripped before injection."""

    def test_context_with_leading_trailing_whitespace_is_stripped(self):
        context_with_whitespace = "  " + CONTEXT + "\n\n"
        prompt = "\n".join(f"Line {i}" for i in range(5))
        result = inject_context_repetition_at_attention_positions(
            prompt, context_with_whitespace, k=2
        )
        # Stripped version appears; raw version with leading spaces does NOT
        assert CONTEXT in result
        # No double-space prefix in the injected block
        assert "  " + CONTEXT not in result

    def test_prompt_with_mixed_blank_lines_not_mangled(self):
        """Prompts containing blank lines should not confuse the splitter."""
        prompt = "First block.\n\nSecond block.\n\nThird block."
        result = inject_context_repetition_at_attention_positions(prompt, CONTEXT, k=3)
        assert "First block." in result
        assert "Third block." in result
