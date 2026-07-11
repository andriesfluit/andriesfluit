# Capture — de ruwe editie binnenhalen

De e-paper vereist je ingelogde sessie, dus deze ene stap is handmatig. Hij
duurt twee tellen en hoeft niets te weten van selectie of opmaak: hij dumpt
alleen de **ruwe JSON**. De rest van de pijplijn (opschonen, selecteren,
samenvatten, mailen) draait daarna automatisch op die JSON.

## Console (snelste)

1. Open en log in op <https://epaper.standaard.be/> en open de editie van vandaag.
2. **F12** (of Cmd+Option+I) → tabblad **Console**.
3. Plak de inhoud van [`bookmarklet.js`](bookmarklet.js), Enter.
4. Er wordt een bestand `De_Standaard_{datum}.raw.json` gedownload.

## Als bookmarklet (één klik)

Maak een bladwijzer met als URL `javascript:` gevolgd door de geminificeerde
inhoud van `bookmarklet.js`. Klik hem aan terwijl je in een geopende editie zit.

## Daarna

Leg het `.raw.json`-bestand in `_destandaard/data/incoming/`.

- **Lokaal / in een Claude-chat:** `python main.py --dry-run` (zie de hoofd-README).
- **Automatisch mailen:** commit het bestand naar de repo. De GitHub Action
  `destandaard.yml` ziet de push, bouwt de digest, mailt hem en ruimt de ruwe
  JSON weer op.

## Juridisch

Werkt enkel met je eigen abonnement, voor persoonlijk gebruik. De inhoud is
auteursrechtelijk beschermd — niet herpubliceren of verspreiden.
