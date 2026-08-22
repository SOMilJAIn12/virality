"""
Turns a completed simulation (list of RoundResults + scoring) into:
  1. A SimulationReport pydantic object (structured, for later reuse
     by a frontend/API).
  2. A human-readable text report (for printing to the console now).

The AI-generated part is ONLY the closing "AI SUMMARY" paragraph, and
it is explicitly instructed to explain the real numbers, not invent a
score (see prompts.persona.SUMMARY_SYSTEM_PROMPT).
"""
from __future__ import annotations

import json

from app.config import Settings
from app.llm.base import LLMProvider
from app.models import ContentProfile, RoundResult, SimulationReport
from app.personas.definitions import get_persona_pool
from app.prompts.persona import SUMMARY_SYSTEM_PROMPT
from app.simulation.scoring import (
    classify_potential,
    compute_virality_score,
    identify_drivers_and_weaknesses,
)

_ID_TO_NAME = {p.id: p.name for p in get_persona_pool()}


async def build_report(
    video_path: str,
    content: ContentProfile,
    rounds: list[RoundResult],
    llm: LLMProvider,
    settings: Settings,
) -> SimulationReport:
    virality_score = compute_virality_score(rounds, settings.round_cohort_sizes)
    potential = classify_potential(virality_score)
    drivers, weaknesses = identify_drivers_and_weaknesses(rounds)

    summary_input = {
        "video": video_path,
        "content_title": content.title,
        "rounds": [
            {
                "round": r.round_number,
                "cohort_size": r.cohort_size,
                "watch_rate": r.stats.watch_rate,
                "completion_rate": r.stats.average_completion_rate,
                "like_rate": r.stats.like_rate,
                "comment_rate": r.stats.comment_rate,
                "share_rate": r.stats.share_rate,
                "follow_rate": r.stats.follow_rate,
                "distribution_score": r.distribution_score,
                "decision": r.decision,
            }
            for r in rounds
        ],
        "virality_score": virality_score,
        "potential": potential,
        "main_drivers": drivers,
        "weaknesses": weaknesses,
    }

    try:
        # complete_text, not complete_json: the summary is plain prose
        # (see SUMMARY_SYSTEM_PROMPT), not something we parse as JSON.
        # It was previously sent through complete_json(), which forces
        # Groq's response_format=json_object mode -- the model can't
        # satisfy both "write plain English" and "respond only with
        # valid JSON" at once, which is exactly what produced the
        # `json_validate_failed` (HTTP 400) error.
        ai_summary = await llm.complete_text(
            SUMMARY_SYSTEM_PROMPT,
            "Here are the real simulation metrics as JSON:\n"
            + json.dumps(summary_input, indent=2)
            + "\n\nWrite the plain-English summary now (plain text, not JSON).",
            temperature=0.5,
        )
        ai_summary = ai_summary.strip().strip("`")
    except Exception as e:
        ai_summary = f"(AI summary unavailable: {e})"

    return SimulationReport(
        video_path=video_path,
        content_profile=content,
        rounds=rounds,
        virality_score=virality_score,
        potential=potential,
        main_drivers=drivers,
        weaknesses=weaknesses,
        ai_summary=ai_summary,
    )


def _insight_label(reaction) -> str:
    if reaction.share:
        return "LIKELY TO SHARE"
    if reaction.comment:
        return "LIKELY TO COMMENT"
    if reaction.like:
        return "LIKELY TO LIKE"
    if not reaction.watch or reaction.completion_rate < 0.25:
        return "LIKELY TO SKIP"
    return "PASSIVE VIEWER"


def render_text_report(report: SimulationReport) -> str:
    lines: list[str] = []
    W = 50
    lines.append("=" * W)
    lines.append("AI VIRALITY SIMULATOR")
    lines.append("=" * W)
    lines.append("")
    lines.append("VIDEO")
    lines.append(report.video_path)
    lines.append("")
    lines.append("CONTENT PROFILE")
    lines.append(f"Title: {report.content_profile.title}")
    lines.append(f"Summary: {report.content_profile.summary}")
    lines.append(f"Duration: {report.content_profile.duration_seconds:.1f}s")
    lines.append(f"Target audience: {report.content_profile.target_audience}")
    lines.append("")
    lines.append("-" * W)
    lines.append("SIMULATION")
    lines.append("-" * W)

    for r in report.rounds:
        s = r.stats
        lines.append("")
        lines.append(f"Round {r.round_number}")
        lines.append(f"Personas: {s.total_personas} "
                      f"(successful: {s.successful_personas}, failed: {s.failed_personas})")
        lines.append(f"Watch Rate: {s.watch_rate * 100:.1f}%")
        lines.append(f"Completion: {s.average_completion_rate * 100:.1f}%")
        lines.append(f"Rewatch Rate: {s.rewatch_rate * 100:.1f}%")
        lines.append(f"Like Rate: {s.like_rate * 100:.1f}%")
        lines.append(f"Comment Rate: {s.comment_rate * 100:.1f}%")
        lines.append(f"Share Rate: {s.share_rate * 100:.1f}%")
        lines.append(f"Follow Rate: {s.follow_rate * 100:.1f}%")
        lines.append("")
        lines.append(f"Distribution Score: {r.distribution_score:.2f}")
        lines.append(f"Decision: {r.decision}")

    lines.append("")
    lines.append("-" * W)
    lines.append("FINAL RESULT")
    lines.append("-" * W)
    lines.append("")
    lines.append(f"VIRALITY SCORE: {report.virality_score:.0f}/100")
    lines.append("")
    lines.append(f"Potential: {report.potential}")
    lines.append("")
    lines.append("Main Drivers:")
    for d in report.main_drivers:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("Weaknesses:")
    for w in report.weaknesses:
        lines.append(f"- {w}")

    lines.append("")
    lines.append("-" * W)
    lines.append("PERSONA INSIGHTS")
    lines.append("-" * W)
    if report.rounds:
        last_round = report.rounds[-1]
        seen = set()
        for reaction in last_round.reactions:
            if reaction.persona_id in seen:
                continue
            seen.add(reaction.persona_id)
            display_name = _ID_TO_NAME.get(reaction.persona_id, reaction.persona_id)
            lines.append("")
            lines.append(f"{display_name}:")
            lines.append(_insight_label(reaction))

    lines.append("")
    lines.append("-" * W)
    lines.append("AI SUMMARY")
    lines.append("-" * W)
    lines.append("")
    lines.append(report.ai_summary)
    lines.append("=" * W)

    return "\n".join(lines)
