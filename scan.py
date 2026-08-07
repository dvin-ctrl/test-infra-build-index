#!/usr/bin/env python3
"""
Stage 1 - find each target's job board, pull every posting, keyword-filter.

Nothing here is paid or authenticated. Ashby, Greenhouse and Lever all expose a
public JSON job board endpoint, which is what makes the whole index reproducible
by anyone with curl.

Two failure modes this file exists to prevent:

1. Acronym substring matching. "HIL" appears inside "while" and "child", so naive
   matching flagged 98% of all postings as test-infrastructure signals. Acronyms
   are matched case-sensitively with word boundaries; phrases case-insensitively
   with word boundaries.

2. Lever truncation. Lever's mode=json returns only the intro blurb in
   descriptionPlain; requirements live in a separate lists[] array. Reading only
   descriptionPlain captured 32% of each posting and silently produced false
   negatives - one company scored 0 signals across 58 postings until this was
   fixed. See lever_text().

Both stages cache to data/, so re-running is free and resumable.
"""
import json, os, re, time, html, datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from targets import TARGETS, CAREERS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
BOARDS_F = os.path.join(DATA, "boards.json")
POSTINGS_F = os.path.join(DATA, "postings.json")
META_F = os.path.join(DATA, "meta.json")

UA = {"User-Agent": "Mozilla/5.0 (compatible; test-infra-build-index/1.0)"}

ENDPOINTS = {
    "ashby":      "https://api.ashbyhq.com/posting-api/job-board/{s}?includeCompensation=true",
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true",
    "lever":      "https://api.lever.co/v0/postings/{s}?mode=json",
}

# Matched case-sensitively, with word boundaries. These are the ones that bite.
ACRONYMS = ["HIL", "DAQ", "PXI", "SIL", "MIL", "GSE", "SCADA", "CAN", "PLC"]
# Matched case-insensitively, with word boundaries.
PHRASES = [
    "labview", "teststand", "diadem", "veristand",
    "hardware-in-the-loop", "hardware in the loop",
    "data acquisition", "test automation", "test infrastructure", "test framework",
    "test stand", "test bench", "test rig", "telemetry", "ground station",
    "matlab", "simulink", "dspace", "vector canoe",
    "influxdb", "grafana", "timescale", "prometheus",
    "flight test", "integration and test", "verification and validation",
]

BOARD_PATTERNS = [
    ("greenhouse", re.compile(r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I)),
    ("lever",      re.compile(r"jobs\.lever\.co/([a-z0-9_-]+)", re.I)),
    ("ashby",      re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_.-]+)", re.I)),
]
BAD_SLUGS = {"embed", "job_board", "boards", "www", "jobs", "static", "v1"}


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or ""))


def lever_text(job):
    """Lever splits a posting across three places. Read all of them."""
    parts = [job.get("descriptionPlain") or job.get("description") or ""]
    for section in (job.get("lists") or []):
        parts.append(section.get("text") or "")
        parts.append(section.get("content") or "")
    parts.append(job.get("additionalPlain") or job.get("additional") or "")
    return strip_html("\n".join(parts))


def parse(provider, payload):
    out = []
    if provider == "lever":
        for j in payload if isinstance(payload, list) else []:
            out.append({"title": j.get("text", ""), "url": j.get("hostedUrl", ""),
                        "text": lever_text(j)})
    elif provider == "ashby":
        for j in payload.get("jobs", []):
            out.append({"title": j.get("title", ""), "url": j.get("jobUrl", ""),
                        "text": strip_html(j.get("descriptionPlain") or j.get("descriptionHtml") or "")})
    else:
        for j in payload.get("jobs", []):
            out.append({"title": j.get("title", ""), "url": j.get("absolute_url", ""),
                        "text": strip_html(j.get("content", ""))})
    return out


def try_board(provider, slug):
    try:
        r = requests.get(ENDPOINTS[provider].format(s=slug), headers=UA, timeout=25)
        if r.status_code != 200:
            return None
        jobs = parse(provider, r.json())
        return jobs if jobs else None
    except Exception:
        return None


def find_board(company, segment, slugs):
    for slug in slugs:
        for provider in ENDPOINTS:
            jobs = try_board(provider, slug)
            if jobs:
                return {"company": company, "segment": segment, "provider": provider,
                        "slug": slug, "job_count": len(jobs)}, jobs
            time.sleep(0.03)
    # fall back to reading the careers page for a real board token
    for url in CAREERS.get(company, []):
        try:
            body = requests.get(url, headers=UA, timeout=30).text
        except Exception:
            continue
        for provider, pat in BOARD_PATTERNS:
            for slug in pat.findall(body):
                slug = slug.strip().lower()
                if slug in BAD_SLUGS:
                    continue
                jobs = try_board(provider, slug)
                if jobs:
                    return {"company": company, "segment": segment, "provider": provider,
                            "slug": slug, "job_count": len(jobs)}, jobs
    return {"company": company, "segment": segment, "provider": None,
            "slug": None, "job_count": 0}, []


def signals(text):
    found = []
    for a in ACRONYMS:
        if re.search(r"\b" + a + r"\b", text):          # case-sensitive on purpose
            found.append(a)
    for p in PHRASES:
        if re.search(r"\b" + re.escape(p) + r"\b", text, re.I):
            found.append(p)
    return sorted(set(found))


def naive_signals(text):
    """What a careless implementation does. Kept to quantify the difference."""
    low = text.lower()
    return [t for t in ACRONYMS + PHRASES if t.lower() in low]


def main():
    boards = {b["company"]: b for b in json.load(open(BOARDS_F))} if os.path.exists(BOARDS_F) else {}
    postings = json.load(open(POSTINGS_F)) if os.path.exists(POSTINGS_F) else {}

    todo = [(c, s, sl) for c, (s, sl) in TARGETS.items() if c not in boards]
    if todo:
        print(f"probing {len(todo)} companies ({len(boards)} cached)")
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = [ex.submit(find_board, c, s, sl) for c, s, sl in todo]
            for f in as_completed(futs):
                meta, jobs = f.result()
                boards[meta["company"]] = meta
                if jobs:
                    postings[meta["company"]] = jobs
                    print(f"  OK {meta['company']:<22} {meta['provider']:<11} {len(jobs)}")
                else:
                    print(f"  -- {meta['company']}")
        json.dump(list(boards.values()), open(BOARDS_F, "w"), indent=1)
        json.dump(postings, open(POSTINGS_F, "w"))
        # Stamp when postings were pulled. Carried through to the page so a later
        # re-render cannot misdate the data, and so dead links read as an expected
        # property of a dated snapshot rather than as a broken page.
        json.dump({"scanned": datetime.date.today().isoformat()}, open(META_F, "w"))

    total = sum(len(v) for v in postings.values())
    strict = sum(1 for v in postings.values() for j in v if signals(j["text"]))
    naive = sum(1 for v in postings.values() for j in v if naive_signals(j["text"]))
    live = len([b for b in boards.values() if b["job_count"]])

    print(f"\n{live}/{len(boards)} boards resolved, {total:,} postings")
    print(f"naive substring match  {naive:,} ({naive/total*100:.1f}%)")
    print(f"strict boundary match  {strict:,} ({strict/total*100:.1f}%)")
    print(f"false positives cut    {naive-strict:,} ({(naive-strict)/naive*100:.1f}% of naive hits)")
    print("\nnext: OPENAI_API_KEY=... python3 classify.py")


if __name__ == "__main__":
    main()
