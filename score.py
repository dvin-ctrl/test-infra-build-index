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

from targets import SUPPRESSED as CUSTOMERS

# Legacy stacks Nominal explicitly positions against (Connect launch post names
# TestStand and LabVIEW by name). A named legacy tool is a displacement signal.
LEGACY = {"labview", "teststand", "diadem", "veristand", "dspace", "matlab", "simulink", "pxi"}
DIY = {"influxdb", "grafana", "timescale", "prometheus"}  # rolled-their-own telemetry stack


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

    rows, suppressed = [], []
    for co, p in per.items():
        b = BOARDS.get(co, {})
        stack_norm = {norm(t) for t in p["stack"]}
        legacy_hits = sorted({t for t in p["stack"] if norm(t) in LEGACY})
        diy_hits = sorted({t for t in p["stack"] if norm(t) in DIY})

        # deterministic score, 0-8
        nb = len(p["builds"])
        score = 0
        score += 3 if nb >= 15 else 2 if nb >= 8 else 1 if nb >= 3 else 0   # build volume
        score += 2 if len(legacy_hits) >= 2 else 1 if legacy_hits else 0     # legacy displacement
        score += 1 if diy_hits else 0                                        # DIY telemetry stack
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
            "legacy": legacy_hits,
            "diy": diy_hits,
            "stack_top": [t for t, _ in p["stack"].most_common(6)],
            "score": score,
            "tier": tier,
            "evidence": (best[0].get("evidence") or "")[:230] if best else "",
            "evidence_title": best[0]["title"] if best else "",
            "evidence_url": best[0]["url"] if best else "",
        }
        if co in CUSTOMERS:
            row["suppressed_reason"] = CUSTOMERS[co]
            suppressed.append(row)
        else:
            rows.append(row)

    rows.sort(key=lambda r: (-r["score"], -r["builds"]))

    out = {
        "generated_note": "counts are live at scan time",
        "companies_scanned": len(BOARDS),
        "boards_resolved": len([b for b in BOARDS.values() if b.get("job_count")]),
        "total_postings": sum(len(v) for v in POSTINGS.values()),
        "keyword_matched": len(CL),
        "llm_discarded": sum(1 for v in CL.values() if v["posture"] == "neither"),
        "builds_total": sum(1 for v in CL.values() if v["posture"] == "builds_tooling"),
        "operates_total": sum(1 for v in CL.values() if v["posture"] == "operates_tests"),
        "rows": rows,
        "suppressed": suppressed,
    }
    json.dump(out, open(os.path.join(HERE, "data", "index.json"), "w"), indent=1)

    print(f"scanned {out['companies_scanned']} companies / {out['boards_resolved']} boards resolved")
    print(f"{out['total_postings']} postings -> {out['keyword_matched']} keyword -> "
          f"{out['builds_total']} build-posture ({out['llm_discarded']} discarded by LLM)")
    print(f"\nSUPPRESSED (existing customers): {[r['company'] for r in suppressed]}\n")
    print(f"{'#':>2} {'company':<22} {'seg':<22} {'T':<2} {'sc':>2} {'bld':>4} {'ops':>4} {'legacy'}")
    for i, r in enumerate(rows[:24], 1):
        print(f"{i:>2} {r['company']:<22} {r['segment']:<22} {r['tier']:<2} {r['score']:>2} "
              f"{r['builds']:>4} {r['operates']:>4} {', '.join(r['legacy'][:3])}")


if __name__ == "__main__":
    main()
