#!/usr/bin/env python3
"""
Phase 4 - suppress, score, rank, emit index.json for the page.

Scoring is deliberately deterministic. The LLM extracts posture and stack per
posting; Python decides the account score. A prompt change can move an individual
verdict but cannot silently reshuffle the ranking.
"""
import json, os, re
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
_cl = os.path.join(HERE, "data", "classified.json")
if not os.path.exists(_cl):
    raise SystemExit("data/classified.json missing. Run:\n"
                     "  python3 scan.py\n"
                     "  OPENAI_API_KEY=sk-... python3 classify.py")
CL = json.load(open(_cl))
BOARDS = {b["company"]: b for b in json.load(open(os.path.join(HERE, "data", "boards.json")))}
POSTINGS = json.load(open(os.path.join(HERE, "data", "postings.json")))

from targets import SUPPRESSED as CUSTOMERS, COMPETITORS, COMPETITOR_INCUMBENT

# Legacy stacks Nominal explicitly positions against (Connect launch post names
# TestStand and LabVIEW by name). A named legacy tool is a displacement signal.
LEGACY = {"labview", "teststand", "diadem", "veristand", "dspace", "matlab", "simulink", "pxi"}
DIY = {"influxdb", "grafana", "timescale", "prometheus"}  # rolled-their-own telemetry stack

# A tool named in one req out of eighty-six is one engineer's nice-to-have. The same
# tool named once at an account with thirteen test reqs is a real signal. So the bar is
# corroboration OR prevalence: a tool scores if it appears in at least MIN_MENTIONS
# postings, or in at least MIN_RATE of that account's test-related postings. A flat
# count alone punished small boards and pushed the single best-evidenced account
# (one req naming both LabVIEW and TestStand) down eight places.
MIN_MENTIONS = 2
MIN_RATE = 0.05


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# The model returns tool names verbatim, so "LabVIEW"/"LabView"/"Labview" arrive as
# three distinct strings and would be counted three times. Canonicalise on the
# normalised key; anything unmapped keeps its most common surface form.
CANON = {
    "labview": "LabVIEW", "teststand": "TestStand", "nteststand": "TestStand",
    "diadem": "DIAdem", "veristand": "VeriStand", "matlab": "MATLAB",
    "simulink": "Simulink", "dspace": "dSPACE", "pxi": "PXI", "influxdb": "InfluxDB",
    "grafana": "Grafana", "timescale": "TimescaleDB", "timescaledb": "TimescaleDB",
    "prometheus": "Prometheus", "daq": "DAQ", "scada": "SCADA", "plc": "PLC",
    "canbus": "CAN bus", "can": "CAN bus", "vectorcanoe": "Vector CANoe",
    "canoe": "Vector CANoe", "ni": "NI", "nationalinstruments": "NI",
    "hil": "HIL", "hardwareintheloop": "HIL",
}


def canon(tool):
    k = norm(tool)
    return CANON.get(k, (tool or "").strip())


def main():
    per = defaultdict(lambda: {"builds": [], "operates": [], "neither": 0, "stack": Counter()})
    for v in CL.values():
        co = v["company"]
        p = per[co]
        if v["posture"] == "builds_tooling":
            p["builds"].append(v)
        elif v["posture"] == "operates_tests":
            p["operates"].append(v)
        else:
            p["neither"] += 1
        for t in v.get("stack", []):
            if t and len(t) < 30:
                p["stack"][canon(t)] += 1

    rows, suppressed, competitors = [], [], []
    for co, p in per.items():
        b = BOARDS.get(co, {})
        # Carry counts, not just presence. Presence alone made a tool named once
        # render identically to one named sixteen times.
        legacy_hits = sorted(((t, n) for t, n in p["stack"].items() if norm(t) in LEGACY),
                             key=lambda x: (-x[1], x[0]))
        diy_hits = sorted(((t, n) for t, n in p["stack"].items() if norm(t) in DIY),
                          key=lambda x: (-x[1], x[0]))
        sig = len(p["builds"]) + len(p["operates"]) or 1

        def scores(n):
            return n >= MIN_MENTIONS or (n / sig) >= MIN_RATE

        strong_legacy = [t for t, n in legacy_hits if scores(n)]
        strong_diy = [t for t, n in diy_hits if scores(n)]

        # deterministic score, 0-8
        nb = len(p["builds"])
        score = 0
        score += 3 if nb >= 15 else 2 if nb >= 8 else 1 if nb >= 3 else 0   # build volume
        score += 2 if len(strong_legacy) >= 2 else 1 if strong_legacy else 0  # legacy displacement
        score += 1 if strong_diy else 0                                      # DIY telemetry stack
        total = len(p["builds"]) + len(p["operates"])
        ratio = nb / total if total else 0
        score += 2 if ratio >= 0.6 else 1 if ratio >= 0.4 else 0             # build-heavy posture

        tier = "A" if score >= 6 else "B" if score >= 4 else "C"
        best = sorted(p["builds"], key=lambda x: (x["confidence"] != "high", -len(x.get("evidence") or "")))
        row = {
            "company": co,
            "segment": b.get("segment", "?"),
            "board": b.get("provider"),
            "total_postings": len(POSTINGS.get(co, [])),
            "signal_postings": len(p["builds"]) + len(p["operates"]) + p["neither"],
            "builds": nb,
            "operates": len(p["operates"]),
            "discarded_by_llm": p["neither"],
            "build_ratio": round(ratio, 2),
            "legacy": [[t, n] for t, n in legacy_hits],
            "legacy_scoring": strong_legacy,
            "diy": [[t, n] for t, n in diy_hits],
            "stack_top": [[t, n] for t, n in p["stack"].most_common(8)],
            "score": score,
            "tier": tier,
            "evidence": (best[0].get("evidence") or "")[:230] if best else "",
            "evidence_title": best[0]["title"] if best else "",
            "evidence_url": best[0]["url"] if best else "",
        }
        if co in COMPETITOR_INCUMBENT:
            row["incumbent_note"] = COMPETITOR_INCUMBENT[co]
        if co in CUSTOMERS:
            row["excluded_reason"] = CUSTOMERS[co]
            row["excluded_kind"] = "customer"
            suppressed.append(row)
        elif co in COMPETITORS:
            row["excluded_reason"] = COMPETITORS[co]
            row["excluded_kind"] = "competitor"
            competitors.append(row)
        else:
            rows.append(row)

    rows.sort(key=lambda r: (-r["score"], -r["builds"]))

    meta_f = os.path.join(HERE, "data", "meta.json")
    scanned = json.load(open(meta_f))["scanned"] if os.path.exists(meta_f) else "unknown"

    out = {
        "scanned": scanned,
        "companies_scanned": len(BOARDS),
        "boards_resolved": len([b for b in BOARDS.values() if b.get("job_count")]),
        "total_postings": sum(len(v) for v in POSTINGS.values()),
        "keyword_matched": len(CL),
        "llm_discarded": sum(1 for v in CL.values() if v["posture"] == "neither"),
        "builds_total": sum(1 for v in CL.values() if v["posture"] == "builds_tooling"),
        "operates_total": sum(1 for v in CL.values() if v["posture"] == "operates_tests"),
        "rows": rows,
        "suppressed": suppressed,
        "competitors": competitors,
        "min_mentions": MIN_MENTIONS,
        "min_rate": MIN_RATE,
    }
    json.dump(out, open(os.path.join(HERE, "data", "index.json"), "w"), indent=1)

    print(f"scanned {out['companies_scanned']} companies / {out['boards_resolved']} boards resolved")
    print(f"{out['total_postings']} postings -> {out['keyword_matched']} keyword -> "
          f"{out['builds_total']} build-posture ({out['llm_discarded']} discarded by LLM)")
    print(f"\nEXCLUDED as customers:   {[r['company'] for r in suppressed]}")
    print(f"EXCLUDED as competitors: {[r['company'] for r in competitors]}\n")
    print(f"{'#':>2} {'company':<22} {'seg':<22} {'T':<2} {'sc':>2} {'bld':>4} {'ops':>4} {'legacy'}")
    for i, r in enumerate(rows[:24], 1):
        print(f"{i:>2} {r['company']:<22} {r['segment']:<22} {r['tier']:<2} {r['score']:>2} "
              f"{r['builds']:>4} {r['operates']:>4} {', '.join(f'{t}x{n}' for t, n in r['legacy'][:3])}")


if __name__ == "__main__":
    main()
