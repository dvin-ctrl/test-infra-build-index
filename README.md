# Test Infrastructure Build Index

Ranks hardware companies by how much they are currently paying engineers to **build**
test infrastructure in-house, rather than to **operate** tests with tooling they already
have. Computed entirely from public job board APIs.

**[View the rendered index →](https://claude.ai/code/artifact/544a771c-0b4d-4140-a751-428eadcd02cc)**

```
51 companies probed  →  32 boards resolved  →  3,497 live postings
     →  1,029 keyword matches  →  316 build-posture reqs  →  29 accounts ranked
Total cost: $0.11.  No paid data. No authentication. Reproducible with curl.
```

## Why this signal

Companies that sell test and operations software have a targeting problem: their best
prospect is a team already investing in test infrastructure, and that investment is
invisible. Technographic tools read what a company exposes on its website, and a
hardware-in-the-loop rig sits in a high bay behind a badge reader. No vendor sells the
signal.

But a company staffing up to build a test stack writes the entire thing into its job
descriptions, in public, every week. A req that says *"develop and maintain automated
test sequences in Python, LabVIEW, TestStand"* is a company paying salary to build what
a vendor already sells, and it names the incumbent stack while it does it.

The distinction that matters is **build versus operate**. "Test Engineer" is not a
signal. "Test Engineer who will architect our data acquisition pipeline" is.

## How it works

| Stage | File | What it does | Cost |
|---|---|---|---|
| 1 | `scan.py` | Resolve each target's job board, pull every posting, keyword-filter | $0 |
| 2 | `classify.py` | Per posting: build vs operate posture, named stack, verbatim evidence | $0.11 |
| 3 | `score.py` | Suppress customers, score deterministically, rank | $0 |
| 4 | `render.py` | Emit the standalone page | $0 |

Job boards are read from the public Ashby, Greenhouse and Lever endpoints. Where slug
guessing fails, `scan.py` reads the company's careers page and regexes out the real
board token.

**Scoring is deterministic.** The model extracts posture and stack per posting; Python
computes the account score from four inputs (build-req volume, named legacy tooling,
self-hosted telemetry stack, and build-to-operate ratio). A prompt change can move one
verdict but cannot silently reshuffle the ranking.

**Cost control.** Classification sends keyword-centered excerpts, not whole reqs. A
posting averages ~9.4k characters and the tool names cluster in two or three places.
Excerpting cut input tokens from 2.42M to 582K, a 76% reduction, and improved precision
by removing benefits boilerplate and EEO statements the model would otherwise weigh.

## Three ways this data tried to mislead me

This is the part worth reading. All three produced confident, wrong output before they
were caught.

### 1. Naive matching called 98% of the market a lead

Substring matching flagged **3,427 of 3,497 postings**. Ninety-eight percent is not a
signal, it is a broken filter, and its absurdity is the only reason it got caught.

The cause is acronyms. `HIL` matches inside "while" and "child", so a Workplace
Assistant req scored as a hardware-in-the-loop lead. Acronyms are now matched
case-sensitively with word boundaries, phrases case-insensitively with word boundaries.
That cut 2,398 false positives, **70% of all naive hits**. The classifier then discarded
a further 403 where the tool names were genuinely incidental.

### 2. One job board silently returned a third of each posting

Commonwealth Fusion came back with **0 signals across 58 postings**. Zero is implausible
for a company building tokamaks, which is what made it worth checking.

Lever's `mode=json` endpoint returns only the intro blurb in `descriptionPlain`. The
requirements live in a separate `lists[]` array. The scanner was reading 1,833 of 5,778
characters per posting and missing exactly the section where tool names appear. After
concatenating the sections:

| Company | Before | After |
|---|---|---|
| Commonwealth Fusion | 0 | 11 |
| Zoox | 15 | 61 |
| Venus Aerospace | 6 | 13 |

This is the more dangerous of the two failures. A false positive wastes a rep's time. A
false negative deletes an account from the pipeline and nobody ever learns it existed.

### 3. The model over-answered a list field

Asked to extract named tools, the model volunteers domain nouns to fill the array:
"fluid systems", "mechanical hardware", "accelerometers". Separately it echoes whatever
casing the posting used, so `LabVIEW`, `LabView` and `Labview` counted as three distinct
tools and split one account's stack across three rows.

Display is filtered to a known tool vocabulary and names are canonicalized before
counting. Both failures are quiet: neither throws, and both produce a plausible-looking
column.

## Suppression

Publicly named customers are removed before ranking, each with a citation for where the
relationship was disclosed (see `targets.py`). This matters more than it looks: **the
highest-scoring account in the dataset, at 8 out of 8, was an existing customer.** A
naive scan would have handed a rep a confident, well-evidenced cold brief for a company
the vendor already bills.

## Coverage this does not have

Nineteen of the 51 targeted companies run Workday or custom boards with no public API.
They are absent, not scored zero. Naming the gap is cheaper than letting someone assume
the index is exhaustive.

## Running it

```bash
pip install -r requirements.txt

python3 scan.py                              # free, caches to data/
OPENAI_API_KEY=sk-... python3 classify.py    # ~$0.11, resumable
python3 score.py                             # writes data/index.json
python3 render.py                            # writes index.html
```

Every stage caches. Re-running `scan.py` costs nothing and picks up new postings.
`classify.py` is keyed by company and posting URL, so an interrupted run resumes
instead of re-billing.

Edit `targets.py` to point it at a different market. The method is not specific to
hardware: any category where the incumbent tool is internal infrastructure rather than
a public web technology will work the same way.

## License

MIT.
