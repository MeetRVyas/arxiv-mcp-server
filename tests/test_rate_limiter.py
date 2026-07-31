"""
Tests for arxiv_mcp.rate_limiter.

The important property to prove here isn't just "wait() sleeps roughly the
right amount" (easy even with the old racy implementation) — it's that
concurrent callers from *different threads* actually get serialized instead
of all reading the same stale timestamp and releasing together
(concurrency-and-reliability.md #3).
"""

from __future__ import annotations

import threading
import time

from arxiv_mcp.rate_limiter import RateLimiter


class TestRateLimiterConcurrency:
    def test_concurrent_callers_are_serialized(self):
        """N threads all calling wait() at once on a limiter with interval I
        must finish spread out across roughly N*I seconds, not all bunched
        up near t=0 — that spread is only possible if access to the
        "read timestamp, decide, sleep, write timestamp" sequence is
        actually mutually exclusive across threads.
        """
        interval = 0.05
        n_threads = 6
        limiter = RateLimiter(interval)
        completion_times: list[float] = []
        lock = threading.Lock()

        def worker():
            limiter.wait()
            with lock:
                completion_times.append(time.monotonic())

        start = time.monotonic()
        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        completion_times.sort()
        elapsed_offsets = [t - start for t in completion_times]

        # The last completion should be roughly (n_threads - 1) * interval
        # after start — if threads were racing instead of serializing, most
        # would complete almost immediately instead of being spread out.
        expected_min_total = (n_threads - 1) * interval * 0.6  # generous tolerance
        assert elapsed_offsets[-1] >= expected_min_total, (
            f"Expected serialized completions spread across >= {expected_min_total:.3f}s, "
            f"got offsets {elapsed_offsets}"
        )

        # No two completions should be suspiciously close together (i.e. a
        # burst release), which is what the old racy version produced.
        gaps = [b - a for a, b in zip(elapsed_offsets, elapsed_offsets[1:], strict=False)]
        assert all(gap >= interval * 0.4 for gap in gaps), f"Burst detected: gaps={gaps}"

    def test_single_caller_paces_correctly(self):
        interval = 0.05
        limiter = RateLimiter(interval)
        limiter.wait()  # first call: no wait
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= interval * 0.8

    def test_set_min_interval_takes_effect(self):
        limiter = RateLimiter(1.0)
        limiter.set_min_interval(0.01)
        limiter.wait()
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # would be ~1s if still using the old interval
