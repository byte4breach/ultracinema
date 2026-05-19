"""
CinemaMax API — FastAPI backend
Serves: /movies  /showtimes/<id>  /booked/<id>  /book
Run:    uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ── Config ─────────────────────────────────────────────────────
DB_DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://database_0zbe_user:YiKpZqSTuPrZwFlOHItjD9K7AU70ttee@dpg-d8631lh9rddc73ev38k0-a/database_0zbe"
)

# ── Lifespan (DB pool) ──────────────────────────────────────────
pool: asyncpg.Pool | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DB_DSN, min_size=2, max_size=10)
    yield
    await pool.close()

app = FastAPI(title="CinemaMax API", lifespan=lifespan)

# ── CORS (allow your GitHub Pages domain + localhost) ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your GH Pages URL in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Models ──────────────────────────────────────────────────────
class BookRequest(BaseModel):
    showtime_id: int
    seats: List[str]   # ["0-3", "0-4", …]

# ── Routes ──────────────────────────────────────────────────────

@app.get("/movies")
async def get_movies():
    """All movies with showtime count."""
    rows = await pool.fetch("""
        SELECT m.id, m.title,
               COALESCE(m.genre, 'CINEMA') AS genre,
               m.is_blockbuster,
               COUNT(s.id) AS show_count
        FROM movies m
        LEFT JOIN showtimes s ON s.movie_id = m.id
        GROUP BY m.id, m.title, m.genre, m.is_blockbuster
        ORDER BY m.title
    """)
    return [dict(r) for r in rows]


@app.get("/showtimes/{movie_id}")
async def get_showtimes(movie_id: int):
    """Showtimes for a movie, with available seat count."""
    rows = await pool.fetch("""
        SELECT s.id, s.hall_name, s.show_time::text AS show_time, s.is_vip,
               CASE WHEN s.is_vip THEN 24 ELSE 96 END
                 - COUNT(b.id) AS available
        FROM showtimes s
        LEFT JOIN booked_seats b ON b.showtime_id = s.id
        WHERE s.movie_id = $1
        GROUP BY s.id, s.hall_name, s.show_time, s.is_vip
        ORDER BY s.show_time
    """, movie_id)
    return [dict(r) for r in rows]


@app.get("/booked/{showtime_id}")
async def get_booked(showtime_id: int):
    """List of booked seat positions as 'row-col' strings."""
    rows = await pool.fetch(
        "SELECT seat_row, seat_col FROM booked_seats WHERE showtime_id = $1",
        showtime_id
    )
    return [f"{r['seat_row']}-{r['seat_col']}" for r in rows]


@app.post("/book")
async def book_seats(req: BookRequest):
    """Book seats. Returns 409 if any seat is already taken."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Lock existing bookings for this showtime
            existing = await conn.fetch(
                "SELECT seat_row, seat_col FROM booked_seats "
                "WHERE showtime_id = $1 FOR UPDATE",
                req.showtime_id
            )
            taken = {f"{r['seat_row']}-{r['seat_col']}" for r in existing}
            conflict = [s for s in req.seats if s in taken]
            if conflict:
                raise HTTPException(
                    status_code=409,
                    detail=f"Seats already taken: {', '.join(conflict)}"
                )

            for pos in req.seats:
                row, col = pos.split("-")
                await conn.execute(
                    "INSERT INTO booked_seats (showtime_id, seat_row, seat_col) "
                    "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                    req.showtime_id, int(row), int(col)
                )
    return {"status": "confirmed", "seats": req.seats}


@app.get("/health")
async def health():
    return {"status": "ok"}
