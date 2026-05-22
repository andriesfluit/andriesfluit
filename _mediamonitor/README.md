# mediamonitor

Dagelijkse mediamonitoring per e-mail voor een vaste lijst van bedrijven die
ik adviseer. Hergebruikt het feed-arsenaal van `_trumpflood/` en voegt
sectorpers toe (HR, retail, wegenbouw, filantropie).

## Pipeline

```
feeds.py        feed-catalogus (Belgische pers + sectorpers)
fetcher.py      fetch + Brussels-local "today" filter (cloudscraper voor Cloudflare)
companies.py    bedrijfs-configs met regex match-rules per bedrijf
matcher.py      regex-matching van artikels op bedrijven
llm_filter.py   Claude (Haiku) drop false positives en zet 1-lijn nut graf
render.py       HTML + tekst e-mailbody
mailer.py       SMTP via Gmail app-password
main.py         orkestrator
```

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

Bewerk `companies.py`. Elk bedrijf heeft één of meer rules met:

- `any`: lijst regex-patronen die in titel+samenvatting moeten matchen
- `context_any` *(optioneel)*: minstens één van deze moet óók matchen (disambiguatie)
- `none` *(optioneel)*: geen van deze mag matchen (exclusies)

Een artikel hit een bedrijf als één van zijn rules vuurt. Daarna doet Claude
de tweede pass.
