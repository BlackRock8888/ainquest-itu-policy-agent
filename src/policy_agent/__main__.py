"""CLI.

  python -m policy_agent ask "question" [--log runs/decisions.jsonl] [--llm ollama:LOCAL_MODEL]
  python -m policy_agent eval evals/dev.jsonl [--out runs/dev.json]
  python -m policy_agent replay evals/scenarios/uaeu_progressive_ar_ru.json [--out runs/replay.json]
  python -m policy_agent export-upstream OUT_DIR
  python -m policy_agent standards
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .agent import answer
from .evaluate import evaluate, load_items
from .kb import load_kb
from .replay import check, run_scenario


def _dump(obj, out: str | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=1)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text + "\n", encoding="utf-8")
    print(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="policy_agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask"); a.add_argument("query"); a.add_argument("--log"); a.add_argument("--llm")
    e = sub.add_parser("eval"); e.add_argument("path"); e.add_argument("--out"); e.add_argument("--log")
    r = sub.add_parser("replay"); r.add_argument("path"); r.add_argument("--out"); r.add_argument("--log")
    x = sub.add_parser("export-upstream"); x.add_argument("out_dir")
    sub.add_parser("standards")
    args = ap.parse_args(argv)
    kb = load_kb()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if args.cmd == "ask":
        _dump(answer(args.query, kb, log_path=Path(args.log) if args.log else None, llm=args.llm), None)
    elif args.cmd == "eval":
        res = evaluate(load_items(Path(args.path)), kb, Path(args.log) if args.log else None)
        res = {"run_utc": stamp, "split": args.path, **res}
        _dump(res, args.out)
        return 0 if res["overall_pass"]["ok"] == res["items"] else 1
    elif args.cmd == "replay":
        p = Path(args.path)
        results = run_scenario(p, kb, Path(args.log) if args.log else None)
        rep = check(results, json.loads(p.read_text(encoding="utf-8")))
        _dump({"run_utc": stamp, "scenario": args.path, "corpus_sha256": kb.corpus_sha256,
               "checks": rep, "results": results}, args.out)
        return 0 if all(c["pass"] for c in rep) else 1
    elif args.cmd == "export-upstream":
        from .upstream_export import export
        print(json.dumps(export(kb, Path(args.out_dir)), indent=1))
    elif args.cmd == "standards":
        from .standards import mapping
        print(json.dumps(mapping(), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
