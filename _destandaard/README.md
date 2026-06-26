# destandaard

Persoonlijke ochtenddigest van **De Standaard** uit je eigen e-paper-abonnement.
Eén handmatige capture-klik in je ingelogde sessie levert de ruwe editie; de
rest draait automatisch: opschonen → een redacteur-AI kiest en vat samen →
markdown-bestand + e-mail. Met een **feedback-lus** die je smaak leert, en een
**beschermde verrassingssectie** die je uit een echokamer houdt.

## Pipeline

```
capture/bookmarklet.js  dumpt ruwe Twipe-JSON van de editie (jouw sessie)
parse.py                ruwe JSON → schone artikels (echte HTML/entity-decode)
preferences.md          wat jij wil zien (stuurt enkel 'Op maat')
feedback.py             leest data/feedback.md, koppelt aan history.jsonl,
                        bouwt een 'geleerde voorkeuren'-blok voor de selectie
digest.py               Claude kiest KERN (op maat) + VERRASSING (buiten je
                        bubbel, beschermd), vat samen, strikt uit de tekst
render.py               markdown-digest + HTML-mailbody, met feedback-handles
mailer.py               SMTP via Gmail app-password
main.py                 orkestrator
```

### Twee buckets, met opzet

- **Op maat (KERN)** — volgt `preferences.md` én je eerdere feedback.
- **Verrassing** — bewust *buiten* je voorkeuren, maximaal gespreid over
  rubrieken. Feedback mag hier de kwaliteitslat verhogen, maar nooit de sectie
  laten krimpen of naar je smaak toetrekken. Zo voorkomt de feedback-lus dat je
  in een filterbubbel belandt. De vloer staat op `VERRASSING_MIN` in `digest.py`.

### De feedback-lus

Elke digest geeft elk item een kort **handle** (bv. `0626-a3`). Reageer in
`data/feedback.md`:

```
0626-a3 + meer van dit soort duiding
0626-v1 -
```

`history.jsonl` onthoudt wat getoond werd, zodat een handle later terug te
koppelen is aan titel/rubriek. De volgende run vouwt dat samen tot een signaal
voor de **Op maat**-selectie.

## Lokaal draaien

```bash
cd _destandaard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Leg eerst een capture in data/incoming/ (zie capture/README.md), dan:

# Smoke-test zonder API (page-order pick, geen samenvattingen):
python main.py --no-llm

# Echte digest naar bestand (vereist ANTHROPIC_API_KEY), geen mail:
ANTHROPIC_API_KEY=sk-ant-... python main.py --dry-run

# Digest + mail:
ANTHROPIC_API_KEY=sk-ant-... GMAIL_APP_PASSWORD=xxxx \
  python main.py --to andries.fluit@gmail.com
```

Output komt in `data/digests/De_Standaard_{datum}.md` (+ `.html` bij dry-run).

## GitHub Actions

`.github/workflows/destandaard.yml` draait wanneer je een `*.raw.json` naar
`_destandaard/data/incoming/` pusht (en is ook handmatig te starten). Hij bouwt
de digest, mailt hem, commit het digest-bestand + `history.jsonl` terug en
verwijdert de verwerkte ruwe JSON zodat de repo niet aandikt.

Vereiste repo-secrets:

| Secret               | Inhoud                                   |
|----------------------|------------------------------------------|
| `ANTHROPIC_API_KEY`  | Claude API key voor de redacteur-AI      |
| `GMAIL_USER`         | Verzendend gmail-adres                    |
| `GMAIL_APP_PASSWORD` | 16-cijferig Gmail app-wachtwoord         |
| `DESTANDAARD_TO_ADDR`| Ontvangend adres                          |

(Gmail app-wachtwoord aanmaken: zie de uitleg in `_mediamonitor/README.md`.)

## Afstemmen

- Te weinig/te veel items → `--kern` / `--verrassing`, of de constanten in
  `digest.py`.
- Selectie zit naast je interesses → werk `preferences.md` bij en geef feedback.
- Ander model → `MODEL` in `digest.py`.

## Juridisch

Werkt enkel met je eigen abonnement, voor persoonlijk gebruik. De inhoud is
auteursrechtelijk beschermd — niet herpubliceren of verspreiden.
