"""Evidence sufficiency gate. Decides answer | context_only | clarify | refuse.

No fallback to the whole library: if nothing in scope supports the topic,
the agent refuses and says why.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .scope import Scope

OUT_OF_KB_TOPICS = {"price"}


@dataclass
class Gate:
    decision: str                      # answer | context_only | clarify | refuse
    reason: str
    applicable: list[dict] = field(default_factory=list)   # retrieval rows
    context: list[dict] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


def gate(sc: Scope, rows: list[dict], context_docs: dict | None = None, *,
         missing_documents: list[str] | None = None) -> Gate:
    context_docs = context_docs or {}
    if missing_documents:
        return Gate("refuse", "requested_document_unavailable:" + ",".join(missing_documents),
                    unknowns=["requested_document_unavailable:" + x for x in missing_documents])
    if sc.conflicts:
        return Gate("clarify", "scope_conflict", conflicts=list(sc.conflicts))
    if sc.unknown_institution:
        return Gate("refuse", f"institution_not_in_kb:{sc.unknown_institution}")
    if sc.topics & OUT_OF_KB_TOPICS:
        return Gate("refuse", "topic_outside_kb:" + ",".join(sorted(sc.topics & OUT_OF_KB_TOPICS)))
    if not sc.topics:
        return Gate("refuse", "no_policy_topic_recognised")

    ev = [r for r in rows if r["eligible"] and r["topic_match"]]
    if sc.institution and not any(r["card"]["institution"] == sc.institution for r in ev):
        other = sorted({r["card"]["level"] for r in rows
                        if r["card"]["institution"] == sc.institution and not r["eligible"]})
        if other:
            return Gate("refuse", f"institution_policy_in_kb_covers_other_level:{','.join(other)}")
    if not ev:
        return Gate("refuse", "no_evidence_in_scope")
    applicable = [r for r in ev if r["applicability"] in ("applies", "applies_if_scope_confirmed")]
    context = [r for r in ev if r["applicability"] == "context_only"]

    g = Gate("answer" if applicable else "context_only",
             "evidence_found" if applicable else "only_nonbinding_or_foreign_context",
             applicable=applicable, context=context)

    # Requiring a detector and forbidding sole reliance are compatible.
    # Mere differences in emphasis must not be labelled a contradiction.

    # what we still do not know
    if sc.institution is None and any(r["card"]["institution"] for r in applicable):
        g.unknowns.append("institution_not_stated")
    if sc.level is None:
        g.unknowns.append("education_level_not_stated")
    if any(r["applicability"] == "applies_if_scope_confirmed" and r["card"]["jurisdiction"] in ("Abu Dhabi", "Dubai", "Sharjah") for r in applicable):
        g.unknowns.append("emirate_or_school_type_not_stated")
    if "permission" in sc.topics and sc.level in ("higher_ed", "graduate", None) \
            and not context_docs.get("syllabus"):
        g.unknowns.append("course_syllabus_not_provided")
    if sc.level == "k12" and sc.topics & {"permission", "exam", "age_limit", "assignment"}:
        g.unknowns.append("moe_2026_classroom_genai_guide_text_not_in_kb")
    if any(r["card"]["source_id"] == "UOS_GRAD_AI_POLICY" for r in applicable):
        g.unknowns.append("UOS_policy_formal_approval_not_evidenced")
    g.unknowns = list(dict.fromkeys(g.unknowns))
    return g
