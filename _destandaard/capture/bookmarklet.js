// De Standaard e-paper — RAW capture
//
// Dumpt de ruwe Twipe-JSON van de huidige editie naar één bestand
// `De_Standaard_{datum}.raw.json`. Alle opschoning en selectie gebeurt
// daarna in Python (parse.py / digest.py) — hier houden we de browserlogica
// bewust minimaal en robuust.
//
// Gebruik:
//   1. Open en log in op https://epaper.standaard.be/ en open een editie.
//   2. F12 → Console, plak dit script, Enter. (Of maak er een bookmarklet van,
//      zie capture/README.md.)
//   3. Leg het gedownloade bestand in _destandaard/data/incoming/.
//
// Verbeteringen t.o.v. het oude script:
//   · Publicaties worden PARALLEL opgehaald (Promise.all) i.p.v. sequentieel.
//   · Geen fragiele HTML/entity-stripping in de browser meer — we bewaren de
//     ruwe HtmlText en laten een echte parser in Python alles decoderen.

(async () => {
  const ED = (location.href.match(/\/data\/(\d+)\//) || [])[1] || prompt('Editie-ID?');
  if (!ED) { alert('Geen editie-ID gevonden.'); return; }
  const base = `https://epaper.standaard.be/data/${ED}/data/`;

  const pkg = await (await fetch(base + `GetContentPackagePublications-${ED}-V3.json`)).json();
  const date = (pkg.PublicationDate || '').slice(0, 10);
  const pubs = (pkg.ContentPackagePublication || []).filter(p => p.TextAvailable);

  const publications = [];
  await Promise.all(pubs.map(async p => {
    try {
      const content = await (await fetch(base + `GetPublicationContentItems-${p.PublicationID}.json`)).json();
      publications.push({ id: p.PublicationID, name: p.PublicationName, content });
    } catch (e) {
      console.warn('Publicatie overgeslagen:', p.PublicationID, e);
    }
  }));

  const bundle = { edition: ED, date, captured_at: new Date().toISOString(), package: pkg, publications };
  const blob = new Blob([JSON.stringify(bundle)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `De_Standaard_${date || ED}.raw.json`;
  a.click();
  console.log(`Klaar — editie ${ED}, ${publications.length} publicaties opgehaald.`);
})();
