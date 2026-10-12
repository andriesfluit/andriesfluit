# Vacaturetest: wie bouwt, beheert of koopt een RAG-chatbot?

Eenmalige test. Verzamelt Belgische vacatures van de laatste 30 dagen, classificeert ze en
maakt een lijst van organisaties die mogelijk hulp nodig hebben met hun RAG-chatbot.
Alles draait lokaal; geen database, geen hosting.

| Fase | Script | Resultaat |
|---|---|---|
| 1. Verzamelen | `collect.py` | `data/raw/`, `data/vacatures.jsonl`, `data/vacatures_fase1.csv`, `data/fase1_overzicht.md` |
| 2. Classificeren | `classify.py` (volgt na akkoord op fase 1) | |
| 3. Output | `report.py` (volgt na akkoord op fase 2) | `output/vacatures.csv`, `output/samenvatting.md` |

## Installatie (eenmalig)

Python 3.10 of nieuwer.

```bash
cd _bikon-vacatures
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # vul ADZUNA_APP_ID en ADZUNA_APP_KEY in
```

## Fase 1 draaien

Eerst een kleine proefrun (enkele minuten), om te zien of elke bron antwoordt:

```bash
python collect.py --terms RAG chatbot "AI Act" --no-linkedin-details
```

Dan de volledige run:

```bash
python collect.py
```

Reken op 1 tot 2 uur: LinkedIn geeft in de zoekresultaten geen vacaturetekst, dus die wordt per
vacature apart opgehaald, met telkens 3 tot 6 seconden pauze. Met `--no-linkedin-details` gaat
het veel sneller, maar dan heeft fase 2 voor LinkedIn enkel titel en bedrijf.

Een onderbroken run kan je gewoon opnieuw starten: wat al volledig in `data/raw/` staat, wordt
niet opnieuw opgehaald. `--refresh` haalt alles opnieuw op; `--only-process` haalt niets op en
verwerkt enkel `data/raw/` opnieuw (bv. na een aanpassing aan deduplicatie of recruitervlag).

Het overzicht verschijnt op het scherm en in `data/fase1_overzicht.md`.

### Opties

| Optie | Betekenis |
|---|---|
| `--sources indeed linkedin glassdoor adzuna google` | welke bronnen (standaard alle behalve google) |
| `--terms ...` | enkel deze zoektermen (exact zoals in `common.py`) |
| `--max 50` | resultaten per zoekterm per bron, nooit meer dan 50 |
| `--days 30` | enkel vacatures van de laatste N dagen, nooit meer dan 30 |
| `--no-linkedin-details` | LinkedIn zonder vacaturetekst |
| `--loose` | zoektermen niet als exacte woordgroep zoeken |
| `--seed 1` | vaste keuze van de tien voorbeelden |

## Regels die in de code zitten

- Geen login, geen accounts, geen eigen cookies: enkel publieke zoekpagina's en de Adzuna-API.
- Maximaal 50 resultaten per zoekterm per bron, enkel de laatste 30 dagen (ook nagecontroleerd
  op de datum na het ophalen).
- 3 tot 6 seconden pauze voor elk request naar dezelfde bron, ook binnen JobSpy.
- Blokkeert of rate-limit een bron (HTTP 401, 403, 429 of 999, een "blocked"-melding van JobSpy,
  herhaalde doorverwijzing naar een inlogpagina, of 3 verbindingsfouten op rij), dan wordt die
  bron voor de rest van de run overgeslagen en gemeld. Geen proxies, geen omzeilingen.
- Persoonsgegevens worden verwijderd voor iets op schijf komt: het e-mailveld van JobSpy wordt
  niet bewaard, en in de vacaturetekst worden e-mailadressen, telefoonnummers,
  LinkedIn-profielen en namen in contactzinnen ("Vragen? Contacteer ...") vervangen door
  `[... verwijderd]`. Dat werkt met patronen, dus het is niet waterdicht: kijk bij twijfel na.

## Deduplicatie en recruitervlag

- Dubbels over bronnen en zoektermen heen worden samengevoegd op genormaliseerde bedrijfsnaam
  (zonder NV, SA, Group, Belgium...), functietitel (zonder m/v/x) en plaats (Brussel, Bruxelles
  en Brussels tellen als één plaats). De versie met de langste tekst blijft over; bronnen en
  zoektermen worden samengevoegd.
- Recruitmentbureaus en interimkantoren worden gemarkeerd (`recruiter_vlag`, met reden), niet
  verwijderd: op naam (lijst van bekende bureaus en woorden als recruitment, interim, staffing)
  of op tekst ("pour l'un de nos clients", "voor een van onze klanten").

## Tests

```bash
python -m unittest discover tests
```

De tests gebruiken verzonnen voorbeeldteksten en doen geen netwerkverkeer.
