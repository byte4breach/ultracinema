# CinemaMax — Telegram Mini App + Web App

Full cinema ticket booking app that works both inside Telegram and in any browser.

---

## Architecture

```
GitHub Pages (FREE, static)          Your Server (VPS / Render / Railway)
┌──────────────────────┐             ┌──────────────────────────────┐
│   index.html         │  ← fetch()  │   api.py  (FastAPI, :8000)   │
│   (Telegram Mini App)│ ──────────► │   - GET /movies              │
│   (Regular website)  │             │   - GET /showtimes/<id>      │
└──────────────────────┘             │   - GET /booked/<id>         │
                                     │   - POST /book               │
                                     ├──────────────────────────────┤
         Telegram                    │   bot.py  (python-telegram)  │
         ┌──────────┐                │   - /start command           │
         │  Bot     │ ──────────────►│   - inline booking flow      │
         │ @yourbot │                └──────────────────────────────┘
         └──────────┘                           │
                                                ▼
                                     ┌──────────────────┐
                                     │   PostgreSQL      │
                                     │   cinema_db       │
                                     └──────────────────┘
```

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | Mini App + website (upload to GitHub Pages) |
| `api.py` | FastAPI REST backend (run on your server) |
| `bot.py` | Telegram bot (run on your server) |
| `schema.sql` | PostgreSQL schema + seed data |
| `requirements.txt` | Python dependencies |

---

## Step 1 — Database

```bash
# Create the database
createdb -U postgres cinema_db

# Run the schema (creates tables + seeds 30 movies)
psql -U postgres -d cinema_db -f schema.sql
```

---

## Step 2 — Backend (api.py + bot.py)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

```bash
export BOT_TOKEN="your_telegram_bot_token"
export DATABASE_URL="postgresql://postgres:password@localhost:5432/cinema_db"
export WEB_APP_URL="https://YOUR_USERNAME.github.io/cinemamax"
export API_URL="http://localhost:8000"   # or your public URL
```

### Run the API

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Run the bot (in a separate terminal)

```bash
python bot.py
```

> **Production tip:** use `systemd`, `supervisor`, or `screen` to keep both running.

---

## Step 3 — Frontend (GitHub Pages)

1. Create a public GitHub repo called `cinemamax`
2. Upload `index.html` to the repo root
3. Go to **Settings → Pages → Source → Deploy from branch → main / root**
4. Your URL: `https://YOUR_USERNAME.github.io/cinemamax`

### Point the frontend at your API

Open `index.html` and set the `API_URL` constant near the top:

```javascript
const API_URL = "https://your-server.com:8000";
//               ↑ your public API URL
```

Then re-upload `index.html` to GitHub.

> **No HTTPS on your server?** Use Nginx as a reverse proxy with a free Let's Encrypt cert, or deploy to **Render** / **Railway** (they give you HTTPS automatically).

---

## Step 4 — Register with BotFather

1. Open @BotFather → `/newapp` (or `/editapp`)
2. Select your bot
3. Enter your GitHub Pages URL as the Web App URL
4. Done — Telegram now trusts that domain

---

## Deployment options for the API

| Platform | Cost | Notes |
|----------|------|-------|
| **Render** (render.com) | Free tier | Add PostgreSQL add-on, set env vars |
| **Railway** (railway.app) | ~$5/mo | `railway up`, built-in Postgres |
| **Fly.io** | Free tier | `fly launch` |
| **Your own VPS** | ~$5/mo | Nginx + systemd |

### Example Render deployment

1. Push all files (except `index.html`) to a GitHub repo
2. New Web Service → connect repo → Start Command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
3. Add env var: `DATABASE_URL` (from Render's Postgres add-on)
4. Copy the public URL → paste into `index.html` as `API_URL`

---

## How it works

```
User opens Telegram → /start
  → Bot shows two buttons:
      📱 Open Web App  →  GitHub Pages (index.html)
      🤖 Book in Telegram  →  inline conversation flow

Web App flow:
  index.html loads → fetch("/movies") → shows gallery
  User picks movie → fetch("/showtimes/id") → shows times
  User picks time  → fetch("/booked/id")   → shows seat grid
  User picks seats → POST "/book"          → confirmed ✓
  → tg.sendData() notifies the bot

Telegram flow:
  bot.py calls API for all data (same endpoints)
  Uses inline keyboard buttons for navigation
```

---

## Demo / offline mode

If `API_URL` is empty (`""`), `index.html` uses built-in demo data with a deterministic LCG random for booked seats. No server needed for basic testing.

---

## Database schema

```
movies         id, title, genre, is_blockbuster
showtimes      id, movie_id → movies, hall_name, show_time, is_vip
booked_seats   id, showtime_id → showtimes, seat_row, seat_col  (UNIQUE)
```
