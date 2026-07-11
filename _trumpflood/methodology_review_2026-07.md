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

## Open items

- [x] GDELT normal-presidency anchor fetched (2026-07-11, via Actions
      re-runs; per-window resume in anchors.py).
- [ ] Decide whether to adopt the multiples-of-norm ladder above in
      thresholds.json (editorial call; keeps zones close to current
      behaviour but externally defined).
- [ ] Re-verify the biden-2023 window from a non-datacenter IP before
      leaning on it.
- [ ] Detector validation is still pending and is orthogonal to the
      anchoring question: run `validation/sample_headlines.py`, label
      ~200 headlines, then `validation/validate_detector.py` for
      precision/recall. Measurement accuracy underpins every layer.
