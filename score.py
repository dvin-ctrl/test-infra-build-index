#!/usr/bin/env python3
"""
Stage 3 - exclude, score, rank. Emits data/index.json for render.py.

Scoring philosophy, hardened by findings 1-6:

  RANK ON COMMITMENTS, NOT VOCABULARY. The only inputs to the score are the
  number of build-posture reqs and the build-to-operate ratio, both of which are
  statements of what a company is paying people to do. Detected tooling is
  DISPLAY-ONLY context: finding 5 showed 67% of tool mentions were skills-list
  filler, and finding 6 showed the model's operates/listed judgement itself
  drifts on "or equivalent" sentences. A signal that unreliable may inform a
  conversation; it may not order the account list.

Every displayed tool carries the URL of a posting whose raw text provably
contains it (checked here, at build time, not by the reader). A tool with no
clean source posting is shown only in the listed-only bucket.
"""
import json, os, re
from collections import Counter, defaultdict

from targets import SUPPRESSED as CUSTOMERS, COMPETITORS, COMPETITOR_INCUMBENT

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

_cl = os.path.join(DATA, "classified.json")
if not os.path.exists(_cl):
    raise SystemExit("data/classified.json missing. Run:\n"
                     "  python3 scan.py\n"
                     "  OPENAI_API_KEY=sk-... python3 classify.py")
CL = json.load(open(_cl))
BOARDS = {b["company"]: b for b in json.load(open(os.path.join(DATA, "boards.json")))}
POSTINGS = json.load(open(os.path.join(DATA, "postings.json")))

LEGACY = {"labview", "teststand", "diadem", "veristand", "dspace", "matlab", "simulink", "pxi",
          "matlabsimulink"}
DIY = {"influxdb", "grafana", "timescale", "timescaledb", "prometheus"}

# Display threshold only (dims thin evidence). Not a scoring input.
MIN_MENTIONS = 2
MIN_RATE = 0.05

# Finding 6: 12% of the model's "operates" calls sat inside sentences whose own
# grammar marks the tool as one interchangeable option. The model cannot be
# trusted with this distinction, so it is enforced deterministically: a tool
# whose sentence contains any of these markers is treated as listed, whatever
# the model said.
INTERCHANGE = re.compile(
    r"\b(or similar|or equivalent|or other|or comparable|such as|e\.g\.|and/or)\b", re.I)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


CANON = {
    "labview": "LabVIEW", "teststand": "TestStand", "nteststand": "TestStand",
    "diadem": "DIAdem", "veristand": "VeriStand", "matlab": "MATLAB",
    "matlabsimulink": "MATLAB/Simulink",
    "simulink": "Simulink", "dspace": "dSPACE", "pxi": "PXI", "influxdb": "InfluxDB",
    "grafana": "Grafana", "timescale": "TimescaleDB", "timescaledb": "TimescaleDB",
    "prometheus": "Prometheus", "daq": "DAQ", "scada": "SCADA", "plc": "PLC",
    "canbus": "CAN bus", "can": "CAN bus", "vectorcanoe": "Vector CANoe",
    "canoe": "Vector CANoe", "ni": "NI", "nationalinstruments": "NI",
    "hil": "HIL", "hardwareintheloop": "HIL", "hitl": "HITL", "sitl": "SIL",
}


def canon(tool):
    return CANON.get(norm(tool), (tool or "").strip())


RAW = {co: {p["url"]: p["text"] for p in ps} for co, ps in POSTINGS.items()}


def sentence_for(company, tool, url):
    """The sentence around `tool` in the posting at `url`, or None if the tool
    is not literally present in the raw text. Presence here is what licenses a
    chip to link to this posting."""
    text = re.sub(r"\s+", " ", RAW.get(company, {}).get(url, ""))
    base = tool.split("/")[0]  # "MATLAB/Simulink" -> search "MATLAB"
    m = re.search(r"[^.<>|]{0,150}\b" + re.escape(base) + r"\b[^.<>|]{0,90}", text, re.I)
    return m.group(0) if m else None


def main():
    per = defaultdict(lambda: {"builds": [], "operates": [], "neither": 0,
                               "run_urls": defaultdict(list), "listed": Counter()})
    for v in CL.values():
        p = per[v["company"]]
        if v["posture"] == "builds_tooling":
            p["builds"].append(v)
        elif v["posture"] == "operates_tests":
            p["operates"].append(v)
        else:
            p["neither"] += 1
        for t in v.get("tools", []):
            name, usage = canon(t.get("name") or ""), t.get("usage")
            if not name or len(name) >= 30:
                continue
            if usage == "operates":
                p["run_urls"][name].append(v["url"])
            else:
                p["listed"][name] += 1

    rows, suppressed, competitors = [], [], []
    for co, p in per.items():
        b = BOARDS.get(co, {})

        # Deterministic operates-filter (finding 6). For each claimed tool,
        # keep only postings where the tool is literally present AND its
        # sentence does not mark it as interchangeable. Distinct sentences,
        # not postings, are what get counted (finding 5).
        operated = {}   # tool -> {"n": distinct clean contexts, "url": first clean source}
        for tool, urls in p["run_urls"].items():
            seen, src, demoted = set(), None, 0
            for u in urls:
                sent = sentence_for(co, tool, u)
                if sent is None:
                    continue
                if INTERCHANGE.search(sent):
                    demoted += 1
                    continue
                key = re.sub(r"[^a-z ]", "", sent.lower()).strip()[:90]
                if key not in seen:
                    seen.add(key)
                    src = src or u
            if seen:
                operated[tool] = {"n": len(seen), "url": src}
            if demoted:
                p["listed"][tool] += demoted

        legacy = sorted(((t, d["n"], d["url"]) for t, d in operated.items()
                         if norm(t) in LEGACY), key=lambda x: (-x[1], x[0]))
        diy = sorted(((t, d["n"], d["url"]) for t, d in operated.items()
                      if norm(t) in DIY), key=lambda x: (-x[1], x[0]))
        stack = sorted(((t, d["n"], d["url"]) for t, d in operated.items()),
                       key=lambda x: (-x[1], x[0]))

        # Score: build commitments only. 0-5.
        nb = len(p["builds"])
        total = nb + len(p["operates"])
        ratio = nb / total if total else 0
        score = (3 if nb >= 15 else 2 if nb >= 8 else 1 if nb >= 3 else 0) \
              + (2 if ratio >= 0.6 else 1 if ratio >= 0.4 else 0)
        tier = "A" if score >= 4 else "B" if score >= 3 else "C"

        best = sorted(p["builds"], key=lambda x: (x["confidence"] != "high",
                                                  -len(x.get("evidence") or "")))
        row = {
            "company": co,
            "segment": b.get("segment", "?"),
            "board": b.get("provider"),
            "total_postings": len(POSTINGS.get(co, [])),
            "signal_postings": nb + len(p["operates"]) + p["neither"],
            "builds": nb,
            "operates": len(p["operates"]),
            "discarded_by_llm": p["neither"],
            "build_ratio": round(ratio, 2),
            "legacy": [[t, n, u] for t, n, u in legacy],
            "diy": [[t, n, u] for t, n, u in diy],
            "stack_top": [[t, n, u] for t, n, u in stack[:8]],
            "listed_only": sorted(([t, n] for t, n in p["listed"].items()
                                   if t not in operated), key=lambda x: (-x[1], x[0]))[:6],
            "score": score,
            "tier": tier,
            "evidence": (best[0].get("evidence") or "")[:230] if best else "",
            "evidence_title": best[0]["title"] if best else "",
            "evidence_url": best[0]["url"] if best else "",
        }
        if co in COMPETITOR_INCUMBENT:
            row["incumbent_note"] = COMPETITOR_INCUMBENT[co]
        if co in CUSTOMERS:
            row["excluded_reason"], row["excluded_kind"] = CUSTOMERS[co], "customer"
            suppressed.append(row)
        elif co in COMPETITORS:
            row["excluded_reason"], row["excluded_kind"] = COMPETITORS[co], "competitor"
            competitors.append(row)
        else:
            rows.append(row)

    rows.sort(key=lambda r: (-r["score"], -r["builds"]))

    meta_f = os.path.join(DATA, "meta.json")
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
        "min_mentions": MIN_MENTIONS,
        "min_rate": MIN_RATE,
        "rows": rows,
        "suppressed": suppressed,
        "competitors": competitors,
    }
    json.dump(out, open(os.path.join(DATA, "index.json"), "w"), indent=1)

    print(f"scanned {out['companies_scanned']} companies / {out['boards_resolved']} boards resolved")
    print(f"{out['total_postings']} postings -> {out['keyword_matched']} keyword -> "
          f"{out['builds_total']} build-posture ({out['llm_discarded']} discarded by LLM)")
    print(f"\nEXCLUDED as customers:   {[r['company'] for r in suppressed]}")
    print(f"EXCLUDED as competitors: {[r['company'] for r in competitors]}\n")
    print(f"{'#':>2} {'company':<22} {'seg':<22} {'T':<2} {'sc':>2} {'bld':>4} {'ops':>4}  operated legacy (clean, linked)")
    for i, r in enumerate(rows[:20], 1):
        leg = ", ".join(f"{t}x{n}" for t, n, _ in r["legacy"][:3])
        print(f"{i:>2} {r['company']:<22} {r['segment']:<22} {r['tier']:<2} {r['score']:>2} "
              f"{r['builds']:>4} {r['operates']:>4}  {leg}")


if __name__ == "__main__":
    main()
