"""Policy & legal adviser agent (ITU role: "Policy and legal adviser").

Deterministic by default: the answer is composed only from gated evidence
cards. An optional local LLM (Ollama, same stack as the ITU reference code)
may rephrase the answer; its output is rejected if it cites any card that
was not in the gated context.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

from .audit import Timer, new_run_id, utc_now, write_record
from .evidence import gate
from .source_scope import requested_sources, capability_question, title_sources
from .kb import KB
from .retrieve import retrieve
from .scope import extract_scope

AGENT_VERSION = "policy-adviser/0.1.2-prep"

L10N = {
    "en": {
        "answer": "Applicable rules found ({n}). Strongest source: {top}.",
        "context_only": "No binding rule for your case was found in the knowledge base; only non-binding or foreign context is available.",
        "clarify": "Your question mixes scopes ({c}). Please state one institution and one education level.",
        "refuse": "I cannot answer from the knowledge base: {r}. No rule is inferred.",
        "safe": "Check the course syllabus or ask the instructor in writing; keep a disclosure of any AI use.",
        "safe_detector": "A detector score is a signal, not proof. Request a human review meeting; no penalty should rest on the score alone where the cited policy says so.",
        "not_decision": "This is policy information, not a disciplinary or legal decision.",
    },
    "ru": {
        "answer": "Найдены применимые правила ({n}). Самый сильный источник: {top}.",
        "context_only": "Обязательного правила для вашего случая в базе нет; есть только необязательный или зарубежный контекст.",
        "clarify": "Вопрос смешивает разные области ({c}). Уточните одно учреждение и один уровень обучения.",
        "refuse": "Не могу ответить по базе знаний: {r}. Правило не домысливается.",
        "safe": "Проверьте силлабус курса или спросите преподавателя письменно; укажите использование ИИ.",
        "safe_detector": "Оценка детектора — сигнал, а не доказательство. Попросите рассмотрение человеком; там, где это сказано в цитируемой политике, наказание не может опираться только на оценку.",
        "not_decision": "Это справка о правилах, не дисциплинарное и не юридическое решение.",
    },
    "ar": {
        "answer": "تم العثور على قواعد منطبقة ({n}). أقوى مصدر: {top}.",
        "context_only": "لم يتم العثور على قاعدة ملزمة لحالتك في قاعدة المعرفة؛ يتوفر فقط سياق غير ملزم أو أجنبي.",
        "clarify": "سؤالك يخلط بين نطاقات مختلفة ({c}). يرجى تحديد مؤسسة واحدة ومستوى تعليمي واحد.",
        "refuse": "لا يمكنني الإجابة من قاعدة المعرفة: {r}. لا يتم استنتاج أي قاعدة.",
        "safe": "راجع مخطط المقرر أو اسأل المدرس كتابيًا، وأفصح عن أي استخدام للذكاء الاصطناعي.",
        "safe_detector": "نتيجة الكاشف إشارة وليست دليلاً. اطلب مراجعة بشرية؛ وحيث تنص السياسة المذكورة على ذلك، لا يجوز أن تستند العقوبة إلى النتيجة وحدها.",
        "not_decision": "هذه معلومات عن السياسات وليست قرارًا تأديبيًا أو قانونيًا.",
    },
}
L10N_REVIEW = {"en": "n/a", "ru": "pending", "ar": "pending_native_speaker"}


def _cite(row: dict, kb: KB) -> dict:
    c = row["card"]
    s = kb.sources[c["source_id"]]
    return {"card_id": c["card_id"], "source_id": c["source_id"], "title": s["title"],
            "publisher": s["publisher"], "url": s["url"], "quote": c["quote"],
            "quote_lang": c["quote_lang"], "rule_type": c["rule_type"],
            "binding_status": c["binding_status"], "applicability": row["applicability"],
            "version": c.get("version")}


def answer(query: str, kb: KB, *, explicit_scope: dict | None = None,
           visible_sources: set[str] | None = None, context_docs: dict | None = None,
           log_path: Path | None = None, llm: str | None = None, event_id: str | None = None,
           run_id: str | None = None) -> dict:
    run_id = run_id or new_run_id()
    with Timer() as t:
        sc = extract_scope(query, kb.glossary, explicit_scope)
        active = kb.active_cards(visible_sources)
        required, missing = requested_sources(query, kb.sources, sc.institution)
        available = {c["source_id"] for c in active}
        missing.extend(sorted(required - available))
        titles = title_sources(query, kb.sources)
        if titles:
            active = [c for c in active if c["source_id"] in titles]
        if capability_question(query) and not sc.institution:
            active = [c for c in active if c["source_id"] == "TURNITIN_AI_REPORT_GUIDE"]
        rows = retrieve(active, kb.sources, sc)
        g = gate(sc, rows, context_docs, missing_documents=missing)
        lang = sc.lang if sc.lang in L10N else "en"
        T = L10N[lang]
        applicable = sorted(g.applicable, key=lambda r: (r["card"]["authority_tier"], r["card"]["card_id"]))[:4]
        context = g.context[:2]
        if g.decision == "answer":
            top = kb.sources[applicable[0]["card"]["source_id"]]["title"]
            summary = T["answer"].format(n=len(applicable), top=top)
        elif g.decision == "context_only":
            summary = T["context_only"]
        elif g.decision == "clarify":
            summary = T["clarify"].format(c="; ".join(g.conflicts))
        else:
            summary = T["refuse"].format(r=g.reason)
        detectorish = bool(sc.topics & {"detector", "penalty"})
        out = {
            "run_id": run_id, "agent": AGENT_VERSION, "decision": g.decision, "reason": g.reason,
            "lang": lang, "l10n_review": L10N_REVIEW[lang], "summary": summary,
            "citations": [_cite(r, kb) for r in applicable] if g.decision in ("answer",) else [],
            "context_examples": [_cite(r, kb) for r in context] if g.decision in ("answer", "context_only") else [],
            "conflicts": g.conflicts, "unknowns": g.unknowns,
            "safe_next_step": (T["safe_detector"] if detectorish else T["safe"]) if g.decision in ("answer", "context_only") else None,
            "human_review_required": detectorish or bool(g.conflicts),
            "notice": T["not_decision"],
            "scope": sc.as_dict(),
        }
        llm_meta = {"used": False}
        if llm and g.decision in ("answer", "context_only"):
            out, llm_meta = _llm_rephrase(out, llm)
    record = {
        "run_id": run_id, "event_id": event_id, "utc": utc_now(), "agent": AGENT_VERSION,
        "model": llm_meta.get("model", "none (deterministic)"), "llm": llm_meta,
        "corpus_sha256": kb.corpus_sha256, "input_query": query, "input_lang": sc.lang,
        "scope": sc.as_dict(), "retrieved_ids": [r["card"]["card_id"] for r in rows],
        "retrieved_scores": {r["card"]["card_id"]: r["bm25"] for r in rows},
        "context_ids": [c["card_id"] for c in out["citations"] + out["context_examples"]],
        "citation_ids": [c["card_id"] for c in out["citations"]],
        "gate_decision": g.decision, "refusal_reason": g.reason if g.decision in ("refuse", "clarify") else None,
        "rationale_summary": f"topics={sorted(sc.topics)}; applicable={len(g.applicable)}; context={len(g.context)}; conflicts={len(g.conflicts)}",
        "unknowns": g.unknowns, "terminal": "complete", "latency_ms": t.ms,
        "cost_usd": 0.0 if not llm_meta.get("used") else None,
        "cost_note": "local, no paid API" if not llm_meta.get("used") else "local Ollama; compute cost not metered",
    }
    write_record(log_path, record)
    out["latency_ms"] = t.ms
    return out


def _llm_rephrase(out: dict, model_spec: str) -> tuple[dict, dict]:
    """model_spec like 'ollama:qwen2.5:14b'. Never called by tests."""
    _, model = model_spec.split(":", 1)
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    allowed = {c["card_id"] for c in out["citations"] + out["context_examples"]}
    prompt = (
        f"Answer in language '{out['lang']}' in at most 5 sentences. Use ONLY these evidence cards; "
        f"cite them as [card_id]; do not add rules; say what is unknown: {json.dumps(out['unknowns'])}.\n"
        + json.dumps(out["citations"] + out["context_examples"], ensure_ascii=False))
    body = json.dumps({"model": model, "stream": False, "options": {"temperature": 0, "seed": 7},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    meta = {"used": True, "model": model}
    try:
        req = urllib.request.Request(host + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        text = json.loads(urllib.request.urlopen(req, timeout=120).read())["message"]["content"]
    except Exception as e:  # noqa: BLE001
        meta.update(status="failed", error=str(e)[:200])
        return out, meta
    import re
    cited = set(re.findall(r"\[([A-Z0-9_]+#\d+)\]", text))
    if not cited or not cited <= allowed:
        meta.update(status="rejected_citation_violation", cited=sorted(cited))
        return out, meta
    out = dict(out, llm_text=text)
    meta.update(status="accepted", cited=sorted(cited))
    return out, meta
