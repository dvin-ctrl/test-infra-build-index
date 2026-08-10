#!/usr/bin/env python3
"""Phase 5 - render index.json into the standalone page."""
import json, os, html

HERE = os.path.dirname(__file__)
D = json.load(open(os.path.join(HERE, "data", "index.json")))
OUT = os.path.join(HERE, "index.html")

# The model was told to return test/data tools only, but it also volunteers domain
# nouns ("fluid systems", "mechanical hardware"). Display is filtered to a known
# tool vocabulary; the over-extraction is disclosed in the findings section.
KNOWN = {
    "LabVIEW", "TestStand", "DIAdem", "VeriStand", "MATLAB", "Simulink", "dSPACE",
    "PXI", "NI", "DAQ", "HIL", "SCADA", "PLC", "CAN bus", "Vector CANoe",
    "InfluxDB", "Grafana", "TimescaleDB", "Prometheus", "Datadog", "ROS/ROS2",
    "Beckhoff", "Beckhoff TwinCAT 3", "Siemens TIA Portal", "Terraform", "Python",
    "HITL", "MuJoCo", "SIL", "Ignition", "Kepware", "OPC UA",
}
from collections import Counter

e = html.escape

# Snapshot date, carried from scan time. A dated snapshot is honest about link rot:
# job postings close, so some links will 404 over time. That is expected, not a bug.
_iso = D.get("scanned", "")
try:
    import datetime as _dt
    _d = _dt.date.fromisoformat(_iso)
    SCANNED = f"{_d.day} {_d.strftime('%B %Y')}"
except Exception:
    SCANNED = _iso or "unknown"


MIN_MENTIONS = D.get("min_mentions", 2)
MIN_RATE = D.get("min_rate", 0.05)

_cl = json.load(open(os.path.join(HERE, "data", "classified.json")))
_ops = sum(1 for v in _cl.values() for t in v.get("tools", []) if t["usage"] == "operates")
_lst = sum(1 for v in _cl.values() for t in v.get("tools", []) if t["usage"] == "listed")
LISTED_PCT = round(_lst / max(_ops + _lst, 1) * 100)
TOOL_MENTIONS = _ops + _lst
_ml = Counter()
for v in _cl.values():
    for t in v.get("tools", []):
        if t["name"].strip().upper().startswith("MATLAB"):
            _ml[t["usage"]] += 1
MATLAB_OPS, MATLAB_LST = _ml["operates"], _ml["listed"]
TOP = D["rows"][0]
TIERS = Counter(r["tier"] for r in D["rows"])
NAIVE_CUT = 2427
LEGACY_PREV = Counter()
for _r in D["rows"]:
    for _t, _n, _u in _r["legacy"]:
        LEGACY_PREV[_t] += 1


def chips(triples, cls="chip"):
    """Render [tool, count, source_url] triples as LINKS. Every chip points at a
    posting whose raw text was verified at build time to contain the tool in a
    non-interchangeable sentence, so the question "where is this from" is always
    one click from its answer. Thin evidence (one distinct sentence) renders dim."""
    out = []
    for t, n, u in triples:
        weak = " weak" if n < MIN_MENTIONS else ""
        out.append(f'<a class="{cls}{weak}" href="{e(u)}" target="_blank" rel="noopener">'
                   f'{e(t)}<span class="ct">&times;{n}</span></a>')
    return "".join(out)


rows_html = []
for i, r in enumerate(D["rows"], 1):
    stack = [[t, n, u] for t, n, u in r["stack_top"] if t in KNOWN][:5]
    legacy = r["legacy"][:4]
    inc = (f'<span class="inc">incumbent: {e(r["incumbent_note"])}</span>'
           if r.get("incumbent_note") else "")
    tier_cls = {"A": "t-a", "B": "t-b", "C": "t-c"}[r["tier"]]
    rows_html.append(f"""<tr>
  <td class="n dim">{i}</td>
  <td class="co"><span class="name">{e(r['company'])}</span><span class="seg">{e(r['segment'])}</span>{inc}</td>
  <td><span class="tier {tier_cls}">{r['tier']}</span></td>
  <td class="n">{r['score']}</td>
  <td class="n strong">{r['builds']}</td>
  <td class="n dim">{r['operates']}</td>
  <td class="n dim">{int(r['build_ratio']*100)}%</td>
  <td class="stk">{chips(legacy, 'chip warn') or '<span class="dim">none named</span>'}</td>
  <td class="stk">{chips(stack)}</td>
</tr>
<tr class="ev">
  <td></td>
  <td colspan="8">
    <span class="scope">single highest-confidence req &middot; not the source of the stack chips above</span><br>
    <a href="{e(r['evidence_url'])}" target="_blank" rel="noopener">{e(r['evidence_title'])}</a>
    <q>{e(r['evidence'])}</q>
  </td>
</tr>""")

comp_html = "".join(
    f"""<li><strong>{e(c['company'])}</strong>
    <span class="why">{e(c['excluded_reason'])}</span></li>"""
    for c in sorted(D.get("competitors", []), key=lambda x: -x["score"]))

sup_html = "".join(
    f"""<li><strong>{e(s['company'])}</strong> <span class="mono dim">score {s['score']}, {s['builds']} build-posture reqs</span>
    <span class="why">{e(s['excluded_reason'])}</span></li>"""
    for s in sorted(D["suppressed"], key=lambda x: -x["score"]))

UNREACHED = ["Joby Aviation", "Beta Technologies", "Boston Dynamics", "Stoke Space",
             "Firefly Aerospace", "Castelion", "Sierra Space", "Wisk Aero", "Electra",
             "X-energy", "Zap Energy", "TAE Technologies", "Type One Energy", "Gatik",
             "Plus", "K2 Space", "Overland AI", "Blue Water Autonomy", "Forterra"]

PAGE = f"""<title>Test Infrastructure Build Index</title>
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
.wrap {{ max-width:78rem; margin:0 auto; padding:3.5rem 1.25rem 7rem;
  display:flex; flex-direction:column; gap:3.25rem; }}
a {{ color:var(--signal); }}
:focus-visible {{ outline:2px solid var(--signal); outline-offset:2px; }}

.eyebrow {{ font-family:var(--mono); font-size:.68rem; letter-spacing:.2em;
  text-transform:uppercase; color:var(--signal); margin:0 0 .75rem; }}
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

.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(9.5rem,1fr));
  gap:.7rem; }}
.tile {{ background:var(--panel); border:1px solid var(--line); padding:1rem 1.05rem; }}
.tile .k {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.15em;
  text-transform:uppercase; color:var(--dim); display:block; margin-bottom:.5rem; }}
.tile .v {{ font-size:1.8rem; font-weight:660; line-height:1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em; }}
.tile .s {{ font-size:.76rem; color:var(--soft); margin-top:.4rem; display:block; }}
.tile.acc .v {{ color:var(--signal); }}

.funnel {{ display:flex; flex-wrap:wrap; gap:.5rem; align-items:stretch; margin-top:.4rem; }}
.step {{ background:var(--panel); border:1px solid var(--line); padding:.7rem .95rem;
  flex:1 1 12rem; }}
.step .v {{ font-family:var(--mono); font-size:1.15rem; font-weight:600;
  font-variant-numeric:tabular-nums; }}
.step .k {{ font-size:.75rem; color:var(--soft); display:block; margin-top:.2rem; }}
.step .cut {{ font-family:var(--mono); font-size:.66rem; color:var(--hot);
  display:block; margin-top:.3rem; }}

.scroll {{ overflow-x:auto; border:1px solid var(--line); background:var(--panel); }}
table {{ width:100%; border-collapse:collapse; font-size:.87rem; min-width:60rem; }}
th {{ font-family:var(--mono); font-size:.6rem; letter-spacing:.11em; text-transform:uppercase;
  color:var(--dim); font-weight:400; text-align:right; padding:.8rem .65rem;
  border-bottom:1px solid var(--line2); white-space:nowrap; }}
th:nth-child(2), th:nth-child(8), th:nth-child(9) {{ text-align:left; }}
td {{ padding:.6rem .65rem; vertical-align:middle; }}
td.n {{ text-align:right; font-family:var(--mono); font-size:.82rem;
  font-variant-numeric:tabular-nums; }}
td.strong {{ font-weight:650; }}
td.dim {{ color:var(--dim); }}
.co .name {{ display:block; font-weight:620; }}
.co .seg {{ display:block; font-family:var(--mono); font-size:.65rem; color:var(--dim); }}
tr.ev td {{ padding:0 .65rem .85rem; border-bottom:1px solid var(--line); }}
tr.ev a {{ font-family:var(--mono); font-size:.68rem; text-decoration:none;
  border-bottom:1px solid var(--line2); }}
tr.ev q {{ display:block; color:var(--soft); font-size:.82rem; margin-top:.25rem;
  max-width:62rem; font-style:italic; }}
.tier {{ font-family:var(--mono); font-size:.68rem; font-weight:600; padding:.16rem .48rem;
  display:inline-block; }}
.t-a {{ background:var(--hot-bg); color:var(--hot); }}
.t-b {{ background:var(--warm-bg); color:var(--warm); }}
.t-c {{ background:var(--cool-bg); color:var(--cool); }}
.chip {{ font-family:var(--mono); font-size:.63rem; padding:.14rem .4rem;
  background:var(--signal-bg); color:var(--signal); margin:.1rem .18rem .1rem 0;
  display:inline-block; white-space:nowrap; text-decoration:none;
  border-bottom:1px solid transparent; }}
a.chip:hover {{ border-bottom-color:currentColor; }}
.chip.warn {{ background:var(--warm-bg); color:var(--warm); }}
.stk {{ min-width:11rem; }}
.dim {{ color:var(--dim); }}
.mono {{ font-family:var(--mono); }}

.callout {{ background:var(--panel); border-left:2px solid var(--signal);
  padding:1.05rem 1.25rem; }}
.callout .k {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.15em;
  text-transform:uppercase; color:var(--signal); display:block; margin-bottom:.5rem; }}
.callout p {{ margin:0; color:var(--ink); }}
.callout.warn {{ border-left-color:var(--hot); }}
.callout.warn .k {{ color:var(--hot); }}

ul.plain {{ list-style:none; padding:0; margin:.6rem 0 0; display:grid;
  grid-template-columns:repeat(auto-fit,minmax(19rem,1fr)); gap:.45rem; }}
ul.plain li {{ background:var(--panel); border:1px solid var(--line);
  padding:.65rem .85rem; font-size:.87rem; }}
ul.plain .why {{ display:block; font-family:var(--mono); font-size:.65rem;
  color:var(--signal); margin-top:.22rem; }}

.finding {{ border-top:1px solid var(--line); padding-top:1.1rem; margin-top:1.2rem; }}
.finding .was {{ font-family:var(--mono); font-size:.75rem; color:var(--hot); margin:0 0 .45rem; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:.8rem; margin-top:.9rem; }}
@media (max-width:46rem) {{ .two {{ grid-template-columns:1fr; }} }}
.two > div {{ background:var(--panel); border:1px solid var(--line); padding:.95rem 1.05rem; }}
.two h4 {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.13em;
  text-transform:uppercase; color:var(--dim); margin:0 0 .55rem; font-weight:400; }}
.two ul {{ margin:0; padding-left:1.05rem; font-size:.86rem; color:var(--soft); }}
.two li {{ margin-bottom:.28rem; }}
code {{ font-family:var(--mono); font-size:.85em; background:var(--panel);
  border:1px solid var(--line); padding:.06em .32em; }}
.tags {{ font-family:var(--mono); font-size:.72rem; color:var(--dim); line-height:2; }}
.chip .ct {{ opacity:.6; margin-left:.28em; font-size:.92em; }}
.chip.weak {{ opacity:.45; }}
.scope {{ font-family:var(--mono); font-size:.58rem; letter-spacing:.06em;
  text-transform:none; color:var(--dim); font-weight:400; }}
.co .inc {{ display:block; font-family:var(--mono); font-size:.6rem; color:var(--warm);
  margin-top:.18rem; }}
.specs {{ display:flex; flex-direction:column; gap:1.15rem; margin-top:.4rem; }}
.spec .lbl {{ font-family:var(--mono); font-size:.62rem; letter-spacing:.15em;
  text-transform:uppercase; color:var(--signal); display:block; margin-bottom:.45rem; }}
.srow {{ display:grid; grid-template-columns:minmax(0,1.05fr) minmax(0,1.15fr) auto;
  gap:.35rem 1.1rem; align-items:baseline; background:var(--panel);
  border:1px solid var(--line); padding:.62rem .85rem; margin-bottom:.35rem; }}
@media (max-width:58rem) {{ .srow {{ grid-template-columns:1fr; }} }}
.srow code {{ font-size:.7rem; overflow-wrap:anywhere; background:none; border:0;
  padding:0; color:var(--ink); }}
.srow .what {{ font-size:.82rem; color:var(--soft); }}
.srow .cost {{ font-family:var(--mono); font-size:.62rem; white-space:nowrap;
  padding:.15rem .45rem; justify-self:start; }}
.cost.free {{ background:var(--cool-bg); color:var(--cool); }}
.cost.paid {{ background:var(--warm-bg); color:var(--warm); }}
.notused {{ background:var(--panel); border:1px dashed var(--line2); padding:.7rem .9rem;
  font-size:.83rem; color:var(--soft); margin-top:.2rem; }}
</style>

<div class="wrap">

<header>
  <p class="eyebrow">Nominal / GTM engineering &middot; companion:
     <a href="https://claude.ai/code/artifact/319632e9-7592-44e4-b2e2-57e0d4b8ae69" style="color:inherit">Test Campaign Radar</a></p>
  <h1>Test Infrastructure Build Index</h1>
  <p class="lede">Which hardware teams are currently paying engineers to build the thing
     Nominal sells, ranked from public job board APIs alone, so a rep opens with a named
     req instead of a guess.</p>
  <p class="src">
     <strong style="color:var(--signal)">Snapshot scanned {SCANNED}.</strong>
     Postings close over time, so some links below will expire. That is a property of a
     dated scan, not a broken page. Re-running the scanner refreshes every number.<br>
     51 companies probed &middot; {D['boards_resolved']} boards resolved &middot;
     {D['total_postings']:,} live postings read &middot; {D['builds_total']} build-posture reqs<br>
     Ashby / Greenhouse / Lever public APIs, no auth, no paid enrichment &middot;
     $0.26 total compute &middot; reproducible with curl
  </p>
</header>

<section>
  <div class="tiles">
    <div class="tile"><span class="k">Postings read</span><span class="v">{D['total_postings']:,}</span>
      <span class="s">across {D['boards_resolved']} live boards</span></div>
    <div class="tile acc"><span class="k">Build-posture reqs</span><span class="v">{D['builds_total']}</span>
      <span class="s">hiring to build, not operate</span></div>
    <div class="tile"><span class="k">Accounts ranked</span><span class="v">{len(D['rows'])}</span>
      <span class="s">{TIERS['A']} tier A, {TIERS['B']} tier B, {TIERS['C']} tier C</span></div>
    <div class="tile"><span class="k">Excluded</span><span class="v">{len(D['suppressed']) + len(D['competitors'])}</span>
      <span class="s">{len(D['suppressed'])} customers, {len(D['competitors'])} competitor</span></div>
    <div class="tile"><span class="k">Cost to run</span><span class="v">$0.26</span>
      <span class="s">two gpt-4o-mini passes</span></div>
  </div>
</section>

<section>
  <h2>Tech stack</h2>
  <p>Every input is a public endpoint. There is no paid data vendor, no scraping
     service, no proxy, and no headless browser anywhere in this pipeline, which is why
     anyone at Nominal can reproduce the whole dataset from a laptop.</p>

  <div class="specs">
    <div class="spec">
      <span class="lbl">Ingest &middot; job boards</span>
      <div class="srow">
        <code>GET api.ashbyhq.com/posting-api/job-board/{{slug}}</code>
        <span class="what">Ashby public board. Full description text per posting.</span>
        <span class="cost free">free, no auth</span>
      </div>
      <div class="srow">
        <code>GET boards-api.greenhouse.io/v1/boards/{{slug}}/jobs?content=true</code>
        <span class="what">Greenhouse public board. <code>content=true</code> is what returns
          the description body rather than titles alone.</span>
        <span class="cost free">free, no auth</span>
      </div>
      <div class="srow">
        <code>GET api.lever.co/v0/postings/{{slug}}?mode=json</code>
        <span class="what">Lever public board. Text is split across
          <code>descriptionPlain</code>, <code>lists[]</code> and <code>additionalPlain</code>;
          all three are concatenated. Reading only the first captures 32%.</span>
        <span class="cost free">free, no auth</span>
      </div>
      <div class="srow">
        <code>GET &lt;company&gt;/careers</code>
        <span class="what">Plain HTTP fetch, regexed for a board token when slug guessing
          fails. Recovered 5 boards including Applied Intuition and Commonwealth Fusion.</span>
        <span class="cost free">free</span>
      </div>
    </div>

    <div class="spec">
      <span class="lbl">Synthesis</span>
      <div class="srow">
        <code>POST api.openai.com/v1/chat/completions</code>
        <span class="what">gpt-4o-mini at temperature 0, structured output via
          <code>json_schema</code> with <code>strict:true</code>. Returns build-versus-operate
          posture, named stack, and a verbatim evidence quote. {D['keyword_matched']:,} calls.</span>
        <span class="cost paid">$0.26</span>
      </div>
      <div class="srow">
        <code>python3 &middot; requests &middot; ThreadPoolExecutor</code>
        <span class="what">Orchestration at 8 to 10 concurrent workers. Every stage caches to
          disk and resumes, so an interrupted run never re-bills.</span>
        <span class="cost free">free</span>
      </div>
      <div class="srow">
        <code>re &middot; word-boundary matching</code>
        <span class="what">Pre-filter cutting {D['total_postings']:,} postings to {D['keyword_matched']:,} before any model call.
          Acronyms case-sensitive, phrases case-insensitive. This is what keeps
          classification under a dime.</span>
        <span class="cost free">free</span>
      </div>
      <div class="srow">
        <code>deterministic scoring (score.py)</code>
        <span class="what">The 0 to 8 account score, computed in Python from four inputs.
          No model involvement in the ranking.</span>
        <span class="cost free">free</span>
      </div>
    </div>

    <div class="spec">
      <span class="lbl">Orchestration</span>
      <div class="srow">
        <code>Claude Code (Anthropic)</code>
        <span class="what">Agentic build environment. Authored, ran, and audited every stage
          of this pipeline in one loop: probing the APIs, measuring false-positive rates,
          and re-verifying each finding against raw source data before it shipped. The six
          findings below were caught, fixed, and documented in the same environment.</span>
        <span class="cost free">dev environment</span>
      </div>
      <div class="srow">
        <code>git &middot; GitHub</code>
        <span class="what">Every methodology change is a commit with its reasoning in the
          message, so the scoring's history is auditable, not just its current state.</span>
        <span class="cost free">free</span>
      </div>
    </div>
  </div>

  <p class="notused"><strong>Deliberately not used:</strong> no LinkedIn, no paid enrichment
     or contact vendor, no scraping service or proxy pool, no headless browser, no CRM
     export. If a number on this page cannot be traced to a public endpoint, it is not on
     this page.</p>
</section>

<section>
  <h2>The signal nobody sells</h2>
  <p>Nominal's own positioning names the buying trigger: teams should focus
     <em>"on what to test, not how to build automated test infrastructure,"</em> and the
     Nominal Connect launch describes hardware teams running
     <em>"brittle scripts duct-taped to aging GUIs."</em> Contrary Research names the same
     thing as Nominal's top business risk, that well-resourced companies build their own
     stack instead.</p>
  <p>That risk is also the sharpest targeting signal available, and no data vendor sells it.
     Technographic tools read what a company exposes on its website; a HIL rig sits in a
     high bay. But a company staffing test infrastructure writes the whole stack into its
     job descriptions, every week, in public.</p>
  <div class="funnel">
    <div class="step"><span class="v">{D['total_postings']:,}</span><span class="k">postings pulled</span></div>
    <div class="step"><span class="v">{D['keyword_matched']:,}</span><span class="k">keyword match</span>
      <span class="cut">&minus;{NAIVE_CUT:,} naive false positives</span></div>
    <div class="step"><span class="v">{D['builds_total'] + D['operates_total']}</span><span class="k">genuinely test-related</span>
      <span class="cut">&minus;{D['llm_discarded']} discarded by classifier</span></div>
    <div class="step"><span class="v">{D['builds_total']}</span><span class="k">build posture</span>
      <span class="cut">&minus;{D['operates_total']} operate existing tooling</span></div>
  </div>
</section>

<section>
  <h2>Ranked accounts</h2>
  <p>Score is 0 to 8 and is computed in Python from four inputs: build-req volume, named
     legacy tooling, a self-hosted telemetry stack, and the ratio of build reqs to operate
     reqs. The score is 0 to 5, computed in Python from exactly two inputs: build-req
     volume (0 to 3) and the ratio of build reqs to operate reqs (0 to 2). Detected tooling
     is <strong>never a scoring input</strong>. Findings 5 and 6 showed tool mentions are
     mostly vocabulary, not commitments, so tooling is shown for conversation context only:
     counts are distinct non-interchangeable sentences, and every chip is a link to a
     posting verified at build time to contain it. The model extracts posture and stack per posting; it
     never sets the score, so a prompt change can move one verdict but cannot silently
     reshuffle the ranking.</p>
  <p><strong style="color:var(--ink)">Two different scopes in one row.</strong> The stack
     columns aggregate across every posting at that account. The quote beneath each row is
     one specific req. They are not the same source and are labelled accordingly.</p>
  <div class="scroll">
    <table>
      <thead><tr>
        <th>#</th><th>Account</th><th>Tier</th><th>Score</th><th>Build</th>
        <th>Ops</th><th>Build&nbsp;%</th>
        <th>Legacy stack<br><span class="scope">operated &middot; chip links to source req</span></th>
        <th>Also operated<br><span class="scope">chip links to source req</span></th>
      </tr></thead>
      <tbody>
{"".join(rows_html)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>What a rep opens with</h2>
  <div class="callout">
    <span class="k">Generated brief &middot; largest build commitment</span>
    <p>{e(TOP['company'])} has {TOP['builds']} open reqs classified as building test
       infrastructure against {TOP['operates']} that operate it, the largest build commitment
       in the index. Its highest-confidence req,
       <a href="{e(TOP['evidence_url'])}" target="_blank" rel="noopener">{e(TOP['evidence_title'])}</a>,
       reads: <em>"{e(TOP['evidence'])}"</em>. A company funding that many people to build
       test infrastructure is paying salaries for what Nominal sells, and every req behind
       this row is one click away.</p>
  </div>
  <p style="margin-top:1rem">After the deterministic filter, defensible operated legacy
     tooling is rare: LabVIEW at {LEGACY_PREV['LabVIEW']} accounts, MATLAB at
     {LEGACY_PREV['MATLAB']}, MATLAB/Simulink at {LEGACY_PREV['MATLAB/Simulink']}. That
     scarcity is the finding, not a weakness of the page: job descriptions state what a
     company will pay someone to do far more reliably than they state what software it runs.
     The displacement conversation starts from the build commitment, and the chip links
     provide the tooling context where it genuinely exists.</p>
</section>

<section>
  <h2>Suppression, which is the part that has to work</h2>
  <p>Publicly named Nominal customers are removed before ranking. This matters more than it
     looks: the highest-scoring account in the entire dataset was one of them.</p>
  <p style="margin-top:.4rem"><strong style="color:var(--ink)">Excluded as customers</strong></p>
  <ul class="plain">{sup_html}</ul>
  <p style="margin-top:1rem"><strong style="color:var(--ink)">Excluded as competitors.</strong>
     Ranking a competitor as a warm prospect is the same class of error as ranking a
     customer, and it is the one I missed on the first pass. Applied Intuition would
     have scored {D['competitors'][0]['score']} on {D['competitors'][0]['builds']} build-posture
     reqs, placing it in tier A.</p>
  <ul class="plain">{comp_html}</ul>
  <div class="callout warn" style="margin-top:.9rem">
    <span class="k">Why this check exists</span>
    <p>Varda Space scored 8 out of 8, higher than any account that survived. A naive scan
       would have handed a rep a confident, well-evidenced cold brief for a company Nominal
       already bills. Getting that wrong once is how an internal GTM system loses the
       sales team's trust permanently.</p>
  </div>
</section>

<section>
  <h2>Six ways this data tried to mislead me</h2>
  <p>Each produced confident, wrong output before it was caught. This section matters
     more than the ranking. Findings 4 through 6 were all found the same way: a reader
     asked where one specific number came from, and the answer did not hold. That is also
     why the page now guarantees the question structurally instead of answering it case by
     case.</p>

  <div class="finding">
    <h3>1. Naive matching called 98% of the market a lead</h3>
    <p class="was">Substring matching flagged 3,427 of 3,497 postings as test-infrastructure signals.</p>
    <p class="tight">Ninety-eight percent is not a signal, it is a broken filter, and the
       absurdity is the only reason it got caught. The cause was acronyms:
       <code>HIL</code> matches inside "while" and "child", so a Workplace Assistant req
       scored as a hardware-in-the-loop lead. Case-sensitive word boundaries for acronyms and
       word-boundary matching for phrases cut it to 1,029, removing 2,398 false positives,
       70% of all naive hits. The classifier then discarded a further {D['llm_discarded']}
       where the tool names were incidental.</p>
  </div>

  <div class="finding">
    <h3>2. One job board silently returned a third of each posting</h3>
    <p class="was">Commonwealth Fusion came back with 0 signals across 58 postings.</p>
    <p class="tight">Zero is implausible for a fusion company building tokamaks, which is
       what made it worth checking. Lever's <code>mode=json</code> endpoint returns only the
       intro blurb in <code>descriptionPlain</code>; the requirements live in a separate
       <code>lists[]</code> array. I was reading 1,833 of 5,778 characters per posting and
       missing precisely the section where tool names appear. After concatenating the
       sections, Commonwealth Fusion went to 11 signal postings, Zoox from 15 to 61, and
       Venus Aerospace from 6 to 13. This is the more dangerous of the two failures: a false
       positive wastes a rep's time, but a false negative deletes an account from the
       pipeline and nobody ever learns it existed.</p>
  </div>

  <div class="finding">
    <h3>3. The model over-answered a list field</h3>
    <p class="was">"fluid systems", "mechanical hardware" and "accelerometers" were returned as test tools.</p>
    <p class="tight">Asked to extract named tools, the model volunteers domain nouns to fill
       the array. Separately it returns whatever casing the posting used, so LabVIEW,
       LabView and Labview counted as three different tools and split one account's stack
       across three rows. Display is filtered to a known tool vocabulary and names are
       canonicalised before counting. Both are quiet failures: neither throws, and both
       produce a plausible-looking column.</p>
  </div>

  <div class="finding">
    <h3>4. A correct number sitting next to an unrelated link</h3>
    <p class="was">Relativity Space showed "LabVIEW, MATLAB, Simulink" directly above a link to a req naming none of them.</p>
    <p class="tight">This one was not a data bug. Every number was right. The layout was
       wrong. The stack column aggregates across all of an account's postings, while the
       evidence link points at one specific req, and putting them on adjacent rows with no
       label implied they shared a source. For Relativity at the time, MATLAB came from 16
       postings, LabVIEW from 2 and Simulink from 1, out of 63 test-related reqs, while the
       linked req named no tools at all.
       Anyone who clicked through and searched for LabVIEW would find nothing and would be
       right to distrust every other figure on the page. Both scopes are now labelled, and
       chips carry their mention count so a tool named once cannot pass for one named
       sixteen times. Scoring now requires a tool to appear in at least
       {MIN_MENTIONS} postings, or in {int(MIN_RATE*100)}% of that account's test reqs,
       which reordered the top of the table.</p>
  </div>
  <div class="finding">
    <h3>5. Two thirds of the tool mentions were resume filler</h3>
    <p class="was">MATLAB appeared to be the dominant legacy stack in the index. {MATLAB_LST} of its {MATLAB_OPS + MATLAB_LST} mentions were skills-list boilerplate.</p>
    <p class="tight">Two compounding errors. First, recruiters paste the same requirements
       line across a whole job family, so counting postings counted the template: at
       Relativity, 16 reqs naming MATLAB collapsed to 9 distinct sentences, at Rocket Lab
       28 collapsed to 15. Since scoring had just been made to depend on prevalence, that
       rewarded copy-paste. Counting now dedupes on the sentence, not the posting.
       Second and worse, the classifier extracted named tools without asking whether the
       company <em>runs</em> the tool. "Familiarity with scripting languages such as Python
       or MATLAB" is a recruiter listing two acceptable languages, not a MATLAB test stack.
       Re-classified with an explicit operates-versus-listed judgement, {LISTED_PCT}% of all
       {TOOL_MENTIONS} tool mentions turned out to be listed-only. Scoring now counts only
       tools a company operates, which dropped Relativity from first place to fifth with no
       operated legacy tooling at all, and moved Hadrian to the top. The tier bands were
       recalibrated at the same time, because the tightened definition left exactly one
       tier A account across 28, which is not a usable prioritisation.</p>
  </div>
  <div class="finding">
    <h3>6. The fix for finding 5 had the same disease</h3>
    <p class="was">The model labelled "LabVIEW, Python, or similar test automation tools" as a stack the company operates.</p>
    <p class="tight">After finding 5, tools only counted when the model judged the company
       <em>operates</em> them. Auditing that judgement showed 12% of operates calls sat in
       sentences whose own grammar marks the tool as interchangeable: "or similar", "or
       equivalent", "such as". Two near-identical True Anomaly sentences received opposite
       labels, and the number one account's entire operated-legacy evidence was a single
       "or equivalent" sentence. Two structural changes followed. The interchangeability
       test is now enforced in Python on the source sentence, not delegated to the model.
       And tooling was removed from the score entirely, because a distinction the source
       text only makes 88% reliably cannot order an account list. The ranking now rests
       only on build commitments, which is the one thing job postings state plainly. Every
       remaining tool chip is a link to a posting verified at build time to contain that
       tool in a non-interchangeable sentence: the question that caught findings 4 and 6
       is now answerable by clicking the number itself.</p>
  </div>
</section>

<section>
  <h2>Coverage I do not have</h2>
  <p>Nineteen of the 51 companies I targeted run Workday or custom boards with no public
     API, so they are absent rather than scored zero. Naming the gap is cheaper than
     letting someone assume the index is exhaustive.</p>
  <p class="tags">{" &middot; ".join(UNREACHED)}</p>
</section>

<section>
  <h2>Where this goes on the inside</h2>
  <p>This is the outside-in version, built on public data because that is what an outsider
     can reach. The same pipeline pointed at Nominal's own systems gets materially better
     inputs, and becomes an account-scoring property that lives on the record rather than a
     page someone reads once.</p>
  <div class="two">
    <div>
      <h4>Outside-in (this)</h4>
      <ul>
        <li>Public job boards, 32 of 51 companies</li>
        <li>Inferred build-versus-buy posture</li>
        <li>Legacy stack named in reqs</li>
        <li>No timing signal</li>
      </ul>
    </div>
    <div>
      <h4>Inside-out (with Salesforce and Gong)</h4>
      <ul>
        <li>Stack detections written as contact and account properties, refreshed on a schedule</li>
        <li>Legacy tool named on a Gong call, matched against the req that predicted it</li>
        <li>Won and lost deals scored retroactively to calibrate the weights</li>
        <li>Federal award data as the timing trigger, now live on the
            <a href="https://claude.ai/code/artifact/319632e9-7592-44e4-b2e2-57e0d4b8ae69">Test Campaign Radar</a></li>
      </ul>
    </div>
  </div>
  <div class="callout" style="margin-top:.9rem">
    <span class="k">The check I would want first</span>
    <p>Run this scorer backwards over closed-won accounts. If build-posture density does not
       separate won from lost, the weights are wrong and should be thrown away rather than
       shipped. That test costs an afternoon and is the difference between an account score
       reps trust and one they quietly ignore.</p>
  </div>
</section>

<footer style="border-top:1px solid var(--line);padding-top:1.2rem">
  <p class="src" style="margin:0">Built by Dvin Malekian &middot; scanned {SCANNED} &middot;
     scanner source and method published alongside this page &middot; every number here is
     reproducible from public endpoints</p>
</footer>

</div>
"""

open(OUT, "w").write(PAGE)
print(f"wrote {OUT} ({len(PAGE):,} bytes, {len(D['rows'])} ranked, {len(D['suppressed'])} suppressed)")
