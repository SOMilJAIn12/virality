"""
Deterministic engagement aggregation.

Deliberately contains ZERO LLM calls. Every number here is a plain
Python average/ratio computed from the structured PersonaReaction
objects that already came back from the personas. Keeping this
LLM-free means the metrics are reproducible and auditable.
"""
from __future__ import annotations

from app.models import EngagementStats, PersonaReaction


def aggregate_engagement(
    reactions: list[PersonaReaction],
    total_personas: int,
    failed_personas: int,
) -> EngagementStats:
    n = len(reactions)
    if n == 0:
        return EngagementStats(
            total_personas=total_personas,
            successful_personas=0,
            failed_personas=failed_personas,
            watch_rate=0.0,
            skip_rate=1.0,
            average_completion_rate=0.0,
            rewatch_rate=0.0,
            like_rate=0.0,
            comment_rate=0.0,
            share_rate=0.0,
            follow_rate=0.0,
        )

    watched = [r for r in reactions if r.watch]
    watch_rate = len(watched) / n
    skip_rate = 1.0 - watch_rate
    avg_completion = sum(r.completion_rate for r in reactions) / n
    rewatch_rate = sum(1 for r in reactions if r.rewatch) / n
    like_rate = sum(1 for r in reactions if r.like) / n
    comment_rate = sum(1 for r in reactions if r.comment) / n
    share_rate = sum(1 for r in reactions if r.share) / n
    follow_rate = sum(1 for r in reactions if r.follow) / n

    return EngagementStats(
        total_personas=total_personas,
        successful_personas=n,
        failed_personas=failed_personas,
        watch_rate=watch_rate,
        skip_rate=skip_rate,
        average_completion_rate=avg_completion,
        rewatch_rate=rewatch_rate,
        like_rate=like_rate,
        comment_rate=comment_rate,
        share_rate=share_rate,
        follow_rate=follow_rate,
    )
