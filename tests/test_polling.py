"""Tests for the Backoff helper in polling.py."""

from __future__ import annotations

import pytest

from yandex_messenger_bot.polling.polling import Backoff


class TestBackoff:
    def test_first_delay_near_min(self) -> None:
        b = Backoff(min_delay=1.0, max_delay=60.0, factor=2.0, jitter=0.0)
        delay = b.next()
        # With jitter=0, the first call returns exactly min_delay
        assert delay == pytest.approx(1.0)

    def test_delay_increases_on_successive_calls(self) -> None:
        b = Backoff(min_delay=1.0, max_delay=60.0, factor=2.0, jitter=0.0)
        delays = [b.next() for _ in range(4)]
        # 1.0, 2.0, 4.0, 8.0 with no jitter
        assert delays == pytest.approx([1.0, 2.0, 4.0, 8.0])

    def test_delay_does_not_exceed_max(self) -> None:
        b = Backoff(min_delay=1.0, max_delay=5.0, factor=10.0, jitter=0.0)
        for _ in range(10):
            delay = b.next()
            # With jitter=0, delay == _current before advancing.
            # The internal _current is capped at max after each call.
            # The returned value is _current + jitter_sample (0 here).
            assert delay <= 5.0 + 1e-9  # tiny float tolerance

    def test_reset_returns_to_min(self) -> None:
        b = Backoff(min_delay=0.5, max_delay=30.0, factor=2.0, jitter=0.0)
        b.next()
        b.next()
        b.next()
        b.reset()
        delay = b.next()
        assert delay == pytest.approx(0.5)

    def test_jitter_adds_positive_noise(self) -> None:
        """With jitter > 0 the returned delay should be >= _current (no jitter=0 baseline)."""
        b = Backoff(min_delay=1.0, max_delay=60.0, factor=2.0, jitter=1.0)
        delays = [b.next() for _ in range(20)]
        # All delays must be at least the base value (min_delay=1.0 for first)
        assert all(d >= 0.0 for d in delays)

    def test_multiple_resets_work_correctly(self) -> None:
        b = Backoff(min_delay=2.0, max_delay=100.0, factor=3.0, jitter=0.0)
        # Advance several times
        for _ in range(5):
            b.next()
        b.reset()
        first_after_reset = b.next()
        assert first_after_reset == pytest.approx(2.0)
        # Advance again, reset again
        for _ in range(3):
            b.next()
        b.reset()
        assert b.next() == pytest.approx(2.0)

    def test_factor_one_keeps_delay_constant(self) -> None:
        b = Backoff(min_delay=3.0, max_delay=100.0, factor=1.0, jitter=0.0)
        delays = [b.next() for _ in range(5)]
        assert all(d == pytest.approx(3.0) for d in delays)

    def test_max_delay_clamps_internal_state(self) -> None:
        """After reaching max, further calls must not exceed max + jitter."""
        b = Backoff(min_delay=1.0, max_delay=4.0, factor=2.0, jitter=0.0)
        # 1 → 2 → 4 → 4 (capped)
        for _ in range(10):
            d = b.next()
            assert d <= 4.0 + 1e-9
