# mediamonitor

Dagelijkse mediamonitoring per e-mail voor een vaste lijst van bedrijven die
ik adviseer. Hergebruikt het feed-arsenaal van `_trumpflood/`, voegt
sectorpers toe (HR, retail, wegenbouw, filantropie) en doet per-klant
gerichte Google News-zoekopdrachten voor maximale dekking.

## Pipeline

```
feeds.py        outlet-feeds (Belgische pers + sectorpers) + per-klant
                Google News search-feeds (brand, concurrenten, beleid, breed)
fetcher.py      parallelle fetch (10 workers) met rolling lookback-venster
                vanaf last_sent.txt; Brussels-aware; cloudscraper voor Cloudflare
matcher.py      cross-source dedup (canonical URL + difflib-titel-similarity 0.75)
                + regex-match op titel + RSS-samenvatting
companies.py    per klant: brief + patterns (loose match) + search_terms (Google News)
llm_filter.py   Claude Haiku oordeelt strategische relevantie tegen de brief,
                kent topic-tag + 1-zin nut graf + score 1-5 toe
enricher.py     fetch artikel-body via trafilatura (paywall-detectie)
summarizer.py   Claude maakt 2-3 zinnen NL samenvatting strikt uit body
                (fallback naar RSS-snippet bij paywall/fail, géén verzinsels)
render.py       HTML + tekst e-mailbody, gesorteerd op relevance-score
mailer.py       SMTP via Gmail app-password
main.py         orkestrator
```

**Issue monitoring, geen brand monitoring.** Per klant ~30-50 Google
News-zoekopdrachten op merknaam, concurrenten, beleidstermen en brede thema's,
in nl-BE én fr-BE. Claude filtert strategisch tegen de per-klant briefing.

**Geen verzinsels.** De summarizer mag enkel parafraseren wat in de
gefetchte artikel-body staat. Bij paywall of fetch-fail valt hij terug
op de RSS-snippet verbatim met `achter betaalmuur` of `enkel snippet` badge.

## Lokaal draaien

```bash
cd _mediamonitor
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Preview zonder mail, LLM, body-fetch of URL-resolve:
python main.py --dry-run --no-llm --no-enrich --no-resolve

# Preview met alleen Claude relevance-filter (sneller, zonder body-fetch):
ANTHROPIC_API_KEY=sk-ant-... python main.py --dry-run --no-enrich

# Volledige preview (vereist ANTHROPIC_API_KEY):
ANTHROPIC_API_KEY=sk-ant-... python main.py --dry-run

# Echt versturen (vereist ook GMAIL_APP_PASSWORD):
ANTHROPIC_API_KEY=sk-ant-... \
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx \
  python main.py --to andries.fluit@akkanto.com
```

## GitHub Actions

Workflow `.github/workflows/mediamonitor.yml` draait Mon–Fri tegen 07:30 Brussel,
zodat de mail ~08:00 in de inbox ligt.
Vereiste repo-secrets:

| Secret               | Inhoud                                            |
|----------------------|---------------------------------------------------|
| `ANTHROPIC_API_KEY`  | Claude API key voor de relevance-filter           |
| `GMAIL_USER`         | Verzendend gmail-adres (bv. andries.fluit@gmail.com) |
| `GMAIL_APP_PASSWORD` | 16-cijferig Gmail app-wachtwoord                  |
| `MONITOR_TO_ADDR`    | Ontvangend adres (bv. andries.fluit@akkanto.com)  |

### Gmail app-wachtwoord aanmaken

1. Ga naar https://myaccount.google.com/security
2. Zet 2FA aan als dat nog niet zo is
3. Open https://myaccount.google.com/apppasswords
4. Kies "Mail" + "Other (mediamonitor)" → kopieer het 16-cijferig wachtwoord
5. Voeg toe als `GMAIL_APP_PASSWORD` secret in de repo

## Bedrijven aanpassen

Bewerk `companies.py`. Elke klant heeft:

- `label`: zichtbare naam in de mail
- `brief`: 2-4 zinnen die Claude leest wanneer hij beslist of een item
  strategisch relevant is. Beschrijf wie de klant is, welke directe
  stakeholders, en welke thema's waar ze geloofwaardig op kunnen reageren.
- `patterns`: brede lijst regex-patronen voor matching op outlet-feeds
  (brand + concurrenten + sectorthema's + beleid + adjacencies).
  Hoofdletter-ongevoelig, woordgrenzen. Liever te ruim — Claude filtert.
- `search_terms`: per categorie (brand / competitors / policy / broad) een
  lijst exacte zoekfrases. Elke term wordt geëxpandeerd naar een nl-BE +
  fr-BE Google News search-feed (exact-phrase via "...").

Een artikel hit een klant als een pattern vuurt OF als de search-feed-origine
de klant identificeert. Daarna oordeelt Claude (relevant + score 1-5 + topic
tag + 1-zin nut graf). De mail toont items per klant gesorteerd op score.

## Tuning na verloop van tijd

- Te veel ruis voor een klant → `search_terms.broad` inkrimpen of te brede
  termen verplaatsen naar `patterns` (vangt alleen via outlet-feeds, niet
  via search).
- Te weinig coverage → search-term toevoegen aan de juiste categorie.
- Duplicaten die niet worden samengevoegd → in `matcher.py` `title_threshold`
  van 0.75 lichtjes verlagen, of bekijken of de canonical URL-resolve faalt.
