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

## Open items

- [ ] Run `anchors.py gdelt` where the network is open (Actions runner or
      laptop; GDELT is blocked from some sandboxes) and record the
      normal-presidency anchor.
- [ ] Decide whether to adopt anchor-based pct floors in thresholds.json
      (note: the peer anchor implies *lower* floors than v0-eyeballed —
      flooding at ~2.7% would fire most days, which is truthful as a
      structural statement but weak as a daily signal; hence the
      two-layer split above).
- [ ] Detector validation is still pending and is orthogonal to the
      anchoring question: run `validation/sample_headlines.py`, label
      ~200 headlines, then `validation/validate_detector.py` for
      precision/recall. Measurement accuracy underpins every layer.
