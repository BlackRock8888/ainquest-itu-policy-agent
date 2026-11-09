"""Conservative document boundaries derived from the source manifest.

This is a small curated matcher, not general document entity resolution.
Missing/full-text requirements must not fall back to adjacent policy summaries.
"""
from __future__ import annotations

import re
from .text import normalise

# The manifest contains announcements/summaries, not these full instruments.
MISSING_DOCUMENTS = (
    ('KHDA_AI_POLICY', r'khda|هيئة المعرفة'),
    ('ADEK_TECHNOLOGY_AI_POLICY', r'adek.{0,45}(technology.{0,15}(ai|artificial)|تكنولوجيا)|technology.{0,15}(ai|artificial).{0,25}policy.{0,25}adek'),
    ('MOE_CLASSROOM_GENAI_GUIDE', r'safe and responsible use of (generative ai|genai)|ministry of education.{0,100}classrooms?.{0,15}guid|(moe|classroom|وزارة التربية).{0,65}(classroom.{0,15}guid|genai.{0,15}guid|full manual|دليل)|دليل وزارة التربية|руководств.{0,30}moe|moe.{0,30}руководств'),
    ('AUS_FULL_POLICY', r'(full|complete|полный).{0,25}aus.{0,15}(policy|политик)|aus.{0,25}(full policy|complete policy)'),
    ('SPEA_FULL_FRAMEWORK', r'spea.{0,45}(full|official text)|полный.{0,30}spea'),
)


def requested_sources(query: str, sources: dict, institution: str | None) -> tuple[set[str], list[str]]:
    q = normalise(query)
    missing = [name for name, pattern in MISSING_DOCUMENTS if re.search(normalise(pattern), q)]
    # A jurisdiction-wide existence question cannot be answered by a local rule.
    if re.search(r'federal|national|федеральн|اتحادي', q) and re.search(r'uniform|all universit|all college|disclos|genai|chatgpt|раскрыт', q):
        missing.append('FEDERAL_HIGHER_ED_GENAI_RULE_NOT_ESTABLISHED')
    requested = set()
    if institution:
        requested.update(sid for sid, src in sources.items() if src.get('institution') == institution)
    # Full known titles identify a document even without an institution alias.
    for sid, src in sources.items():
        title = normalise(src['title'])
        if title and title in q:
            requested.add(sid)
    return requested, missing


def capability_question(query: str) -> bool:
    q = normalise(query)
    if 'turnitin' not in q:
        return False
    if re.search(r'misconduct|punish|penalt|sole|наказ|основан|عقوب', q):
        return False
    return bool(re.search(r'detect|support|language|capabil|arabic|russian|english|обнаруж|язык|араб|распозна|поддерж|كشف|لغة|العربية', q))


def title_sources(query: str, sources: dict) -> set[str]:
    q = normalise(query)
    return {sid for sid, src in sources.items() if normalise(src['title']) in q}
