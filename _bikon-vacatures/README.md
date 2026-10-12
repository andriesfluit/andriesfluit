# Vacaturetest: wie bouwt, beheert of koopt een RAG-chatbot?

Eenmalige test. Verzamelt Belgische vacatures van de laatste 30 dagen, classificeert ze en
maakt een lijst van organisaties die mogelijk hulp nodig hebben met hun RAG-chatbot.
Alles draait lokaal; geen database, geen hosting.

| Fase | Script | Resultaat |
|---|---|---|
| 1. Verzamelen | `collect.py` | `data/raw/`, `data/vacatures.jsonl`, `data/vacatures_fase1.csv`, `data/fase1_overzicht.md` |
| 2. Classificeren | `classify.py` | `data/classificaties.jsonl`, `data/fase2_test.md` |
| 3. Output | `report.py` | `output/vacatures.csv`, `output/samenvatting.md` |

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

## Fase 2 draaien

Zet eerst `ANTHROPIC_API_KEY` in `.env` (aan te maken op console.anthropic.com, onder API Keys).
Na `git pull` installeer je de nieuwe pakketten één keer opnieuw:

```bash
pip install -r requirements.txt
```

Test op 20 willekeurige vacatures (enkele seconden, kost minder dan een cent):

```bash
python classify.py --test 20
```

Dat toont per vacature het oordeel van het model en een kostenschatting voor de volledige set,
en bewaart alles in `data/fase2_test.md`. De volledige set pas na akkoord:

```bash
python classify.py
```

Na een aanpassing aan de prompt toont `python classify.py --retest` dezelfde vacatures als de vorige
test opnieuw, met de vorige score ernaast.

Wat al geclassificeerd is met dezelfde prompt, wordt niet opnieuw gestuurd. Pas je de prompt in
`classify.py` aan, dan classificeert het script automatisch opnieuw.

Hoe het werkt:
- Model `claude-haiku-5-5`, effort `low`, met een vaste systeemprompt (definities van alle velden,
  scoreschaal 1 tot 5) die in de cache van de API blijft, zodat hij maar één keer volledig betaald wordt.
- Het model moet JSON teruggeven volgens een vast schema (structured outputs). Het script valideert
  dat JSON daarna nog eens zelf: ongeldige waarden worden als fout gemeld en niet bewaard.
- Tegenstrijdigheden (bv. "niet relevant" met score 4) worden bewaard maar gemarkeerd.
- Bank, verzekering, overheid, zorg, juridisch, HR en payroll en telecom zijn altijd "gereguleerd";
  zegt het model iets anders, dan past het script dat aan en markeert het.
- De vacaturetekst gaat als gegevens mee, zonder persoonsgegevens (die zijn in fase 1 al verwijderd).

## Fase 3 draaien

```bash
python report.py
```

Geen netwerkverkeer en geen kosten. Het maakt:
- `output/vacatures.csv`: alle geclassificeerde vacatures, hoogste score bovenaan, met puntkomma
  als scheidingsteken (opent zo meteen in kolommen in Excel met Belgische instellingen). De laatste
  kolom `tekst_onvolledig` markeert vacatures die enkel via Adzuna kwamen (500 tekens tekst).
- `output/samenvatting.md`: aantal relevante vacatures, verdeling per signaaltype, sector en rol,
  de top 25 organisaties, ruis per zoekterm, relevant per bron en de kanttekeningen.

Organisatiescore in de top 25: de hoogste score van de relevante vacatures van die organisatie,
plus 0,5 per extra relevante functie (hoogstens +1,5); dezelfde functietitel op meerdere plaatsen
telt één keer. Recruitmentbureaus, interimkantoren en andere tussenpersonen (vacatureplatformen,
freelanceplatformen) tellen niet mee in de top 25.

## Fiches per organisatie (na fase 3)

```bash
python fiches.py
```

Zet de relevante vacatureteksten van de 10 organisaties uit de shortlist in
`output/fiches_input.md` (eigen selectie: `python fiches.py Argenta "Delen Private Bank"`).
Dat bestand dient als basis voor een fiche per organisatie.

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
  (zonder NV, SA, Group, Belgium..., en "&" telt als "and"), functietitel (zonder m/v/x en zonder
  landnaam achteraan) en plaats (Brussel, Bruxelles en Brussels tellen als één plaats). Een vacature
  zonder plaats wordt samengevoegd met dezelfde vacature mét plaats, als er maar één zo is. De versie met de langste tekst blijft over; bronnen en
  zoektermen worden samengevoegd.
- Recruitmentbureaus en interimkantoren worden gemarkeerd (`recruiter_vlag`, met reden), niet
  verwijderd: op naam (lijst van bekende bureaus en woorden als recruitment, interim, staffing)
  of op tekst ("pour l'un de nos clients", "voor een van onze klanten").

## Tests

```bash
python -m unittest discover tests
```

De tests gebruiken verzonnen voorbeeldteksten en doen geen netwerkverkeer.
