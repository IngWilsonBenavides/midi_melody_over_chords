# 🎵 MIDI Melody Curator — Web App

Browser-based UI for listening to and curating MIDI melodies.  
**Stack:** Django + DRF · React + TypeScript + Vite · PostgreSQL · pgAdmin · Docker Compose.

---

## Quick start

```bash
# 1. Enter the webapp directory
cd webapp

# 2. Create your env file (edit passwords if you want)
cp .env.example .env

# 3. Create media directories (already exist in the repo, but needed on a fresh clone)
mkdir -p media/midis/dataset media/midis/generated

# 4. Drop some .mid files in the folders:
#    media/midis/dataset/my_chord_dataset.mid
#    media/midis/generated/improv_01.mid

# 5. Start everything
docker compose up -d

# 6. Open the app
open http://localhost:5173          # React frontend
open http://localhost:8000/admin/   # Django admin  (admin / admin)
open http://localhost:5050          # pgAdmin       (admin@example.com / admin)
```

The backend automatically:
1. Runs database migrations.
2. Scans `media/midis/dataset/` and `media/midis/generated/` for `.mid` files.
3. Creates a Django superuser (`admin` / `admin` by default).

---

## Add more MIDI files at any time

```bash
cp /path/to/my.mid media/midis/generated/

# Then click "🔄 Scan" in the UI, OR call the API:
curl -X POST http://localhost:8000/api/midis/scan/
```

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/midis/` | List with filters: `source_type`, `tag`, `approved`, `favorite`, `min_rating`, `search`, `page` |
| `GET`  | `/api/midis/{id}/` | Item detail |
| `GET`  | `/api/midis/{id}/stream/` | Serve the `.mid` file (for the in-browser player) |
| `PATCH`| `/api/midis/{id}/feedback/` | Save curator feedback (see below) |
| `POST` | `/api/midis/scan/` | Rescan media directories |
| `GET`  | `/api/tags/` | List all tags |

### Feedback payload

```json
{
  "rating":   7,
  "approved": true,
  "favorite": false,
  "tags":     ["rock", "blues"],
  "notes":    "Great groove in bar 3"
}
```

- `rating`: 1–10 (or `null` to clear)
- `approved`: `true` = approved · `false` = rejected · `null` = not reviewed
- `tags`: array of strings, auto-created if new

---

## Filtering examples

```
# List only dataset files with rating ≥ 7
GET /api/midis/?source_type=dataset&min_rating=7

# Approved + tagged "blues"
GET /api/midis/?approved=true&tag=blues

# Favorites
GET /api/midis/?favorite=true

# Not yet reviewed
GET /api/midis/?approved=null

# Search by name
GET /api/midis/?search=improv
```

---

## Ports

| Service  | Host port | What's there |
|----------|-----------|--------------|
| Frontend | 5173      | React curator UI |
| Backend  | 8000      | Django REST API + admin |
| pgAdmin  | 5050      | Database browser |

Change ports in `.env` before starting.

---

## MIDI playback

The in-browser player uses [`html-midi-player`](https://github.com/cifkao/html-midi-player) 
(Magenta.js + SGM soundfont).  
**Internet access required** to load the soundfont on first play.  
A self-hosted soundfont can be configured later by changing the `sound-font` attribute in `MidiPlayer.tsx`.

---

## Useful commands

```bash
# View backend logs
docker compose logs -f backend

# Rebuild after code changes
docker compose up -d --build

# Stop everything
docker compose down

# Stop and delete database
docker compose down -v

# Run Django shell
docker compose exec backend python manage.py shell

# Manual scan
docker compose exec backend python manage.py scan_midis
```
