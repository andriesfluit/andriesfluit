# Methodology review — July 2026 (3 months of live data)

Status of the live archive at review time: 82 consecutive live name-only
days (2026-04-20 .. 2026-07-10), no gaps. Thresholds still `v0-eyeballed`.

## The problem with percentile calibration

`calibrate.py` derives zone floors as percentiles of Trump's own observed
distribution ("flooding = top 5% of Trump days"). That is self-referential:
the monitor's premise is that Trump coverage is abnormally high, and
percentile calibration quietly redefines that abnormal level as the
baseline. Zones would then only flag variation *within* the anomaly and the
site's headline claim ("Trump floods the Belgian news zone") would no
longer be supported by its own scale.

## What the data shows (computed 2026-07-11, 82 live days)

Daily share of core-corpus headlines, per figure:

| | median | p95 | max |
|---|---|---|---|
| Trump | 2.76% | 5.83% | 12.67% |
| best NON-Trump figure of the day | 0.62% | 1.82% | 2.66% |
| Putin (highest peer) | 0.29% | 1.07% | 2.59% |
| De Wever (PM) | 0.17% | 0.87% | 2.66% |

- Trump's **median** day (2.76%) exceeds the **all-time best** day of
  every other tracked figure (2.66%).
- On 44 of 82 days Trump exceeded the all-time max of *any* other figure.
- Rank 1 on 81 of 82 days; median dominance 1.85 (Trump alone ~2x all 16
  other figures combined).

The anomaly is not the tail of the distribution — it *is* the
distribution. Calibrating floors on it would erase exactly what the
monitor exists to show.

## Decision: separate LEVEL from VARIATION

Two layers, never mixed:

1. **Structural layer (the claim).** Externally anchored, slow-moving,
   shown as context: "Trump's typical day out-covers any other figure's
   best day" / "N x the attention a US president normally gets". Anchors
   come from `anchors.py`:
   - `peers` mode (offline): distribution of the 16 comparator figures.
   - `gdelt` mode (network): median share of the sitting US president in
     Belgian news during ordinary-presidency reference windows (Trump-I
     2018/2019, Biden 2022/2023), with a GDELT->core scale estimate.
2. **Daily weather layer (the zones).** The composite classifier
   (rank / dominance / breadth / pct) tracks day-to-day variation. Rank
   and dominance are already externally anchored (they compare against
   other figures *today*). The pct floors may stay absolute
   (hand-picked, documented) or be set from the anchors — but NOT from
   percentiles of Trump's own history. If era-relative percentiles are
   ever used, the zone labels must say so explicitly ("high for the
   Trump-II era").

`calibrate.py` output remains useful as a *context annotation* ("today is
p87 of the Trump-II era"), not as zone definition. Do not run
`calibrate.py --write`.

## GDELT anchor results (fetched 2026-07-11, see validation/anchors_report.json)

Share of Belgian GDELT-indexed articles mentioning the sitting US
president, per reference window; core-unit conversion uses the measured
scale factor core ≈ 1.47 × GDELT (median day-ratio over the 83-day
live overlap 2026-04-20 .. 2026-07-11):

| window        | median (GDELT) | p95  | max   | median (core units) |
|---------------|---------------:|-----:|------:|--------------------:|
| Trump-I 2018  | 4.01%          | 6.64 | 10.66 | 5.9%                |
| Trump-I 2019  | 2.36%          | 3.72 |  3.87 | 3.5%                |
| Biden 2022    | 0.78%          | 2.40 |  4.13 | 1.15%               |
| Biden 2023    | 0.00%          | 0.48 |  1.22 | 0.0% (suspect)      |

Reading:

- **Ordinary-presidency norm (Biden 2022, with the Ukraine war on the
  front pages): 1.15% in core units.** Trump-II's current median day
  (2.76%) is ~2.4x that norm; his p95 day (5.8%) is ~5x.
- Biden-2023's flat zero median is suspect (possibly thin GDELT BE
  coverage or silent throttling returning a sparse timeline); weight it
  lightly or re-verify before using. Biden-2022 is the conservative,
  credible norm.
- Honest context the GDELT yardstick also provides: Trump-II today
  (~1.9 GDELT units) sits near Trump-I 2019 (2.36) and *below* the
  Trump-I 2018 trade-war spring (4.01). The flood is structural across
  both Trump eras, not a 2026 novelty.

**Proposed floor ladder** — multiples of the Biden-2022 norm, which
lands remarkably close to the v0-eyeballed values while giving each
zone an external plain-language meaning:

| zone     | proposal (core) | meaning                          | v0-eyeballed |
|----------|----------------:|----------------------------------|-------------:|
| puddles  | >= 1.1%         | 1x normal-president attention    | 0.8%         |
| wet      | >= 2.3%         | 2x normal-president attention    | 1.5%         |
| soaked   | >= 3.4%         | 3x normal-president attention    | 2.5%         |
| flooding | >= 5.7%         | 5x normal-president attention    | 4.0%         |

Rank / dominance / breadth gates stay as they are (externally anchored
by construction). Site copy can carry the structural layer directly:
"vandaag krijgt Trump N x de aandacht die een Amerikaanse president
normaal krijgt in de Belgische media."

## Final design, same day (v3): natural breakpoints, retroactive

v2 still hung the zone ladder on share reference points (which point of
Biden's distribution belongs to which zone?) - every assignment was
contestable and outcome-steering. The resolution: "flooding the zone"
is a claim about CROWDING OUT, and the signals that measure that
directly (rank, dominance, breadth) have NATURAL BREAKPOINTS - values
meaningful by definition, immune to tuning:

| zone     | definition                                                | gates                                  |
|----------|-----------------------------------------------------------|----------------------------------------|
| flooding | #1, double the 16 others COMBINED, majority of outlets    | rank 1, dominance >= 2.0, breadth >= .5 |
| soaked   | #1, out-mentions the 16 others COMBINED (parity)          | rank 1, dominance >= 1.0               |
| wet      | top-2 figure of the day                                   | rank <= 2                              |
| puddles  | top-4 figure of the day                                   | rank <= 4                              |

Dominance 1.0 = parity and 2.0 = double are given by arithmetic; rank
1/2/4 are ordinal; breadth 0.5 = majority. The ONLY external number is
the materiality floor on every zone above dry: share >= 1.15% (the
norm president's median day), so a #1 spot on a dead news day cannot
count. Share ladders are gone entirely; the norm-presidency comparison
lives on as a continuous readout (N x norm), gating nothing.

Applied RETROACTIVELY to the archive on 2026-07-11: 88 live records
recomputed (44 changed zone; prior states remain in git history and
each record carries `zone_recomputed`). Resulting distribution,
strictly a finding: dry 2, puddles 0, wet 13, soaked 46, flooding 27.
In words: on 73 of 88 measured days one man out-mentioned the entire
tracked Belgian and European political top combined; on 27 of those
days doubly so, across a majority of outlets.

## Superseded: v2 floors (same day, kept for the audit trail)

The first adopted ladder set flooding at 5x the norm median, partly
argued from "then flooding fires on ~5% of days" and "it coincides
with Trump's own p95". Both arguments reference Trump's observed
distribution - the exact circularity this review exists to remove,
re-imported through the choice of multiple. Whether flooding is rare
must be a FINDING, never a design input.

Fixed in thresholds version `norm-biden2022-dist-2026-07-11`: every
share floor is now a reference point of the norm president's own
distribution (Biden spring 2022, core units): puddles >= 1.1 (his
median day), wet >= 2.3 (double his median day, an a-priori semantic
step), soaked >= 3.5 (his p95 day), flooding >= 6.1 (his single
busiest day of the window - during the invasion of Ukraine). Observed
frequencies on the 83-day archive, reported strictly as findings:
share-floor exceedance 81 / 55 / 28 / 3 days.

## Adopted 2026-07-11

The multiples-of-norm ladder is live: thresholds.json version
`norm-biden2022-x1-2-3-5-2026-07-11` (floors 1.1 / 2.3 / 3.4 / 5.7,
anchor metadata in the file). Effect on the 83-day live archive,
old floors -> new floors: flooding 15 -> 4 days (now genuinely rare),
soaked 24 -> 23, wet 37 -> 25, puddles 5 -> 29, dry 2 -> 2. The site
hero now carries the structural layer ("N x the attention a US
president normally gets here") and the methodology section explains the
anchor. calibrate.py refuses `--write` without
`--force-self-referential`; its percentile dry-run stays available as
context.

## Detector validation (2026-07-11, validation/labels.jsonl)

325 stratified headlines from the live archive (220 sampled name-only
positives, all 17 family-filtered, all 88 expanded-only), title-only
relevance judgments (labeled by Claude, machine-assisted — spot-check
via `validate_detector.py --show-disagreements`):

| detector                      | precision | recall* |
|-------------------------------|----------:|--------:|
| name-raw (`\btrump\b`)        | 92.0%     | 80.4%   |
| name-donald (production)      | **99.1%** | 80.4%   |
| expanded                      | 83.4%     | 100%    |

*Recall is measured against expanded-detector positives only (the log
stores no detector-negatives), so read it as: ~20% of Trump-relevant
coverage refers to him only indirectly ("Witte Huis", "de Amerikaanse
president"). That is the deliberate name-only tradeoff the site
already documents, now quantified.

Findings:
- The family/building filter earns its keep: it removes 17 real
  false positives (Trump Tower, Ivanka/Kushner resorts) and leaves
  production precision at 99.1% (2 FPs in 220: "Trump Mobile", a
  buffalo resembling Trump).
- The expanded detector's 54 false positives are mostly White
  House-as-location incidents (shootings near the WH, a foiled attack
  at a WH event) and family stories - fine for its display-only role,
  and a reason it must not drive the zone.
- ~~Known name-only miss: the Dutch genitive "Trumps" escapes
  `\btrump\b`.~~ **Fixed 2026-07-11 as a versioned change**
  (`PATTERN_VERSION s-genitive-2026-07-11`): all consonant-ending
  comparator names now accept a trailing s (Trumps, Poetins, De
  Wevers, ...), applied symmetrically so rank/dominance keep their
  footing; daily records log `pattern_version` so the archive marks
  the cut. Jambon deliberately excluded (French plural = hams).
  Revalidation on the same labels: name-only recall 80.4% -> 83.0%,
  precision unchanged at 99.1%.

## Open items

- [ ] Re-verify the biden-2023 window from a non-datacenter IP before
      leaning on it (not used for the anchor).
- [ ] Recall against true negatives needs main.py to persist a daily
      sample of non-matching titles; until then recall is only
      measurable relative to the expanded detector.
- [x] "Trumps" genitive adopted as versioned pattern change
      (s-genitive-2026-07-11, see above).
