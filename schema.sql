-- CinemaMax — PostgreSQL schema
-- Run once: psql -U postgres -d cinema_db -f schema.sql

CREATE TABLE IF NOT EXISTS movies (
    id            SERIAL PRIMARY KEY,
    title         TEXT    NOT NULL,
    genre         TEXT    NOT NULL DEFAULT 'CINEMA',
    is_blockbuster BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS showtimes (
    id         SERIAL PRIMARY KEY,
    movie_id   INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    hall_name  TEXT    NOT NULL,
    show_time  TIME    NOT NULL,
    is_vip     BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS booked_seats (
    id           SERIAL PRIMARY KEY,
    showtime_id  INTEGER NOT NULL REFERENCES showtimes(id) ON DELETE CASCADE,
    seat_row     INTEGER NOT NULL,
    seat_col     INTEGER NOT NULL,
    UNIQUE (showtime_id, seat_row, seat_col)
);

CREATE INDEX IF NOT EXISTS idx_showtimes_movie   ON showtimes(movie_id);
CREATE INDEX IF NOT EXISTS idx_booked_showtime   ON booked_seats(showtime_id);

-- ── Seed data ──────────────────────────────────────────────────
INSERT INTO movies (title, genre, is_blockbuster) VALUES
  ('The Dark Knight',          'ACTION',    true),
  ('Interstellar',             'SCI-FI',    true),
  ('Inception',                'THRILLER',  true),
  ('The Matrix',               'SCI-FI',    false),
  ('Oppenheimer',              'DRAMA',     true),
  ('Dune: Part Two',           'SCI-FI',    true),
  ('Gladiator II',             'ACTION',    true),
  ('John Wick 4',              'ACTION',    false),
  ('Spider-Man: Spider-Verse', 'ANIMATION', false),
  ('Avatar: Way of Water',     'SCI-FI',    true),
  ('Pulp Fiction',             'CRIME',     false),
  ('The Godfather',            'CRIME',     false),
  ('Seven',                    'THRILLER',  false),
  ('Fight Club',               'DRAMA',     false),
  ('Forrest Gump',             'DRAMA',     false),
  ('The Lion King',            'ANIMATION', false),
  ('Joker: Folie à Deux',      'DRAMA',     true),
  ('Deadpool & Wolverine',     'ACTION',    true),
  ('Iron Man',                 'ACTION',    false),
  ('The Avengers',             'ACTION',    true),
  ('Parasite',                 'THRILLER',  false),
  ('Spirited Away',            'ANIMATION', false),
  ('Mad Max: Fury Road',       'ACTION',    false),
  ('Top Gun: Maverick',        'ACTION',    true),
  ('Blade Runner 2049',        'SCI-FI',    false),
  ('The Prestige',             'THRILLER',  false),
  ('Whiplash',                 'DRAMA',     false),
  ('Coco',                     'ANIMATION', false),
  ('Arrival',                  'SCI-FI',    false),
  ('Alien: Romulus',           'HORROR',    true)
ON CONFLICT DO NOTHING;

-- Showtimes: 3 standard halls for every movie, VIP for blockbusters
DO $$
DECLARE
  m RECORD;
BEGIN
  FOR m IN SELECT id, is_blockbuster FROM movies LOOP
    INSERT INTO showtimes (movie_id, hall_name, show_time, is_vip)
    VALUES
      (m.id, 'Hall A', '11:00', false),
      (m.id, 'Hall B', '15:30', false),
      (m.id, 'Hall C', '19:00', false);
    IF m.is_blockbuster THEN
      INSERT INTO showtimes (movie_id, hall_name, show_time, is_vip)
      VALUES (m.id, 'VIP Platinum', '22:00', true);
    END IF;
  END LOOP;
END $$;
