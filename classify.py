#!/usr/bin/env python3
"""
Phase 3 - classify each signal-bearing posting.

The question is not "does this mention test tooling" (keywords answered that).
It is "is this company paying an engineer to BUILD test infrastructure, or to
OPERATE tests using something they already have?" Only the first is a Nominal wedge.

Cost control: we send keyword-centred excerpts, not whole postings. A req averages
~9.4k chars; the tool names cluster in 2-3 places. Excerpting cuts input tokens ~70%
and measurably improves precision by removing boilerplate the model would otherwise
weigh (benefits, EEO statements, company boilerplate).

Resumable: every result is cached by (company, url).
"""
import json, os, re, hashlib, sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(__file__)
CACHE = os.path.join(HERE, "data", "classified.json")
_p = os.path.join(HERE, "data", "postings.json")
if not os.path.exists(_p):
    raise SystemExit("data/postings.json missing. Run python3 scan.py first.")
POSTINGS = json.load(open(_p))
BOARDS = {b["company"]: b for b in json.load(open(os.path.join(HERE, "data", "boards.json")))}

KEY = os.environ.get("OPENAI_API_KEY")
if not KEY:
    sys.exit("set OPENAI_API_KEY in your environment (see README)")
HDRS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
MODEL = "gpt-4o-mini"

ACRONYMS = ["HIL", "DAQ", "PXI", "SIL", "MIL", "GSE", "SCADA", "CAN", "PLC"]
PHRASES = [
    "labview", "teststand", "diadem", "veristand",
    "hardware-in-the-loop", "hardware in the loop",
    "data acquisition", "test automation", "test infrastructure", "test framework",
    "test stand", "test bench", "test rig", "telemetry", "ground station",
    "matlab", "simulink", "dspace", "vector canoe",
    "influxdb", "grafana", "timescale", "prometheus",
    "flight test", "integration and test", "verification and validation",
]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "posture": {"type": "string", "enum": ["builds_tooling", "operates_tests", "neither"]},
        "stack": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["posture", "stack", "evidence", "confidence"],
}

SYSTEM = """You read engineering job descriptions and decide one thing: is this company paying this hire to BUILD AND MAINTAIN test/data infrastructure, or to OPERATE tests using tooling that already exists?

posture:
- "builds_tooling": the req asks the hire to develop, build, architect, own, or maintain test infrastructure, data acquisition pipelines, test automation frameworks, telemetry systems, HIL rigs, or internal tooling. Verbs like develop/build/design/architect/own applied to infrastructure.
- "operates_tests": the req is about running, executing, or analysing tests with existing tooling. The hire is a user of the stack, not its author.
- "neither": the tool names are incidental (e.g. listed only as a nice-to-have skill, or the role is unrelated).

stack: named test/data tools ONLY, verbatim as written (LabVIEW, TestStand, MATLAB, Simulink, dSPACE, InfluxDB, Grafana, PXI, DAQ, ...). Empty array if none named. Do not infer tools that are not written.

evidence: one verbatim sentence from the posting, max 220 chars, that justifies the posture. Must be copied exactly from the text, not paraphrased. If you cannot find one, return "".

confidence: high only if the evidence sentence is explicit about building vs operating."""


def excerpts(text, width=420, cap=4):
    """Keyword-centred windows, merged when they overlap."""
    spans = []
    for a in ACRONYMS:
        for m in re.finditer(r"\b" + a + r"\b", text):
            spans.append((m.start(), m.end()))
    for p in PHRASES:
        for m in re.finditer(r"\b" + re.escape(p) + r"\b", text, re.I):
            spans.append((m.start(), m.end()))
    if not spans:
        return text[:width]
    spans.sort()
    wins, cur = [], None
    for s, e in spans:
        lo, hi = max(0, s - width // 2), min(len(text), e + width // 2)
        if cur and lo <= cur[1]:
            cur = (cur[0], max(cur[1], hi))
        else:
            if cur:
                wins.append(cur)
            cur = (lo, hi)
    if cur:
        wins.append(cur)
    return "\n...\n".join(text[a:b] for a, b in wins[:cap])


def signals(text):
    out = []
    for a in ACRONYMS:
        if re.search(r"\b" + a + r"\b", text):
            out.append(a)
    for p in PHRASES:
        if re.search(r"\b" + re.escape(p) + r"\b", text, re.I):
            out.append(p)
    return sorted(set(out))


def classify(company, job):
    body = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"COMPANY: {company}\nTITLE: {job['title']}\n\nEXCERPTS:\n{excerpts(job['text'])}"},
        ],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "posture", "strict": True, "schema": SCHEMA}},
    }
    for attempt in range(4):
        try:
            r = requests.post("https://api.openai.com/v1/chat/completions",
                              headers=HDRS, json=body, timeout=90)
            if r.status_code == 200:
                out = json.loads(r.json()["choices"][0]["message"]["content"])
                out["usage"] = r.json().get("usage", {})
                return out
            if r.status_code in (429, 500, 502, 503):
                import time; time.sleep(2 * (attempt + 1)); continue
            return None
        except Exception:
            import time; time.sleep(2 * (attempt + 1))
    return None


def main():
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    todo = []
    for co, jobs in POSTINGS.items():
        for j in jobs:
            s = signals(j["text"])
            if not s:
                continue
            k = hashlib.md5(f"{co}|{j['url']}".encode()).hexdigest()
            if k in cache:
                continue
            todo.append((k, co, j, s))

    print(f"{len(cache)} cached, {len(todo)} to classify")
    if not todo:
        return summarise(cache)

    done = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(classify, co, j): (k, co, j, s) for k, co, j, s in todo}
        for f in as_completed(futs):
            k, co, j, s = futs[f]
            res = f.result()
            if res:
                cache[k] = {"company": co, "title": j["title"], "url": j["url"],
                            "keywords": s, **res}
            done += 1
            if done % 50 == 0:
                json.dump(cache, open(CACHE, "w"))
                print(f"  {done}/{len(todo)}")
    json.dump(cache, open(CACHE, "w"))
    summarise(cache)


def summarise(cache):
    from collections import Counter
    tin = sum(v.get("usage", {}).get("prompt_tokens", 0) for v in cache.values())
    tout = sum(v.get("usage", {}).get("completion_tokens", 0) for v in cache.values())
    print(f"\nclassified {len(cache)} postings")
    print("posture:", Counter(v["posture"] for v in cache.values()).most_common())
    print(f"tokens: {tin:,} in / {tout:,} out")
    print(f"cost:   ${tin/1e6*0.15 + tout/1e6*0.60:.3f}")
    builds = Counter(v["company"] for v in cache.values() if v["posture"] == "builds_tooling")
    print("\ntop builds_tooling accounts:")
    for co, n in builds.most_common(15):
        print(f"  {co:<24} {n}")


if __name__ == "__main__":
    main()
