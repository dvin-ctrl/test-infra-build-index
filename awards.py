#!/usr/bin/env python3
"""
Stage 5 (new spine) - federal awards with test obligations, joined to build posture.

The strongest row this system can produce is a JOIN:
  award text names a funded test obligation  x  open reqs staffing to build the
  test infrastructure for it. One layer is a list; two layers is an argument.

Source: USAspending API. Free, public, no auth. Every filter here is a filed
fact: dollar amount, agency, date, and the award description text written into
the contract record itself. Verbatim quotes are substrings of that record, so
verification is trivial by construction.

Recipient-name trap (learned on Prospeo /enrich-company): a keyword search
returns whatever recipient matches loosely, so every hit is validated by token
overlap between our target name and the legal recipient name, and generic
one-word names are additionally required to carry a qualifier token before they
are accepted. Rejects are logged, not silently dropped.
"""
import json, os, re, time
import requests

from targets import TARGETS, SUPPRESSED, COMPETITORS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "awards.json")

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Test obligations as they appear in federal award descriptions. NOTE: this
# language is common in prime contractors' DT&E awards and RARE in venture-backed
# startups' awards, whose descriptions are mission names and SBIR titles. It is
# therefore a bonus flag on a kept award, never a gate: gating on it produced
# zero recall across all 46 targets on the first run, because the phrase list
# had been validated against Northrop and Lockheed awards, the wrong population.
TEST_TERMS = re.compile(
    r"\b(flight test(?:s|ing)?|qualification test(?:s|ing)?|qual test(?:s|ing)?|"
    r"environmental test(?:s|ing)?|developmental test(?:s|ing)?|operational test(?:s|ing)?|"
    r"test and evaluation|DT&E|OT&E|ground test(?:s|ing)?|static fire|"
    r"hardware.in.the.loop|test campaign|test program|flight demonstration(?:s)?|"
    r"test range|flight experiment(?:s)?|instrumentation)\b", re.I)

STOP = {"inc", "llc", "corp", "corporation", "company", "co", "ltd", "the", "of"}

# One-word names that collide with unrelated recipients. These only accept a
# recipient whose name also carries one of the qualifier tokens.
AMBIGUOUS = {
    "Apex": {"space", "technology"},
    "Plus": {"ai", "automation"},
    "Electra": {"aero"},
    "Divergent": {"technologies", "3d", "adaptive"},
    "Mach Industries": {"mach"},
}


def tokens(name):
    return [t for t in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if t not in STOP]


def recipient_ok(company, recipient):
    r = (recipient or "").lower()
    need = tokens(company)
    if not all(t in r for t in need):
        return False
    if company in AMBIGUOUS and not any(q in r for q in AMBIGUOUS[company]):
        return False
    return True


def fetch(company):
    body = {
        "filters": {
            "recipient_search_text": [company],
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": "2024-01-01", "end_date": "2026-08-09"}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Description",
                   "Start Date", "End Date", "Awarding Agency", "Awarding Sub Agency",
                   "generated_internal_id"],
        "page": 1, "limit": 40, "sort": "Award Amount", "order": "desc",
    }
    for attempt in range(3):
        try:
            r = requests.post(API, json=body, timeout=60)
            if r.status_code == 200:
                return r.json().get("results", [])
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return []


def main():
    excluded = set(SUPPRESSED) | set(COMPETITORS)
    targets = [c for c in TARGETS if c not in excluded]

    results, rejects = {}, []
    for co in targets:
        rows = fetch(co)
        keep = []
        for a in rows:
            if not recipient_ok(co, a.get("Recipient Name")):
                rejects.append((co, a.get("Recipient Name")))
                continue
            desc = a.get("Description") or ""
            m = TEST_TERMS.search(desc)
            if m:
                i = max(0, m.start() - 80)
                quote = re.sub(r"\s+", " ", desc[i:m.end() + 120]).strip()
            else:
                quote = re.sub(r"\s+", " ", desc[:220]).strip()
            keep.append({
                "award_id": a.get("Award ID"),
                "recipient": a.get("Recipient Name"),
                "amount": a.get("Award Amount"),
                "agency": a.get("Awarding Agency"),
                "sub_agency": a.get("Awarding Sub Agency"),
                "start": a.get("Start Date"),
                "end": a.get("End Date"),
                "test_language": m.group(0) if m else None,
                "quote": quote,
                "url": f"https://www.usaspending.gov/award/{a.get('generated_internal_id')}",
            })
        if keep:
            results[co] = sorted(keep, key=lambda x: -(x["amount"] or 0))[:6]
        tl = sum(1 for k in keep if k["test_language"])
        print(f"  {co:<24} {len(rows):>3} awards, {len(keep):>2} validated, {tl} w/ test language")
        time.sleep(0.4)

    json.dump({"fetched": "2026-08-09", "companies": results}, open(OUT, "w"), indent=1)
    print(f"\n{len(results)} companies with validated federal awards -> data/awards.json")
    print(f"{len(rejects)} recipient-name rejects (validation, not silence):")
    for co, r in rejects[:8]:
        print(f"   {co} != {r}")


if __name__ == "__main__":
    main()
