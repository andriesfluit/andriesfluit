# mediamonitor

Dagelijkse mediamonitoring per e-mail voor een vaste lijst van bedrijven die
ik adviseer. Hergebruikt het feed-arsenaal van `_trumpflood/` en voegt
sectorpers toe (HR, retail, wegenbouw, filantropie).

## Pipeline

```
feeds.py        feed-catalogus (Belgische pers + sectorpers)
fetcher.py      fetch + Brussels-local "today" filter (cloudscraper voor Cloudflare)
companies.py    per klant: brief + brede pattern-set (brand + concurrenten + sector + beleid)
matcher.py      brede regex-match op titel + RSS-samenvatting
llm_filter.py   Claude Haiku oordeelt strategische relevantie tegen de brief,
                kent topic-tag + 1-zin nut graf toe
render.py       HTML + tekst e-mailbody met topic-tags
mailer.py       SMTP via Gmail app-password
main.py         orkestrator
```

**Issue monitoring, geen brand monitoring.** De regex-set per klant is bewust
breed: brand + directe concurrenten + sectorthema's + regelgeving + adjacente
thema's waar de klant geloofwaardig op zou kunnen reageren. Claude doet de
strategische filtering tegen de per-klant briefing.

## Lokaal draaien

```bash
cd _mediamonitor
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Preview zonder mail of LLM:
python main.py --dry-run --no-llm

# Preview met LLM (vereist ANTHROPIC_API_KEY):
ANTHROPIC_API_KEY=sk-ant-... python main.py --dry-run

# Echt versturen (vereist ook GMAIL_APP_PASSWORD):
ANTHROPIC_API_KEY=sk-ant-... \
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx \
  python main.py --to andries.fluit@akkanto.com
```

## GitHub Actions

Workflow `.github/workflows/mediamonitor.yml` draait dagelijks ~08:30 Brussel-tijd.
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
- `brief`: 2-4 zinnen die Claude lezen wanneer het beslist of een item strategisch
  relevant is. Beschrijf wie de klant is, welke directe stakeholders, en welke
  thema's waar ze geloofwaardig op kunnen reageren.
- `patterns`: brede lijst regex-patronen (brand + concurrenten + sectorthema's +
  beleid + adjacencies). Hoofdletter-ongevoelig, woordgrenzen. Liever te ruim:
  ruis filtert Claude er wel uit.

Een artikel hit een klant als één pattern vuurt. Daarna oordeelt Claude tegen
de brief of het écht relevant is, en geeft een topictag + 1-zin nut graf.
