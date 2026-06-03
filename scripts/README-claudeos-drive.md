# ClaudeOS Context naar Google Drive

`build-claudeos-context.sh` bouwt uit `~/Documents/Claude/ClaudeOS/` (alle `.md`,
gesorteerd) een enkel document `ClaudeOS Context.md` en upload het naar Google
Drive via rclone. De Drive-connector in Claude chat kan dat bestand vinden, ook
al is de bron-repo `andriesfluit/claudeos` privé.

GitHub blijft de bron van waarheid. Drive is alleen een spiegel van de output.

## Eenmalige setup

### 1. rclone installeren
```bash
brew install rclone
```

### 2. Remote aanmaken op je eigen Google-account
```bash
rclone config
```

Antwoorden:
- `n` (new remote)
- name: `gdrive`
- storage: `drive` (Google Drive)
- `client_id`: leeg (of eigen OAuth-client voor stabielere rate limits)
- `client_secret`: leeg
- scope: `drive.file` (least privilege; rclone ziet alleen wat het zelf
  aanmaakt, en het bestand blijft zichtbaar voor de Drive-connector)
- `root_folder_id`: leeg
- `service_account_file`: leeg
- auto-config: `y` (browser opent, autoriseer met het Google-account dat ook
  aan de Claude chat Drive-connector hangt)
- `team_drive`: `n`
- `y` om op te slaan

Test:
```bash
rclone lsd gdrive:
```
Moet je root-mappen tonen zonder fout.

### 3. Handmatige rooktest
```bash
~/Documents/GitHub/andriesfluit/scripts/build-claudeos-context.sh
```
Verwachte output: `OK: <datum> -> gdrive:ClaudeOS Context.md (N bytes)`.

Controleer in https://drive.google.com dat het bestand `ClaudeOS Context.md`
in My Drive staat.

### 4. Auto-sync aan bestaande post-commit hook hangen
De bestaande hook `~/Documents/Claude/ClaudeOS/.git/hooks/post-commit` pusht al
naar GitHub. Voeg er onderaan een regel aan toe om ook naar Drive te uploaden:

```bash
cat >> ~/Documents/Claude/ClaudeOS/.git/hooks/post-commit << 'EOF'

# Spiegel naar Google Drive (achtergrond, faalt stil)
( ~/Documents/GitHub/andriesfluit/scripts/build-claudeos-context.sh >> /tmp/claudeos-drive.log 2>&1 ) &
EOF
```

Verifieer:
```bash
cat ~/Documents/Claude/ClaudeOS/.git/hooks/post-commit
```

### 5. End-to-end test
1. Wijzig een bestand in `~/Documents/Claude/ClaudeOS/`.
2. Wacht ~10 sec (launchd-watcher commit, post-commit pusht + bouwt + uploadt).
3. `tail /tmp/claudeos-drive.log` moet een `OK: ...`-regel tonen.
4. Ververs Google Drive; tijdstempel van `ClaudeOS Context.md` moet vers zijn.
5. Open een Claude chat met Drive-connector aan, vraag iets uit je memory en
   bevestig dat de connector het bestand vindt.

## Configuratie via env vars (optioneel)
- `CLAUDEOS_SRC` — pad naar bron (default `~/Documents/Claude/ClaudeOS`)
- `RCLONE_REMOTE` — rclone remote-naam (default `gdrive`)
- `CLAUDEOS_DRIVE_NAME` — bestandsnaam in Drive (default `ClaudeOS Context.md`)
- `CLAUDEOS_OUT` — lokaal output-pad (default `/tmp/claudeos-context.md`)

## Troubleshooting
- `rclone ontbreekt` → `brew install rclone`
- `claudeOS bron niet gevonden` → `CLAUDEOS_SRC` klopt niet, of map bestaat niet
- Drive-bestand wordt niet vervangen maar groeit in versies → check dat het
  commando `rclone copyto` is (overschrijft), niet `rclone copy` (kopieert naar map)
- Auth verlopen → `rclone config reconnect gdrive:`
