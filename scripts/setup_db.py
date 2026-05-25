"""Create extensions, tables, and indexes in Neon Postgres."""
from db.connection import get_connection


SETUP_SQL = """
-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Drop existing tables
DROP TABLE IF EXISTS talks CASCADE;
DROP TABLE IF EXISTS scriptures CASCADE;

-- Talks table: one row per paragraph
CREATE TABLE talks (
    id              SERIAL PRIMARY KEY,
    conference      TEXT NOT NULL,
    year            INT NOT NULL,
    month           INT NOT NULL,
    session         TEXT,
    speaker         TEXT NOT NULL,
    speaker_role    TEXT,
    title           TEXT NOT NULL,
    link            TEXT,
    paragraph_num   INT NOT NULL,
    paragraph       TEXT NOT NULL,
    fts             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', paragraph)) STORED,
    embedding       VECTOR(1536)
);

CREATE INDEX talks_year_idx ON talks (year);
CREATE INDEX talks_month_idx ON talks (month);
CREATE INDEX talks_speaker_idx ON talks (speaker);
CREATE INDEX talks_conference_idx ON talks (conference);
CREATE INDEX talks_fts_idx ON talks USING GIN (fts);

-- Scriptures table: one row per verse
CREATE TABLE scriptures (
    id              SERIAL PRIMARY KEY,
    volume          TEXT NOT NULL,
    book            TEXT NOT NULL,
    book_id         INT NOT NULL,
    chapter         INT NOT NULL,
    verse           INT NOT NULL,
    verse_ref       TEXT NOT NULL,
    text            TEXT NOT NULL,
    book_word_count INT NOT NULL,
    fts             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    embedding       VECTOR(1536)
);

CREATE INDEX scriptures_volume_idx ON scriptures (volume);
CREATE INDEX scriptures_book_idx ON scriptures (book);
CREATE INDEX scriptures_bookid_idx ON scriptures (book_id);
CREATE INDEX scriptures_fts_idx ON scriptures USING GIN (fts);
"""


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SETUP_SQL)
        conn.commit()
        print("Schema created successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
