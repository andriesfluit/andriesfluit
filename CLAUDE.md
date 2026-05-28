# Project: andriesfluit.com

Persoonlijke website van Andries Fluit, gehost op GitHub Pages (CNAME-bestand → custom domain).

## Stack
- Statische site (HTML/CSS/JS) — geen build step.
- Sub-projecten in eigen mappen: `_mediamonitor/`, `_trumpflood/`, `trumpflood/`.
- Jekyll-rendering uitgeschakeld via `.nojekyll`.

## Conventies
- Voorkeurstaal voor communicatie met Andries: **Nederlands**, tenzij hij Engels schrijft.
- Houd antwoorden kort en direct; geen overbodige preambles.
- Geen PRs aanmaken zonder expliciete vraag.

## Werkbranch
- Default ontwikkelbranch voor Claude-sessies: `claude/modest-mendel-ynh6k`.

## Persoonlijke memory (claudeOS)
Bron lokaal: `~/Documents/Claude/ClaudeOS/`.
Gesynced naar private repo `andriesfluit/claudeos`.
In cloud-sessies wordt de inhoud automatisch ingeladen via `.claude/hooks/session-start.sh`
(vereist env var `CLAUDEOS_TOKEN` in de cloud-environment).
