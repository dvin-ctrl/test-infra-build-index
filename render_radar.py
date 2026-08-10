#!/usr/bin/env python3
"""
Stage 6 - render the companion page: Test Campaign Radar.

The join page. One layer is a list, two layers is an argument: a validated
federal award proves a funded program; concurrent build-posture reqs prove the
company is staffing to build its own test infrastructure for it. Rows carry
both halves, each linked to its filed source, and the per-account brief is
assembled mechanically from those fields so every clause is traceable.

No LLM runs in this layer. Awards are filed facts; posture comes from the
already-classified job data. Cost of this page: $0.
"""
import json, os, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AW = json.load(open(os.path.join(DATA, "awards.json")))
IDX = json.load(open(os.path.join(DATA, "index.json")))
OUT = os.path.join(HERE, "radar.html")

e = html.escape
rows_by_co = {r["company"]: r for r in IDX["rows"]}


def money(x):
    if x is None:
        return "n/a"
    if x >= 1e6:
        return f"${x/1e6:,.1f}M"
    return f"${x:,.0f}"


def nice_date(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        return f"{d.day} {d.strftime('%b %Y')}"
    except Exception:
        return iso or "n/a"


# ---- buckets -----------------------------------------------------------------
joined, funded_only = [], []
for co, awards in AW["companies"].items():
    r = rows_by_co.get(co)
    total = sum(a["amount"] or 0 for a in awards)
    entry = {"company": co, "awards": awards, "total": total,
             "segment": (r or {}).get("segment", "?")}
    if r and r["builds"] >= 3:
        entry.update(builds=r["builds"], operates=r["operates"],
                     ratio=r["build_ratio"], req_title=r["evidence_title"],
                     req_url=r["evidence_url"], req_quote=r["evidence"])
        joined.append(entry)
    else:
        funded_only.append(entry)

joined.sort(key=lambda x: (-x["builds"], -x["total"]))
funded_only.sort(key=lambda x: -x["total"])
build_only = [r for r in IDX["rows"]
              if r["builds"] >= 3 and r["company"] not in AW["companies"]]
build_only.sort(key=lambda x: -x["builds"])

# featured brief: highest build ratio among joined accounts with a real bench
featured = max((j for j in joined if j["builds"] >= 8), key=lambda x: x["ratio"])


def brief(j):
    t = j["awards"][0]
    agency = t["sub_agency"] or t["agency"] or "a federal agency"
    return (f'{j["company"]} was awarded {money(t["amount"])} by {agency} '
            f'(start {nice_date(t["start"])}): "{t["quote"][:140]}". They are staffing it '
            f'now: {j["builds"]} open reqs building test infrastructure against '
            f'{j["operates"]} operating it, including {j["req_title"]}.')


cards = []
for i, j in enumerate(joined, 1):
    t = j["awards"][0]
    more = ""
    if len(j["awards"]) > 1:
        more = (f'<span class="more">+{len(j["awards"]) - 1} more validated awards, '
                f'{money(j["total"])} total</span>')
    cards.append(f"""<article class="card">
  <div class="cardhead">
    <span class="rank">{i}</span>
    <div><span class="name">{e(j['company'])}</span>
    <span class="seg">{e(j['segment'])}</span></div>
    <span class="ratio" title="build reqs / all test reqs">{j['builds']} build / {j['operates']} operate &middot; {int(j['ratio']*100)}%</span>
  </div>
  <div class="halves">
    <div class="half">
      <span class="lbl">Funded &middot; USAspending record</span>
      <p class="amt">{money(t['amount'])} <span class="agency">{e(t['sub_agency'] or t['agency'] or '')}</span>
         <span class="date">start {e(nice_date(t['start']))}</span></p>
      <q>{e(t['quote'][:180])}</q>
      <a href="{e(t['url'])}" target="_blank" rel="noopener">award record</a>
      {more}
    </div>
    <div class="half">
      <span class="lbl">Staffing &middot; live req</span>
      <p class="amt">{e(j['req_title'])}</p>
      <q>{e((j['req_quote'] or '')[:180])}</q>
      <a href="{e(j['req_url'])}" target="_blank" rel="noopener">job posting</a>
    </div>
  </div>
  <p class="brief"><span class="lbl">Assembled brief</span>{e(brief(j))}</p>
</article>""")

funded_html = "".join(
    f'''<li><strong>{e(x["company"])}</strong>
    <span class="mono dim">{len(x["awards"])} awards &middot; {money(x["total"])}</span>
    <span class="why">funded, but no current test-infra build hiring detected</span></li>'''
    for x in funded_only)

buildonly_html = "".join(
    f'''<li><strong>{e(r["company"])}</strong>
    <span class="mono dim">{r["builds"]} build reqs</span>
    <span class="why">no validated federal award found (commercial or VC funded)</span></li>'''
    for r in build_only)

ft = featured["awards"][0]

PAGE = f"""<title>Test Campaign Radar</title>
<style>
:root {{
  --bg:#F4F6F6; --panel:#FFFFFF; --ink:#10171A; --soft:#47555A; --dim:#7A8A8E;
  --line:#DFE5E5; --line2:#C7D2D2;
  --signal:#0F6E80; --signal-bg:#E2EFF1;
  --hot:#A6382C; --hot-bg:#F6E7E4;
  --warm:#8A6212; --warm-bg:#F7EFDB;
  --cool:#2C6B52; --cool-bg:#E3F0E9;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}}
@media (prefers-color-scheme:dark) {{
  :root {{
    --bg:#0C1214; --panel:#141C1F; --ink:#E4EBEC; --soft:#9DAEB2; --dim:#6E7E82;
    --line:#1E282B; --line2:#2C393D;
    --signal:#4FBDD4; --signal-bg:#102C33;
    --hot:#E08A7E; --hot-bg:#2B1815;
    --warm:#D6A852; --warm-bg:#2A2114;
    --cool:#69BE99; --cool-bg:#14271E;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#0C1214; --panel:#141C1F; --ink:#E4EBEC; --soft:#9DAEB2; --dim:#6E7E82;
  --line:#1E282B; --line2:#2C393D;
  --signal:#4FBDD4; --signal-bg:#102C33;
  --hot:#E08A7E; --hot-bg:#2B1815;
  --warm:#D6A852; --warm-bg:#2A2114;
  --cool:#69BE99; --cool-bg:#14271E;
}}
:root[data-theme="light"] {{
  --bg:#F4F6F6; --panel:#FFFFFF; --ink:#10171A; --soft:#47555A; --dim:#7A8A8E;
  --line:#DFE5E5; --line2:#C7D2D2;
  --signal:#0F6E80; --signal-bg:#E2EFF1;
  --hot:#A6382C; --hot-bg:#F6E7E4;
  --warm:#8A6212; --warm-bg:#F7EFDB;
  --cool:#2C6B52; --cool-bg:#E3F0E9;
}}
*, *::before, *::after {{ box-sizing:border-box; }}
body {{ background:var(--bg); color:var(--ink); font-family:var(--sans);
  font-size:16px; line-height:1.62; -webkit-font-smoothing:antialiased; margin:0; }}
.wrap {{ max-width:72rem; margin:0 auto; padding:3.5rem 1.25rem 7rem;
  display:flex; flex-direction:column; gap:3rem; }}
a {{ color:var(--signal); }}
:focus-visible {{ outline:2px solid var(--signal); outline-offset:2px; }}
.eyebrow {{ font-family:var(--mono); font-size:.68rem; letter-spacing:.2em;
  text-transform:uppercase; color:var(--signal); margin:0 0 .75rem; }}
.eyebrow a {{ color:inherit; }}
h1 {{ font-size:clamp(2.1rem,5.2vw,3.1rem); font-weight:650; letter-spacing:-.025em;
  line-height:1.06; margin:0 0 .85rem; text-wrap:balance; }}
.lede {{ font-size:1.08rem; color:var(--soft); max-width:46rem; margin:0; }}
.src {{ font-family:var(--mono); font-size:.72rem; color:var(--dim); margin-top:1.1rem;
  line-height:1.9; }}
h2 {{ font-size:1.4rem; font-weight:640; letter-spacing:-.012em; margin:0 0 .6rem; }}
h3 {{ font-size:.98rem; font-weight:640; margin:0 0 .35rem; }}
p {{ margin:0 0 .85rem; max-width:50rem; color:var(--soft); }}
p.tight {{ margin-bottom:0; }}
section {{ display:flex; flex-direction:column; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr)); gap:.7rem; }}
.tile {{ background:var(--panel); border:1px solid var(--line); padding:1rem 1.05rem; }}
.tile .k {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.15em;
  text-transform:uppercase; color:var(--dim); display:block; margin-bottom:.5rem; }}
.tile .v {{ font-size:1.8rem; font-weight:660; line-height:1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
.tile .s {{ font-size:.76rem; color:var(--soft); margin-top:.4rem; display:block; }}
.tile.acc .v {{ color:var(--signal); }}
.mono {{ font-family:var(--mono); }}
.dim {{ color:var(--dim); }}

.card {{ background:var(--panel); border:1px solid var(--line); padding:1.1rem 1.2rem;
  margin-bottom:.9rem; }}
.cardhead {{ display:flex; align-items:baseline; gap:.9rem; flex-wrap:wrap;
  border-bottom:1px solid var(--line); padding-bottom:.6rem; margin-bottom:.85rem; }}
.rank {{ font-family:var(--mono); font-size:.8rem; color:var(--dim);
  font-variant-numeric:tabular-nums; }}
.name {{ font-weight:650; font-size:1.05rem; }}
.seg {{ display:block; font-family:var(--mono); font-size:.65rem; color:var(--dim); }}
.ratio {{ margin-left:auto; font-family:var(--mono); font-size:.72rem; color:var(--signal);
  background:var(--signal-bg); padding:.2rem .55rem; white-space:nowrap; }}
.halves {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; }}
@media (max-width:46rem) {{ .halves {{ grid-template-columns:1fr; }} }}
.half {{ min-width:0; }}
.lbl {{ font-family:var(--mono); font-size:.6rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--dim); display:block; margin-bottom:.35rem; }}
.amt {{ font-weight:640; margin:0 0 .3rem; color:var(--ink); }}
.amt .agency {{ font-weight:400; font-size:.82rem; color:var(--soft); }}
.amt .date {{ font-family:var(--mono); font-size:.68rem; color:var(--dim); margin-left:.4rem; }}
.half q {{ display:block; font-size:.82rem; color:var(--soft); font-style:italic;
  margin:0 0 .4rem; }}
.half a {{ font-family:var(--mono); font-size:.7rem; }}
.more {{ display:block; font-family:var(--mono); font-size:.66rem; color:var(--dim);
  margin-top:.3rem; }}
.brief {{ border-top:1px dashed var(--line2); margin:.85rem 0 0; padding-top:.7rem;
  font-size:.88rem; color:var(--ink); max-width:none; }}
.brief .lbl {{ display:block; margin-bottom:.3rem; color:var(--signal); }}

.callout {{ background:var(--panel); border-left:2px solid var(--signal);
  padding:1.05rem 1.25rem; }}
.callout .k {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.15em;
  text-transform:uppercase; color:var(--signal); display:block; margin-bottom:.5rem; }}
.callout p {{ margin:0; color:var(--ink); }}
.callout.warn {{ border-left-color:var(--hot); }}
.callout.warn .k {{ color:var(--hot); }}
ul.plain {{ list-style:none; padding:0; margin:.6rem 0 0; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(17rem,1fr)); gap:.45rem; }}
ul.plain li {{ background:var(--panel); border:1px solid var(--line);
  padding:.65rem .85rem; font-size:.87rem; }}
ul.plain .why {{ display:block; font-family:var(--mono); font-size:.65rem;
  color:var(--signal); margin-top:.22rem; }}
.finding {{ border-top:1px solid var(--line); padding-top:1.1rem; margin-top:1.2rem; }}
.finding .was {{ font-family:var(--mono); font-size:.75rem; color:var(--hot); margin:0 0 .45rem; }}
code {{ font-family:var(--mono); font-size:.85em; background:var(--panel);
  border:1px solid var(--line); padding:.06em .32em; }}
</style>

<div class="wrap">

<header>
  <p class="eyebrow">Nominal / GTM engineering &middot; companion to the
     <a href="https://claude.ai/code/artifact/544a771c-0b4d-4140-a751-428eadcd02cc">Test Infrastructure Build Index</a></p>
  <h1>Test Campaign Radar</h1>
  <p class="lede">Companies holding a validated federal award and simultaneously hiring
     engineers to build their own test infrastructure for it. One layer is a list; two
     layers is an argument a rep can open with.</p>
  <p class="src">
     Awards fetched 9 August 2026 (USAspending API, contracts since 2024) &middot;
     hiring posture scanned 8 August 2026 &middot; recipient names validated, 122 wrong-company
     hits rejected &middot; no paid data, no LLM in this layer, $0 to run
  </p>
</header>

<section>
  <div class="tiles">
    <div class="tile"><span class="k">Companies queried</span><span class="v">47</span>
      <span class="s">suppressions already applied</span></div>
    <div class="tile"><span class="k">Validated awards</span><span class="v">{sum(len(v) for v in AW['companies'].values())}</span>
      <span class="s">across {len(AW['companies'])} recipients</span></div>
    <div class="tile acc"><span class="k">Joined accounts</span><span class="v">{len(joined)}</span>
      <span class="s">funded and staffing to build</span></div>
    <div class="tile"><span class="k">Wrong recipients rejected</span><span class="v">122</span>
      <span class="s">name validation, logged not silent</span></div>
    <div class="tile"><span class="k">Cost of this layer</span><span class="v">$0</span>
      <span class="s">public endpoints only</span></div>
  </div>
</section>

<section>
  <h2>Why the join</h2>
  <p>A federal award proves a funded program with dates and dollars, but startup award
     descriptions are mission names, not activity language: only 2 of {sum(len(v) for v in AW['companies'].values())}
     descriptions in this set even contain the word "test". A build-posture req proves a
     company is paying salaries for test infrastructure, but says nothing about timing or
     budget. Either alone is a list. Together they say: this company is funded to deliver a
     hardware program right now, and is hiring people to build the data layer under it
     instead of buying one. That sentence is the outreach, and every clause of it links to
     a filed source.</p>
</section>

<section>
  <h2>Joined accounts</h2>
  <p>Ordered by build-req count. Each card carries both halves of the argument with its
     source one click away, and the assembled brief at the bottom is generated mechanically
     from those fields, so it cannot say anything the sources do not.</p>
  {"".join(cards)}
</section>

<section>
  <h2>The row dollars would have missed</h2>
  <div class="callout">
    <span class="k">Reading awards as program access, not revenue</span>
    <p>Saronic's only validated award is a $500 initial order on the Missile Defense
       Agency's SHIELD program, dated 29 December 2025. As revenue that is nothing. As a
       signal it is the opposite: an initial order on an IDIQ means they are now eligible
       for task orders on a missile-defense program, while concurrently hiring a Senior
       Systems Test Software Engineer for their hardware-in-the-loop capabilities. A
       dollar-floor filter would have dropped the row entirely.</p>
  </div>
</section>

<section>
  <h2>What the pilot caught before a reader had to</h2>
  <p>The companion page documents six findings caught after publication, three of them by
     readers. This layer ran the five-account pilot first, and the pilot caught three more
     before anything shipped.</p>
  <div class="finding">
    <h3>1. The test-language gate had zero recall on the actual population</h3>
    <p class="was">Gating awards on phrases like "flight test" returned 0 companies across all 47 targets.</p>
    <p class="tight">The phrase list had been validated against Northrop and Lockheed
       awards, which carry DT&amp;E language. Venture-backed startups' award descriptions
       are mission names and SBIR titles. Validating a filter on the wrong population is
       the same mistake as finding 2 on the companion page, caught by the pilot this time.
       Test language is now a bonus flag, never a gate.</p>
  </div>
  <div class="finding">
    <h3>2. The regex could not match plurals</h3>
    <p class="was">"flight test" with a trailing word boundary fails on "FLIGHT TESTS", the exact string that validated the approach.</p>
    <p class="tight">Immaterial here once the gate was removed, but it means the original
       probe result would not have passed the original filter. Fixed with optional
       s/ing suffixes.</p>
  </div>
  <div class="finding">
    <h3>3. Keyword recipient search returns whoever loosely matches</h3>
    <p class="was">"Apex" returned GOLDBELT APEX, LLC and CAPEX CONSTRUCTION LLC as recipients.</p>
    <p class="tight">Every hit is validated by token overlap against the target's name,
       and generic one-word names additionally require a qualifier token. 122 wrong-company
       awards were rejected and logged. Unvalidated, those awards would have credited
       federal funding to the wrong companies and generated confident briefs about
       programs they do not hold.</p>
  </div>
</section>

<section>
  <h2>The other two buckets</h2>
  <p><strong style="color:var(--ink)">Funded, but not staffing to build.</strong> Validated
     awards with no concurrent test-infra build hiring. Watch list: if build reqs appear,
     they move up.</p>
  <ul class="plain">{funded_html}</ul>
  <p style="margin-top:1.2rem"><strong style="color:var(--ink)">Building, but no federal
     footprint.</strong> Commercial and VC-funded accounts ranked on the
     <a href="https://claude.ai/code/artifact/544a771c-0b4d-4140-a751-428eadcd02cc">companion page</a>;
     this layer cannot see them by design.</p>
  <ul class="plain">{buildonly_html}</ul>
</section>

<section>
  <h2>Method</h2>
  <p>One endpoint: <code>POST api.usaspending.gov/api/v2/search/spending_by_award</code>,
     free and unauthenticated, queried per target with recipient-name validation on every
     hit. Joined in Python against the build-posture data from the companion page's
     pipeline. No model runs in this layer: award facts are filed, posture was already
     classified, and the brief is string assembly. Quotes are substrings of the federal
     record, so verification is a text search on the linked page.</p>
</section>

<footer style="border-top:1px solid var(--line);padding-top:1.2rem">
  <p class="src" style="margin:0">Built by Dvin Malekian &middot; awards fetched 9 August 2026 &middot;
     scanner and join source published in the same repository as the companion page</p>
</footer>

</div>
"""

open(OUT, "w").write(PAGE)
print(f"wrote {OUT} ({len(PAGE):,} bytes, {len(joined)} joined, "
      f"{len(funded_only)} funded-only, {len(build_only)} build-only)")
print(f"featured (for reference): {featured['company']} at {int(featured['ratio']*100)}% build ratio")
