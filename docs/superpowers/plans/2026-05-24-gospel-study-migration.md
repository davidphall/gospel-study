# Gospel Study Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the Gospel Study R Shiny app as a Python Dash app deployable to Vercel, backed by Neon Postgres and OpenAI, preserving the identical user experience.

**Architecture:** Multi-page Dash app with dash-bootstrap-components for layout. Neon Postgres with pgvector for data storage, full-text search, and vector similarity. OpenAI GPT-4o for chat, text-embedding-3-small for embeddings. Vercel Python serverless for hosting.

**Tech Stack:** Python 3.11, Dash 2.x, dash-bootstrap-components, Plotly, psycopg2, openai, httpx, beautifulsoup4, pandas, numpy

**Spec:** `docs/superpowers/specs/2026-05-24-gospel-study-migration-design.md`

**Existing R source (read-only reference):** `C:\Users\dave2\OneDrive\Desktop\gospel-study-v4`

---

## File Map

```
gospel-study-r/
├── app.py                          # Dash app entry, WSGI export for Vercel
├── pages/
│   ├── home.py                     # Home tab: image, quote, stats, update button
│   ├── trends.py                   # Keyword/phrase search + proximity search
│   ├── promises.py                 # Promise phrase search with filters
│   ├── invitations.py              # Invitation phrase search with filters
│   ├── questions.py                # Question sentence search with filters
│   ├── scripture_frequency.py      # Word frequency by book with charts
│   ├── scripture_context.py        # Words-in-context with ngram analysis
│   └── chat.py                     # Unified RAG chat over talks + scriptures
├── components/
│   ├── sidebar.py                  # Collapsible sidebar with grouped menu items
│   └── filters.py                  # Reusable conference/speaker/year filter row
├── db/
│   ├── connection.py               # Neon Postgres connection pool
│   └── queries.py                  # All parameterized SQL queries
├── services/
│   ├── openai_client.py            # Embedding + chat completion wrappers
│   ├── scraper.py                  # Conference talk scraper (BeautifulSoup)
│   └── text_analysis.py            # Ngram, stopword, windowing logic
├── scripts/
│   ├── export_scriptures.R         # One-time: Rdata → CSV
│   ├── setup_db.py                 # Create extensions, tables, indexes
│   ├── seed_talks.py               # CSV → talks table (with paragraph splitting)
│   ├── seed_scriptures.py          # CSV → scriptures table
│   └── generate_embeddings.py      # Batch embed all rows via OpenAI
├── tests/
│   ├── test_queries.py             # DB query unit tests
│   ├── test_text_analysis.py       # Ngram/windowing tests
│   ├── test_scraper.py             # Scraper parsing tests
│   └── test_search.py              # FTS query builder tests
├── assets/
│   ├── custom.css                  # Dashboard theme (ported from R app)
│   ├── Jesus_color.jpg             # Home page image
│   └── Jesus_bnw.jpg               # Alternate image
├── requirements.txt
├── vercel.json
├── .env.local                      # DATABASE_URL, OPENAI_API_KEY (gitignored)
└── .gitignore
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `vercel.json`
- Create: `.gitignore`
- Create: `.env.local`

- [ ] **Step 1: Create requirements.txt**

```txt
dash==2.18.2
dash-bootstrap-components==1.6.0
plotly==6.0.1
psycopg2-binary==2.9.10
openai==1.82.0
httpx==0.28.1
beautifulsoup4==4.13.4
pandas==2.2.3
numpy==2.2.6
python-dotenv==1.1.0
gunicorn==23.0.0
pytest==8.3.5
```

- [ ] **Step 2: Create vercel.json**

```json
{
  "builds": [
    { "src": "app.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/assets/(.*)", "dest": "assets/$1" },
    { "src": "/(.*)", "dest": "app.py" }
  ]
}
```

- [ ] **Step 3: Create .gitignore**

```
.env.local
__pycache__/
*.pyc
.pytest_cache/
venv/
node_modules/
.vercel/
```

- [ ] **Step 4: Create .env.local**

```
DATABASE_URL=postgresql://your_user:your_password@ep-xxx.us-east-2.aws.neon.tech/gospel-study?sslmode=require
OPENAI_API_KEY=sk-your-new-key-here
```

- [ ] **Step 5: Create empty directory structure**

Run:
```bash
mkdir pages components db services scripts tests assets
```

- [ ] **Step 6: Install dependencies**

Run:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 7: Copy image assets from R app**

Run:
```bash
copy "C:\Users\dave2\OneDrive\Desktop\gospel-study-v4\www\Jesus_color.jpg" assets\Jesus_color.jpg
copy "C:\Users\dave2\OneDrive\Desktop\gospel-study-v4\www\Jesus_bnw.jpg" assets\Jesus_bnw.jpg
```

- [ ] **Step 8: Initialize git repo and commit**

Run:
```bash
git init
git add .
git commit -m "chore: scaffold project with dependencies and config"
```

---

## Task 2: Database Connection & Schema Setup

**Files:**
- Create: `db/connection.py`
- Create: `scripts/setup_db.py`
- Test: `tests/test_queries.py` (placeholder for later)

- [ ] **Step 1: Write db/connection.py**

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(".env.local")

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def execute_query(query, params=None):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return None


def execute_many(query, params_list):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
        conn.commit()
```

- [ ] **Step 2: Write scripts/setup_db.py**

```python
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
```

- [ ] **Step 3: Run schema setup against Neon**

Run:
```bash
python -m scripts.setup_db
```
Expected: "Schema created successfully."

- [ ] **Step 4: Commit**

```bash
git add db/ scripts/setup_db.py
git commit -m "feat: add database connection and schema setup"
```

---

## Task 3: Data Export & Seed Scripts

**Files:**
- Create: `scripts/export_scriptures.R`
- Create: `scripts/seed_talks.py`
- Create: `scripts/seed_scriptures.py`

- [ ] **Step 1: Write scripts/export_scriptures.R**

This one-time R script exports the Rdata corpus to a flat CSV that Python can read.

```r
load("C:/Users/dave2/OneDrive/Desktop/gospel-study-v4/data/scriptures.Rdata")

# scriptures is a data.frame loaded from the Rdata file
# Export relevant columns to CSV
write.csv(
  scriptures[, c("volume_title", "book_title", "book_id",
                  "chapter_number", "verse_number", "verse_title",
                  "text", "book_word_count")],
  file = "data/scriptures.csv",
  row.names = FALSE
)

cat("Exported", nrow(scriptures), "verses to data/scriptures.csv\n")
```

Note: Column names in the Rdata file may differ slightly. Run this in R and inspect the output. Adjust column names if needed. The key columns we need are: volume, book, book_id, chapter, verse, verse_ref (display name like "1 Nephi 3:7"), text, book_word_count.

- [ ] **Step 2: Run the R export**

Run in R (or RStudio):
```bash
Rscript scripts/export_scriptures.R
```
Expected: Creates `data/scriptures.csv`. Verify it has ~32K+ rows and the expected columns.

- [ ] **Step 3: Write scripts/seed_talks.py**

```python
"""Load talk_df.csv into the talks table, splitting text into paragraphs."""
import csv
import re
from db.connection import get_connection


EXCLUDED_TITLES = [
    "Sustaining of Church Officers",
    "Sustaining of General Authorities",
    "Church Audit Committee Report",
    "Church Auditing Department Report",
    "Statistical Report",
]

INSERT_SQL = """
    INSERT INTO talks (conference, year, month, session, speaker, speaker_role,
                       title, link, paragraph_num, paragraph)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def split_into_paragraphs(text, min_words=30, max_words=500):
    """Split a talk's full text into paragraph-sized chunks.

    The CSV stores talks as one continuous string (paragraph breaks were lost
    during scraping). We split on sentence boundaries, grouping sentences into
    chunks of roughly min_words–max_words each.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    paragraphs = []
    current = []
    word_count = 0

    for sentence in sentences:
        s_words = len(sentence.split())
        if word_count + s_words > max_words and current:
            paragraphs.append(" ".join(current))
            current = [sentence]
            word_count = s_words
        else:
            current.append(sentence)
            word_count += s_words

    if current:
        last = " ".join(current)
        if paragraphs and word_count < min_words:
            paragraphs[-1] += " " + last
        else:
            paragraphs.append(last)

    return paragraphs


def month_name(month_str):
    return "April" if month_str.strip() == "04" else "October"


def main():
    csv_path = "C:/Users/dave2/OneDrive/Desktop/gospel-study-v4/data/talk_df.csv"
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["title"]
            if any(excl in title for excl in EXCLUDED_TITLES):
                continue

            text = row.get("text", "")
            if not text.strip():
                continue

            year = int(row["year"])
            month_str = row["month"].strip().zfill(2)
            month_int = int(month_str)
            conference = f"{month_name(month_str)} {year}"
            speaker = row["speaker"]
            speaker_role = row.get("speaker_role") or None
            link = row.get("link") or None

            paragraphs = split_into_paragraphs(text)

            for i, para in enumerate(paragraphs, start=1):
                cur.execute(INSERT_SQL, (
                    conference, year, month_int, None, speaker,
                    speaker_role, title, link, i, para,
                ))
                inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {inserted} paragraph rows from talks.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run seed_talks.py**

Run:
```bash
python -m scripts.seed_talks
```
Expected: "Inserted NNNNN paragraph rows from talks." (roughly 15K–25K rows depending on chunk sizes)

- [ ] **Step 5: Write scripts/seed_scriptures.py**

```python
"""Load scriptures.csv into the scriptures table."""
import csv
from db.connection import get_connection


INSERT_SQL = """
    INSERT INTO scriptures (volume, book, book_id, chapter, verse,
                            verse_ref, text, book_word_count)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def main():
    csv_path = "data/scriptures.csv"
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("text", "")
            if not text.strip():
                continue

            cur.execute(INSERT_SQL, (
                row["volume_title"],
                row["book_title"],
                int(row["book_id"]),
                int(row["chapter_number"]),
                int(row["verse_number"]),
                row["verse_title"],
                text,
                int(row["book_word_count"]),
            ))
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {inserted} scripture verses.")


if __name__ == "__main__":
    main()
```

Note: Column names (`volume_title`, `book_title`, `chapter_number`, `verse_number`, `verse_title`, `book_word_count`) must match the CSV headers from the R export. If the R export used different names, update this script to match.

- [ ] **Step 6: Run seed_scriptures.py**

Run:
```bash
python -m scripts.seed_scriptures
```
Expected: "Inserted ~41995 scripture verses."

- [ ] **Step 7: Verify data in Neon**

Run:
```bash
python -c "from db.connection import execute_query; print(execute_query('SELECT COUNT(*) AS cnt FROM talks')); print(execute_query('SELECT COUNT(*) AS cnt FROM scriptures'))"
```
Expected: Both return row counts.

- [ ] **Step 8: Commit**

```bash
git add scripts/ data/
git commit -m "feat: add data export and seed scripts for talks and scriptures"
```

---

## Task 4: Embedding Generation

**Files:**
- Create: `services/openai_client.py`
- Create: `scripts/generate_embeddings.py`

- [ ] **Step 1: Write services/openai_client.py**

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env.local")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

DEFAULT_SYSTEM_PROMPT = (
    "You are a faithful member of the Church of Jesus Christ of Latter-Day Saints (LDS). "
    "You always provide answers in line with LDS beliefs. In all responses, cite references "
    "from scriptures and modern Prophets in your answers. Be concise and format as a table "
    "when making comparisons."
)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts. Max ~8K tokens per request."""
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def chat_completion(messages: list[dict], system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    """Non-streaming chat completion."""
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(model=CHAT_MODEL, messages=full_messages)
    return response.choices[0].message.content


def chat_completion_stream(messages: list[dict], system_prompt: str = DEFAULT_SYSTEM_PROMPT):
    """Streaming chat completion. Yields content chunks."""
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    stream = client.chat.completions.create(
        model=CHAT_MODEL, messages=full_messages, stream=True
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

- [ ] **Step 2: Write scripts/generate_embeddings.py**

```python
"""Batch-generate embeddings for all talks and scriptures, writing them to Postgres."""
import time
from db.connection import get_connection
from services.openai_client import get_embeddings


BATCH_SIZE = 200


def embed_table(table: str, text_column: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT id, {text_column} FROM {table} WHERE embedding IS NULL ORDER BY id")
    rows = cur.fetchall()
    total = len(rows)
    print(f"Embedding {total} rows from {table}...")

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]

        embeddings = get_embeddings(texts)

        for row_id, emb in zip(ids, embeddings):
            cur.execute(
                f"UPDATE {table} SET embedding = %s WHERE id = %s",
                (emb, row_id),
            )

        conn.commit()
        done = min(i + BATCH_SIZE, total)
        print(f"  {done}/{total} done")
        time.sleep(1)

    cur.close()
    conn.close()
    print(f"Finished embedding {table}.")


def build_hnsw_indexes():
    conn = get_connection()
    cur = conn.cursor()
    print("Building HNSW indexes (this may take a few minutes)...")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS talks_embedding_idx "
        "ON talks USING hnsw (embedding vector_cosine_ops)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS scriptures_embedding_idx "
        "ON scriptures USING hnsw (embedding vector_cosine_ops)"
    )
    conn.commit()
    cur.close()
    conn.close()
    print("HNSW indexes created.")


def main():
    embed_table("talks", "paragraph")
    embed_table("scriptures", "text")
    build_hnsw_indexes()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run embedding generation**

Run:
```bash
python -m scripts.generate_embeddings
```
Expected: Takes 5–15 minutes. Prints progress. Cost ~$0.10 total.

- [ ] **Step 4: Verify embeddings exist**

Run:
```bash
python -c "from db.connection import execute_query; print(execute_query('SELECT COUNT(*) FROM talks WHERE embedding IS NOT NULL')); print(execute_query('SELECT COUNT(*) FROM scriptures WHERE embedding IS NOT NULL'))"
```
Expected: Counts match total rows.

- [ ] **Step 5: Commit**

```bash
git add services/openai_client.py scripts/generate_embeddings.py
git commit -m "feat: add OpenAI client and batch embedding generation"
```

---

## Task 5: Database Query Layer

**Files:**
- Create: `db/queries.py`
- Create: `tests/test_queries.py`

- [ ] **Step 1: Write the failing tests in tests/test_queries.py**

```python
"""Tests for database query functions.

These are integration tests that hit the real Neon database.
Run after seeding data.
"""
import pytest
from db.queries import (
    get_corpus_stats,
    search_talks_fts,
    search_talks_proximity,
    search_talks_regex,
    get_speakers,
    get_conferences,
    search_scriptures,
    get_scripture_volumes,
    get_scripture_frequency,
    get_similar_talks,
    get_similar_scriptures,
    get_missing_conferences,
)


def test_corpus_stats_returns_counts():
    stats = get_corpus_stats()
    assert stats["talk_count"] > 0
    assert stats["speaker_count"] > 0
    assert stats["conference_count"] > 0
    assert stats["year_count"] > 0


def test_search_talks_fts_exact():
    results = search_talks_fts("faith", mode="exact")
    assert len(results) > 0
    assert "year" in results[0]
    assert "speaker" in results[0]
    assert "paragraph" in results[0]


def test_search_talks_fts_fuzzy():
    results = search_talks_fts("faith", mode="fuzzy")
    assert len(results) > 0


def test_search_talks_regex_promises():
    results = search_talks_regex(
        "I promise you|I promise that", year_min=1971, year_max=2025
    )
    assert len(results) > 0


def test_get_speakers_returns_list():
    speakers = get_speakers()
    assert len(speakers) > 100


def test_get_conferences_returns_list():
    conferences = get_conferences()
    assert len(conferences) > 50


def test_search_scriptures():
    results = search_scriptures("faith", volumes=["Book of Mormon"])
    assert len(results) > 0
    assert "verse_ref" in results[0]


def test_get_scripture_volumes():
    volumes = get_scripture_volumes()
    assert "Book of Mormon" in volumes


def test_get_scripture_frequency():
    freq = get_scripture_frequency("faith", volumes=["Book of Mormon"], normalize=False)
    assert len(freq) > 0
    assert "book" in freq[0]
    assert "count" in freq[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_queries.py -v
```
Expected: All fail with ImportError (db.queries functions don't exist yet).

- [ ] **Step 3: Write db/queries.py**

```python
"""All database queries for the Gospel Study app."""
from db.connection import execute_query


def get_corpus_stats() -> dict:
    rows = execute_query("""
        SELECT
            COUNT(DISTINCT title) AS talk_count,
            COUNT(DISTINCT speaker) AS speaker_count,
            COUNT(DISTINCT conference) AS conference_count,
            COUNT(DISTINCT year) AS year_count
        FROM talks
    """)
    return dict(rows[0])


def get_speakers() -> list[str]:
    rows = execute_query(
        "SELECT DISTINCT speaker FROM talks ORDER BY speaker"
    )
    return [r["speaker"] for r in rows]


def get_conferences() -> list[str]:
    rows = execute_query(
        "SELECT DISTINCT conference, year, month FROM talks ORDER BY year DESC, month DESC"
    )
    return [r["conference"] for r in rows]


def search_talks_fts(term: str, mode: str = "exact",
                     speakers: list[str] = None,
                     year_min: int = None, year_max: int = None) -> list[dict]:
    """Full-text search on talks. mode is 'exact' or 'fuzzy'."""
    if mode == "fuzzy":
        tsquery = " | ".join(f"{w}:*" for w in term.split())
        fts_clause = "fts @@ to_tsquery('english', %(tsquery)s)"
    else:
        fts_clause = "fts @@ plainto_tsquery('english', %(tsquery)s)"
        tsquery = term

    where = [fts_clause]
    params = {"tsquery": tsquery}

    if speakers:
        where.append("speaker = ANY(%(speakers)s)")
        params["speakers"] = speakers
    if year_min is not None:
        where.append("year >= %(year_min)s")
        params["year_min"] = year_min
    if year_max is not None:
        where.append("year <= %(year_max)s")
        params["year_max"] = year_max

    sql = f"""
        SELECT year, month, conference, speaker, title, link,
               paragraph, paragraph_num,
               ts_headline('english', paragraph,
                   plainto_tsquery('english', %(highlight_term)s),
                   'StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=50'
               ) AS snippet
        FROM talks
        WHERE {" AND ".join(where)}
        ORDER BY year DESC, month DESC, title, paragraph_num
        LIMIT 2000
    """
    params["highlight_term"] = term
    return [dict(r) for r in execute_query(sql, params)]


def search_talks_proximity(word1: str, word2: str, window: int = 5,
                           ordered: bool = False) -> list[dict]:
    """Proximity search: find paragraphs where word1 and word2 appear within N words."""
    if ordered:
        pattern = rf"\m{word1}\M\W+(?:\w+\W+){{0,{window}}}\m{word2}\M"
    else:
        pattern = (
            rf"\m{word1}\M\W+(?:\w+\W+){{0,{window}}}\m{word2}\M"
            rf"|\m{word2}\M\W+(?:\w+\W+){{0,{window}}}\m{word1}\M"
        )

    sql = """
        SELECT year, month, conference, speaker, title, link,
               paragraph, paragraph_num
        FROM talks
        WHERE paragraph ~* %(pattern)s
        ORDER BY year DESC, month DESC, title, paragraph_num
        LIMIT 2000
    """
    return [dict(r) for r in execute_query(sql, {"pattern": pattern})]


def search_talks_regex(pattern: str, speakers: list[str] = None,
                       conferences: list[str] = None,
                       year_min: int = None, year_max: int = None) -> list[dict]:
    """Regex search on paragraph text (for promises, invitations, questions)."""
    where = ["paragraph ~* %(pattern)s"]
    params = {"pattern": pattern}

    if speakers:
        where.append("speaker = ANY(%(speakers)s)")
        params["speakers"] = speakers
    if conferences:
        where.append("conference = ANY(%(conferences)s)")
        params["conferences"] = conferences
    if year_min is not None:
        where.append("year >= %(year_min)s")
        params["year_min"] = year_min
    if year_max is not None:
        where.append("year <= %(year_max)s")
        params["year_max"] = year_max

    sql = f"""
        SELECT year, conference, speaker, title, link, paragraph
        FROM talks
        WHERE {" AND ".join(where)}
        ORDER BY year DESC, title, paragraph_num
        LIMIT 2000
    """
    return [dict(r) for r in execute_query(sql, params)]


def get_scripture_volumes() -> list[str]:
    rows = execute_query(
        "SELECT DISTINCT volume FROM scriptures ORDER BY volume"
    )
    return [r["volume"] for r in rows]


def search_scriptures(term: str, volumes: list[str] = None) -> list[dict]:
    """Full-text search on scriptures, optionally filtered by volume."""
    where = ["text ~* %(term)s"]
    params = {"term": term}

    if volumes:
        where.append("volume = ANY(%(volumes)s)")
        params["volumes"] = volumes

    sql = f"""
        SELECT verse_ref, book, volume, text
        FROM scriptures
        WHERE {" AND ".join(where)}
        ORDER BY book_id, chapter, verse
        LIMIT 2000
    """
    return [dict(r) for r in execute_query(sql, params)]


def get_scripture_frequency(term: str, volumes: list[str],
                            normalize: bool = False) -> list[dict]:
    """Count occurrences of a term per book, optionally normalized per 1000 words."""
    if normalize:
        sql = """
            SELECT book, book_id,
                   (COUNT(*)::float / MAX(book_word_count)) * 1000 AS count
            FROM scriptures
            WHERE text ~* %(term)s AND volume = ANY(%(volumes)s)
            GROUP BY book, book_id
            ORDER BY book_id
        """
    else:
        sql = """
            SELECT book, book_id, COUNT(*) AS count
            FROM scriptures
            WHERE text ~* %(term)s AND volume = ANY(%(volumes)s)
            GROUP BY book, book_id
            ORDER BY book_id
        """
    return [dict(r) for r in execute_query(sql, {"term": term, "volumes": volumes})]


def get_similar_talks(embedding: list[float], limit: int = 5) -> list[dict]:
    """Vector similarity search for RAG chat context."""
    sql = """
        SELECT speaker, title, year, conference, link, paragraph
        FROM talks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(emb)s::vector
        LIMIT %(limit)s
    """
    return [dict(r) for r in execute_query(sql, {"emb": str(embedding), "limit": limit})]


def get_similar_scriptures(embedding: list[float], limit: int = 10) -> list[dict]:
    """Vector similarity search for RAG chat context."""
    sql = """
        SELECT verse_ref, volume, book, text
        FROM scriptures
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(emb)s::vector
        LIMIT %(limit)s
    """
    return [dict(r) for r in execute_query(sql, {"emb": str(embedding), "limit": limit})]


def get_existing_conferences() -> set[tuple[int, int]]:
    """Returns set of (year, month) tuples for conferences already in the DB."""
    rows = execute_query("SELECT DISTINCT year, month FROM talks")
    return {(r["year"], r["month"]) for r in rows}


def get_missing_conferences() -> list[dict]:
    """Compare all possible conferences against what's in the DB."""
    import datetime
    current_year = datetime.date.today().year
    existing = get_existing_conferences()

    missing = []
    for year in range(1971, current_year + 1):
        for month in [4, 10]:
            if (year, month) not in existing:
                name = f"{'April' if month == 4 else 'October'} {year}"
                missing.append({"year": year, "month": month, "name": name})
    return missing
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_queries.py -v
```
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add db/queries.py tests/test_queries.py
git commit -m "feat: add database query layer with FTS, regex, and vector search"
```

---

## Task 6: Text Analysis Service

**Files:**
- Create: `services/text_analysis.py`
- Create: `tests/test_text_analysis.py`

- [ ] **Step 1: Write failing tests in tests/test_text_analysis.py**

```python
import pytest
from services.text_analysis import (
    tokenize_and_remove_stopwords,
    generate_ngrams,
    get_window_words,
    SCRIPTURE_STOPWORDS,
)


def test_tokenize_removes_punctuation():
    tokens = tokenize_and_remove_stopwords("And it came to pass, behold!")
    assert "," not in tokens
    assert "!" not in tokens


def test_tokenize_removes_stopwords():
    tokens = tokenize_and_remove_stopwords(
        "the Lord said unto them", SCRIPTURE_STOPWORDS
    )
    assert "the" not in tokens
    assert "unto" not in tokens
    assert "Lord" in tokens or "lord" in tokens


def test_generate_ngrams_bigrams():
    tokens = ["faith", "hope", "charity", "love"]
    ngrams = generate_ngrams(tokens, ns=[2])
    assert "faith hope" in ngrams
    assert "hope charity" in ngrams
    assert "charity love" in ngrams
    assert len(ngrams) == 3


def test_generate_ngrams_trigrams():
    tokens = ["faith", "hope", "charity", "love"]
    ngrams = generate_ngrams(tokens, ns=[3])
    assert "faith hope charity" in ngrams
    assert len(ngrams) == 2


def test_generate_ngrams_mixed():
    tokens = ["faith", "hope", "charity"]
    ngrams = generate_ngrams(tokens, ns=[2, 3])
    assert "faith hope" in ngrams
    assert "faith hope charity" in ngrams


def test_get_window_words_both():
    text = "I know that faith in Jesus Christ is essential"
    words = get_window_words(text, "Jesus", window=2, direction="Both")
    assert "faith" in words or "in" in words
    assert "Christ" in words or "is" in words


def test_get_window_words_before():
    text = "I know that faith in Jesus Christ is essential"
    words = get_window_words(text, "Jesus", window=2, direction="Before")
    assert "Christ" not in words


def test_get_window_words_after():
    text = "I know that faith in Jesus Christ is essential"
    words = get_window_words(text, "Jesus", window=2, direction="After")
    assert "faith" not in words
    assert "in" not in words
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_text_analysis.py -v
```
Expected: All fail with ImportError.

- [ ] **Step 3: Write services/text_analysis.py**

```python
"""Text analysis utilities: tokenization, ngrams, windowing.

Replaces quanteda's tokens(), tokens_ngrams(), and tokens_select() from the R app.
"""
import re
from collections import Counter

ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can",
    "could", "did", "do", "does", "doing", "down", "during", "each", "few",
    "for", "from", "further", "get", "got", "had", "has", "have", "having",
    "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "let",
    "like", "ll", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours",
    "ourselves", "out", "over", "own", "re", "s", "same", "she", "should",
    "so", "some", "such", "t", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "ve", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "would", "you", "your", "yours", "yourself",
}

SCRIPTURE_STOPWORDS = ENGLISH_STOPWORDS | {
    "pass", "came", "yea", "ye", "behold", "shall", "unto", "even",
    "according", "thou", "us", "may", "said", "hast", "can", "upon",
    "hath", "men", "brethren", "therefore", "say", "might", "things",
    "also", "thy", "wherefore", "many", "thee", "thus", "one", "thing", "o",
}


def tokenize_and_remove_stopwords(
    text: str, stopwords: set[str] = None
) -> list[str]:
    """Split text into lowercase words, remove punctuation and stopwords."""
    if stopwords is None:
        stopwords = ENGLISH_STOPWORDS
    words = re.findall(r"[a-zA-Z'-]+", text.lower())
    return [w for w in words if w not in stopwords and len(w) > 1]


def generate_ngrams(tokens: list[str], ns: list[int] = None) -> list[str]:
    """Generate n-grams from a list of tokens."""
    if ns is None:
        ns = [2, 3]
    ngrams = []
    for n in ns:
        for i in range(len(tokens) - n + 1):
            ngrams.append(" ".join(tokens[i : i + n]))
    return ngrams


def get_window_words(
    text: str, focal_word: str, window: int = 3, direction: str = "Both"
) -> list[str]:
    """Extract words within a window around the focal word."""
    words = re.findall(r"[a-zA-Z'-]+", text.lower())
    focal_lower = focal_word.lower()
    result = []

    for i, w in enumerate(words):
        if re.search(focal_lower, w):
            if direction in ("Both", "Before"):
                start = max(0, i - window)
                result.extend(words[start:i])
            if direction in ("Both", "After"):
                end = min(len(words), i + window + 1)
                result.extend(words[i + 1 : end])

    return result


def top_ngrams_from_texts(
    texts: list[str], ns: list[int] = None, top_n: int = 25,
    stopwords: set[str] = None
) -> list[dict]:
    """Aggregate top n-grams across multiple texts."""
    if ns is None:
        ns = [2, 3]
    if stopwords is None:
        stopwords = SCRIPTURE_STOPWORDS

    counter = Counter()
    for text in texts:
        tokens = tokenize_and_remove_stopwords(text, stopwords)
        ngrams = generate_ngrams(tokens, ns)
        counter.update(ngrams)

    return [
        {"phrase": phrase, "count": count}
        for phrase, count in counter.most_common(top_n)
    ]


def top_window_words_from_texts(
    texts: list[str], focal_word: str, window: int = 3,
    direction: str = "Both", top_n: int = 25,
    stopwords: set[str] = None
) -> list[dict]:
    """Aggregate top words within window across multiple texts."""
    if stopwords is None:
        stopwords = SCRIPTURE_STOPWORDS

    counter = Counter()
    focal_lower = focal_word.lower()

    for text in texts:
        words = get_window_words(text, focal_word, window, direction)
        filtered = [w for w in words if w not in stopwords and w != focal_lower and len(w) > 1]
        counter.update(filtered)

    return [
        {"phrase": phrase, "count": count}
        for phrase, count in counter.most_common(top_n)
    ]
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_text_analysis.py -v
```
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add services/text_analysis.py tests/test_text_analysis.py
git commit -m "feat: add text analysis service with ngrams and windowing"
```

---

## Task 7: App Shell, Sidebar, and CSS

**Files:**
- Create: `app.py`
- Create: `components/sidebar.py`
- Create: `assets/custom.css`

- [ ] **Step 1: Write components/sidebar.py**

```python
"""Collapsible sidebar matching shinydashboard layout."""
import dash_bootstrap_components as dbc
from dash import html


def create_sidebar():
    return html.Div(
        [
            html.Div(
                html.H4("Gospel Study", className="sidebar-title"),
                className="sidebar-header",
            ),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-home me-2"), "Home"],
                        href="/", active="exact",
                    ),
                    html.Hr(className="sidebar-divider"),
                    html.P("Conference", className="sidebar-section-label"),
                    dbc.NavLink(
                        [html.I(className="fas fa-chart-line me-2"), "Trends"],
                        href="/trends", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-place-of-worship me-2"), "Promises"],
                        href="/promises", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-check-circle me-2"), "Invitations"],
                        href="/invitations", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-question-circle me-2"), "Questions"],
                        href="/questions", active="exact",
                    ),
                    html.Hr(className="sidebar-divider"),
                    html.P("Scriptures", className="sidebar-section-label"),
                    dbc.NavLink(
                        [html.I(className="fas fa-chart-simple me-2"), "Frequency"],
                        href="/scripture-frequency", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-book me-2"), "Words in Context"],
                        href="/scripture-context", active="exact",
                    ),
                    html.Hr(className="sidebar-divider"),
                    dbc.NavLink(
                        [html.I(className="fas fa-comments me-2"), "Chat"],
                        href="/chat", active="exact",
                    ),
                ],
                vertical=True, pills=True,
            ),
        ],
        className="sidebar",
    )
```

- [ ] **Step 2: Write assets/custom.css**

```css
/* Font */
body {
    font-family: Calibri, "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    background-color: #fff;
    margin: 0;
    padding: 0;
}

/* Sidebar */
.sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 220px;
    background-color: #051c2c;
    padding: 0;
    overflow-y: auto;
    z-index: 1000;
    transition: width 0.3s;
}

.sidebar-header {
    background-color: #051c2c;
    padding: 15px 20px;
    border-bottom: 1px solid #0a2e4a;
}

.sidebar-title {
    color: #fff;
    font-size: 18px;
    margin: 0;
}

.sidebar-section-label {
    color: #8aa4af;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 10px 20px 5px;
    margin: 0;
}

.sidebar-divider {
    border-color: #0a2e4a;
    margin: 5px 15px;
}

.sidebar .nav-link {
    color: #8aa4af;
    padding: 8px 20px;
    font-size: 14px;
    border-radius: 0;
}

.sidebar .nav-link:hover {
    color: #fff;
    background-color: #0a2e4a;
}

.sidebar .nav-link.active {
    color: #fff;
    background-color: #0a2e4a;
}

/* Content area */
.content {
    margin-left: 220px;
    padding: 20px 30px;
    min-height: 100vh;
    background-color: #fff;
}

/* Home page */
.home-image {
    width: 500px;
    margin-left: -30px;
    margin-top: -50px;
}

.home-quote {
    font-family: Calibri, sans-serif;
    font-size: 20px;
    padding-left: 30px;
    color: #666;
}

/* Charts */
.js-plotly-plot {
    width: 100% !important;
}

/* Data tables */
.dash-table-container {
    font-family: Calibri, "Segoe UI", Tahoma, sans-serif;
    font-size: 14px;
}

/* Chat */
.chat-message-user {
    font-weight: bold;
    margin-bottom: 10px;
}

.chat-message-assistant {
    margin-bottom: 15px;
    line-height: 1.6;
}

.system-prompt-editor {
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px;
    margin-bottom: 15px;
    background-color: #f8f9fa;
}
```

- [ ] **Step 3: Write app.py**

```python
"""Main Dash application entry point."""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

from components.sidebar import create_sidebar

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    ],
    suppress_callback_exceptions=True,
)

app.layout = html.Div([
    dcc.Location(id="url"),
    create_sidebar(),
    html.Div(
        dash.page_container,
        className="content",
    ),
])

server = app.server

if __name__ == "__main__":
    app.run(debug=True, port=8050)
```

- [ ] **Step 4: Create a minimal home page placeholder to test the shell**

Create `pages/home.py`:

```python
import dash
from dash import html

dash.register_page(__name__, path="/", name="Home")

layout = html.Div([
    html.H2("Gospel Study"),
    html.P("App shell is working."),
])
```

- [ ] **Step 5: Run the dev server and verify the shell**

Run:
```bash
python app.py
```
Open `http://localhost:8050`. Expected: Dark navy sidebar on the left with all menu items. White content area with "Gospel Study / App shell is working." Home link is active/highlighted.

- [ ] **Step 6: Commit**

```bash
git add app.py components/ assets/ pages/home.py
git commit -m "feat: add app shell with sidebar and theme CSS"
```

---

## Task 8: Reusable Filter Component

**Files:**
- Create: `components/filters.py`

- [ ] **Step 1: Write components/filters.py**

```python
"""Reusable conference/speaker/year filter row used by promises, invitations, questions, and trends."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from db.queries import get_speakers, get_conferences
from datetime import date


def create_filter_row(prefix: str, show_year_slider: bool = True):
    """Create a filter row with conference, speaker, and year range controls.

    Args:
        prefix: Unique prefix for component IDs (e.g., 'promises', 'invitations').
        show_year_slider: Whether to show the year range slider.
    """
    conferences = get_conferences()
    speakers = get_speakers()
    current_year = date.today().year

    children = [
        dbc.Col([
            html.Label("Select Conference(s)"),
            dcc.Dropdown(
                id=f"{prefix}-conference-filter",
                options=[{"label": c, "value": c} for c in conferences],
                multi=True, placeholder="All conferences",
            ),
        ], width=3),
        dbc.Col([
            html.Label("Select Speaker(s)"),
            dcc.Dropdown(
                id=f"{prefix}-speaker-filter",
                options=[{"label": s, "value": s} for s in speakers],
                multi=True, placeholder="All speakers",
            ),
        ], width=3),
    ]

    if show_year_slider:
        children.append(
            dbc.Col([
                html.Label("Select Year(s)"),
                dcc.RangeSlider(
                    id=f"{prefix}-year-slider",
                    min=1971, max=current_year,
                    value=[1971, current_year],
                    marks={y: str(y) for y in range(1971, current_year + 1, 10)},
                    tooltip={"placement": "bottom", "always_visible": False},
                ),
            ], width=4)
        )

    return dbc.Row(children, className="mb-3")
```

- [ ] **Step 2: Commit**

```bash
git add components/filters.py
git commit -m "feat: add reusable filter row component"
```

---

## Task 9: Home Page

**Files:**
- Modify: `pages/home.py`

- [ ] **Step 1: Write the full pages/home.py**

```python
import dash
from dash import html, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
from db.queries import get_corpus_stats, get_missing_conferences
from services.scraper import scrape_and_insert_conference

dash.register_page(__name__, path="/", name="Home")


layout = html.Div([
    html.Br(),
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div(
                    html.Img(src="/assets/Jesus_color.jpg", className="home-image"),
                    style={"display": "inline-block"},
                ),
                html.Div([
                    html.Hr(style={"borderTop": "1px solid #b1b3b1"}),
                    html.P(
                        '"Therefore, dearly beloved brethren, let us cheerfully do all '
                        'things that lie in our power; and then may we stand still, with '
                        'the utmost assurance, to see the salvation of God, and for his '
                        'arm to be revealed."',
                        className="home-quote",
                    ),
                    html.P("D&C 123:17", className="home-quote"),
                    html.Hr(style={"borderTop": "1px solid #b1b3b1"}),
                ], style={"padding": "100px 0", "marginLeft": "50px", "maxWidth": "400px",
                           "display": "inline-block", "verticalAlign": "top"}),
            ]),
        ], width=8),
    ]),
    html.Br(),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.P("This app contains the standard works of The Church of Jesus Christ "
                   "of Latter-day Saints, and talks from General Conferences, covering"),
            html.Div(id="corpus-stats"),
            html.Br(),
            dbc.Button("Update database", id="update-db-btn", color="secondary",
                       style={"width": "200px"}),
        ], width=5),
    ]),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="update-modal-title")),
        dbc.ModalBody(id="update-modal-body"),
        dbc.ModalFooter([
            dbc.Button("Import", id="import-btn", color="primary",
                       style={"display": "none"}),
            dbc.Button("OK", id="close-modal-btn"),
        ]),
    ], id="update-modal", is_open=False),
    dcc.Store(id="missing-conferences-store"),
])


@callback(
    Output("corpus-stats", "children"),
    Input("url", "pathname"),
)
def load_stats(pathname):
    if pathname != "/":
        return no_update
    stats = get_corpus_stats()
    return html.Ul([
        html.Li(f"{stats['conference_count']:,} General Conferences"),
        html.Li(f"{stats['year_count']:,} Years"),
        html.Li(f"{stats['speaker_count']:,} Speakers"),
        html.Li(f"{stats['talk_count']:,} Talks"),
    ])


@callback(
    Output("update-modal", "is_open"),
    Output("update-modal-title", "children"),
    Output("update-modal-body", "children"),
    Output("import-btn", "style"),
    Output("missing-conferences-store", "data"),
    Input("update-db-btn", "n_clicks"),
    Input("close-modal-btn", "n_clicks"),
    Input("import-btn", "n_clicks"),
    State("update-modal", "is_open"),
    State("missing-conferences-store", "data"),
    prevent_initial_call=True,
)
def handle_update_modal(update_clicks, close_clicks, import_clicks,
                        is_open, missing_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "close-modal-btn":
        return False, "", "", {"display": "none"}, None

    if trigger == "update-db-btn":
        missing = get_missing_conferences()
        if not missing:
            return True, "", "The database is up to date!", {"display": "none"}, None

        items = html.Ul([html.Li(m["name"]) for m in missing])
        body = html.Div([
            html.P("Would you like to load the following conferences?"),
            items,
        ])
        return (True, "Missing conferences found", body,
                {"display": "inline-block"}, missing)

    if trigger == "import-btn" and missing_data:
        try:
            count = 0
            for conf in missing_data:
                added = scrape_and_insert_conference(conf["year"], conf["month"])
                count += added
            body = f"Added {count} talks."
        except Exception as e:
            body = f"Error during import: {str(e)}"
        return True, "Import Complete", body, {"display": "none"}, None

    return no_update, no_update, no_update, no_update, no_update
```

- [ ] **Step 2: Run dev server and verify Home page**

Run:
```bash
python app.py
```
Open `http://localhost:8050`. Expected: Jesus image on the left, D&C quote on the right, corpus stats list, Update database button. Note: the scraper import will fail until Task 12 — that's fine, the page should still render.

- [ ] **Step 3: Commit**

```bash
git add pages/home.py
git commit -m "feat: add home page with stats and update database modal"
```

---

## Task 10: Trends Page

**Files:**
- Create: `pages/trends.py`

- [ ] **Step 1: Write pages/trends.py**

```python
import dash
from dash import html, dcc, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from db.queries import search_talks_fts, search_talks_proximity, get_speakers

dash.register_page(__name__, path="/trends", name="Trends")

BLUES = ["#08306b", "#204479", "#395988", "#526e97", "#6a82a6",
         "#8397b5", "#9cacc3", "#b4c0d2", "#cdd5e1", "#e6eaf0"]

speakers = get_speakers()

layout = html.Div([
    html.Br(),
    html.H2("Trend Search"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.H4("Keyword/phrase search"),
            html.P("Enter words and/or phrases, separated by a semicolon"),
            dcc.Textarea(id="search-input", value="", style={"width": "500px", "height": "75px"}),
            dbc.Row([
                dbc.Col([
                    dbc.RadioItems(
                        id="search-mode", value="Exact",
                        options=[{"label": "Exact", "value": "Exact"},
                                 {"label": "Fuzzy", "value": "Fuzzy"}],
                        inline=True,
                    ),
                    dbc.Button("Search", id="keyword-search-btn", color="secondary",
                               style={"width": "150px"}, className="mt-2"),
                ], width=5),
                dbc.Col([
                    html.P('e.g. when fuzzy searching, "faith" will also return "faithful"',
                           className="text-muted mt-2"),
                ], width=6),
            ]),
        ], width=6, style={"borderRight": "1px solid #ccc"}),
        dbc.Col([
            html.H4("Proximity search"),
            dbc.Row([
                dbc.Col([
                    html.Label("Word 1"),
                    dbc.Input(id="prox-word1", type="text", style={"width": "300px"}),
                    html.Label("Word 2", className="mt-2"),
                    dbc.Input(id="prox-word2", type="text", style={"width": "300px"}),
                    dbc.Button("Search", id="prox-search-btn", color="secondary",
                               style={"width": "150px"}, className="mt-2"),
                ], width=6),
                dbc.Col([
                    html.Label("Word window"),
                    dbc.Input(id="prox-window", type="number", value=5, min=1,
                              style={"width": "300px"}),
                    html.Label("Word order", className="mt-2"),
                    dbc.RadioItems(
                        id="prox-order", value="No order",
                        options=[{"label": "No order", "value": "No order"},
                                 {"label": "Ordered", "value": "Ordered"}],
                        inline=True,
                    ),
                ], width=6),
            ]),
        ], width=6),
    ]),
    html.Br(),
    html.H4("Trends"),
    dcc.Graph(id="trend-chart", figure=go.Figure()),
    html.Br(),
    html.H4("Correlations"),
    html.Div(id="correlation-table"),
    html.Br(),
    html.H4("Sentences"),
    html.Div(id="sentences-table"),
])


def build_trend_chart(results: list[dict], terms: list[str]) -> go.Figure:
    if not results:
        return go.Figure()

    df = pd.DataFrame(results)
    fig = go.Figure()

    for i, term in enumerate(terms):
        term_df = df[df["_term"] == term] if "_term" in df.columns else df
        year_counts = term_df.groupby("year").size().reset_index(name="count")
        fig.add_trace(go.Scatter(
            x=year_counts["year"], y=year_counts["count"],
            mode="lines+markers", name=term,
            line=dict(color=BLUES[i % len(BLUES)]),
        ))

    fig.update_layout(
        xaxis_title="", yaxis_title="",
        template="plotly_white", height=400,
    )
    return fig


def build_sentences_table(results: list[dict]) -> dash_table.DataTable:
    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    display_df = df[["year", "speaker", "title", "paragraph"]].copy()
    display_df.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display_df.to_dict("records"),
        columns=[
            {"name": "Year", "id": "Year"},
            {"name": "Speaker", "id": "Speaker"},
            {"name": "Title", "id": "Title", "presentation": "markdown"},
            {"name": "Sentence", "id": "Sentence"},
        ],
        page_size=5,
        filter_action="native",
        sort_action="native",
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Calibri, sans-serif"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )


@callback(
    Output("trend-chart", "figure"),
    Output("correlation-table", "children"),
    Output("sentences-table", "children"),
    Input("keyword-search-btn", "n_clicks"),
    State("search-input", "value"),
    State("search-mode", "value"),
    prevent_initial_call=True,
)
def do_keyword_search(n_clicks, search_input, mode):
    if not search_input or not search_input.strip():
        return go.Figure(), "", ""

    terms = [t.strip() for t in search_input.split(";") if t.strip()]
    all_results = []

    for term in terms:
        fts_mode = "exact" if mode == "Exact" else "fuzzy"
        results = search_talks_fts(term, mode=fts_mode)
        for r in results:
            r["_term"] = term
        all_results.extend(results)

    if not all_results:
        return go.Figure(), "", html.P("No results found.")

    fig = build_trend_chart(all_results, terms)

    # Correlation matrix
    corr_div = ""
    if len(terms) > 1:
        df = pd.DataFrame(all_results)
        pivot = df.groupby(["year", "_term"]).size().unstack(fill_value=0)
        if len(pivot.columns) > 1:
            corr = np.corrcoef(pivot.values.T)
            corr_df = pd.DataFrame(corr, index=pivot.columns, columns=pivot.columns)
            corr_div = dash_table.DataTable(
                data=corr_df.reset_index().to_dict("records"),
                columns=[{"name": c, "id": c} for c in ["index"] + list(pivot.columns)],
                style_cell={"textAlign": "center", "padding": "5px"},
            )

    table = build_sentences_table(all_results)
    return fig, corr_div, table


@callback(
    Output("trend-chart", "figure", allow_duplicate=True),
    Output("correlation-table", "children", allow_duplicate=True),
    Output("sentences-table", "children", allow_duplicate=True),
    Input("prox-search-btn", "n_clicks"),
    State("prox-word1", "value"),
    State("prox-word2", "value"),
    State("prox-window", "value"),
    State("prox-order", "value"),
    prevent_initial_call=True,
)
def do_proximity_search(n_clicks, word1, word2, window, order):
    if not word1 or not word2:
        return go.Figure(), "", ""

    ordered = order == "Ordered"
    results = search_talks_proximity(word1, word2, window=int(window), ordered=ordered)

    if not results:
        return go.Figure(), "", html.P("No results found.")

    label = f'"{word1}" near "{word2}"'
    for r in results:
        r["_term"] = label

    fig = build_trend_chart(results, [label])
    fig.update_layout(title=label)
    table = build_sentences_table(results)
    return fig, "", table
```

- [ ] **Step 2: Run dev server and test the Trends page**

Run:
```bash
python app.py
```
Navigate to `/trends`. Test keyword search with "faith" (exact and fuzzy), multi-term "faith;hope;charity", and proximity search "faith" near "works" with window 5.

- [ ] **Step 3: Commit**

```bash
git add pages/trends.py
git commit -m "feat: add trends page with keyword and proximity search"
```

---

## Task 11: Promises, Invitations, and Questions Pages

**Files:**
- Create: `pages/promises.py`
- Create: `pages/invitations.py`
- Create: `pages/questions.py`

These three pages share the same pattern: filter row + button + results table.

- [ ] **Step 1: Write pages/promises.py**

```python
import dash
from dash import html, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from components.filters import create_filter_row
from db.queries import search_talks_regex

dash.register_page(__name__, path="/promises", name="Promises")

PROMISE_PHRASES = (
    "I promise you|I promise that|I leave you a promise|I leave with you a promise|"
    "I leave you this promise|I can promise you|I can promise that|if you will"
)

layout = html.Div([
    html.Br(),
    html.H2("Promises"),
    html.Hr(),
    create_filter_row("promises"),
    dbc.Button("Find Promises", id="promises-btn", color="secondary",
               style={"width": "200px"}),
    html.Br(), html.Br(),
    html.Div(id="promises-results"),
])


@callback(
    Output("promises-results", "children"),
    Input("promises-btn", "n_clicks"),
    State("promises-conference-filter", "value"),
    State("promises-speaker-filter", "value"),
    State("promises-year-slider", "value"),
    prevent_initial_call=True,
)
def find_promises(n_clicks, conferences, speakers, year_range):
    results = search_talks_regex(
        PROMISE_PHRASES,
        speakers=speakers or None,
        conferences=conferences or None,
        year_min=year_range[0] if year_range else 1971,
        year_max=year_range[1] if year_range else 2100,
    )

    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    df["title"] = df.apply(
        lambda r: f"[{r['title']}]({r['link']})" if r.get("link") else r["title"],
        axis=1,
    )
    display = df[["year", "speaker", "title", "paragraph"]].copy()
    display.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display.to_dict("records"),
        columns=[
            {"name": "Year", "id": "Year"},
            {"name": "Speaker", "id": "Speaker"},
            {"name": "Title", "id": "Title", "presentation": "markdown"},
            {"name": "Sentence", "id": "Sentence"},
        ],
        page_size=5,
        filter_action="native",
        sort_action="native",
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Calibri, sans-serif"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )
```

- [ ] **Step 2: Write pages/invitations.py**

```python
import dash
from dash import html, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from components.filters import create_filter_row
from db.queries import search_talks_regex

dash.register_page(__name__, path="/invitations", name="Invitations")

INVITATION_PHRASES = (
    "I invite you|I encourage you|I recommend|I plead with you|"
    "I challenge you|I ask you to|I encourage everyone|I urge you"
)

layout = html.Div([
    html.Br(),
    html.H2("Invitations"),
    html.Hr(),
    create_filter_row("invitations"),
    dbc.Button("Find Invitations", id="invitations-btn", color="secondary",
               style={"width": "200px"}),
    html.Br(), html.Br(),
    html.Div(id="invitations-results"),
])


@callback(
    Output("invitations-results", "children"),
    Input("invitations-btn", "n_clicks"),
    State("invitations-conference-filter", "value"),
    State("invitations-speaker-filter", "value"),
    State("invitations-year-slider", "value"),
    prevent_initial_call=True,
)
def find_invitations(n_clicks, conferences, speakers, year_range):
    results = search_talks_regex(
        INVITATION_PHRASES,
        speakers=speakers or None,
        conferences=conferences or None,
        year_min=year_range[0] if year_range else 1971,
        year_max=year_range[1] if year_range else 2100,
    )

    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    df["title"] = df.apply(
        lambda r: f"[{r['title']}]({r['link']})" if r.get("link") else r["title"],
        axis=1,
    )
    display = df[["year", "speaker", "title", "paragraph"]].copy()
    display.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display.to_dict("records"),
        columns=[
            {"name": "Year", "id": "Year"},
            {"name": "Speaker", "id": "Speaker"},
            {"name": "Title", "id": "Title", "presentation": "markdown"},
            {"name": "Sentence", "id": "Sentence"},
        ],
        page_size=5,
        filter_action="native",
        sort_action="native",
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Calibri, sans-serif"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )
```

- [ ] **Step 3: Write pages/questions.py**

```python
import dash
from dash import html, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from components.filters import create_filter_row
from db.queries import search_talks_regex

dash.register_page(__name__, path="/questions", name="Questions")

layout = html.Div([
    html.Br(),
    html.H2("Questions"),
    html.Hr(),
    create_filter_row("questions"),
    dbc.Button("Find Questions", id="questions-btn", color="secondary",
               style={"width": "200px"}),
    html.Br(), html.Br(),
    html.Div(id="questions-results"),
])


@callback(
    Output("questions-results", "children"),
    Input("questions-btn", "n_clicks"),
    State("questions-conference-filter", "value"),
    State("questions-speaker-filter", "value"),
    State("questions-year-slider", "value"),
    prevent_initial_call=True,
)
def find_questions(n_clicks, conferences, speakers, year_range):
    results = search_talks_regex(
        r"\?",
        speakers=speakers or None,
        conferences=conferences or None,
        year_min=year_range[0] if year_range else 1971,
        year_max=year_range[1] if year_range else 2100,
    )

    if not results:
        return html.P("No results found.")

    df = pd.DataFrame(results)
    df["title"] = df.apply(
        lambda r: f"[{r['title']}]({r['link']})" if r.get("link") else r["title"],
        axis=1,
    )
    display = df[["year", "speaker", "title", "paragraph"]].copy()
    display.columns = ["Year", "Speaker", "Title", "Sentence"]

    return dash_table.DataTable(
        data=display.to_dict("records"),
        columns=[
            {"name": "Year", "id": "Year"},
            {"name": "Speaker", "id": "Speaker"},
            {"name": "Title", "id": "Title", "presentation": "markdown"},
            {"name": "Sentence", "id": "Sentence"},
        ],
        page_size=5,
        filter_action="native",
        sort_action="native",
        style_cell={"textAlign": "left", "padding": "8px", "fontFamily": "Calibri, sans-serif"},
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
    )
```

- [ ] **Step 4: Run dev server and test all three pages**

Navigate to `/promises`, `/invitations`, `/questions`. Use filters, click search buttons, verify results show in tables.

- [ ] **Step 5: Commit**

```bash
git add pages/promises.py pages/invitations.py pages/questions.py
git commit -m "feat: add promises, invitations, and questions pages"
```

---

## Task 12: Scripture Frequency Page

**Files:**
- Create: `pages/scripture_frequency.py`

- [ ] **Step 1: Write pages/scripture_frequency.py**

```python
import dash
from dash import html, dcc, callback, Output, Input, State, no_update, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from db.queries import get_scripture_volumes, get_scripture_frequency, search_scriptures

dash.register_page(__name__, path="/scripture-frequency", name="Scripture Frequency")

volumes = get_scripture_volumes()

layout = html.Div([
    html.Br(),
    html.H2("Word Frequencies"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Label("Select Volume"),
            dcc.Dropdown(
                id="freq-volume-picker",
                options=[{"label": v, "value": v} for v in volumes],
                multi=True, placeholder="Select volumes...",
            ),
            html.Br(),
            dbc.RadioItems(
                id="freq-sort", value="Values",
                options=[{"label": "Values", "value": "Values"},
                         {"label": "Book order", "value": "Book order"}],
                inline=True,
            ),
            html.Label("Sort chart by", className="text-muted"),
            html.Br(),
            dbc.RadioItems(
                id="freq-normalize", value="Raw counts",
                options=[{"label": "Raw counts", "value": "Raw counts"},
                         {"label": "Per 1000 words", "value": "Per 1000 words"}],
                inline=True,
            ),
            html.Label("Normalize counts", className="text-muted"),
        ], width=3),
        dbc.Col([
            html.Label("Focal word/phrase"),
            dcc.Textarea(id="freq-search-input", style={"width": "400px", "height": "35px"}),
        ], width=4),
        dbc.Col([
            dbc.Button("Search", id="freq-search-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2, className="offset-2"),
    ]),
    html.Hr(),
    dcc.Graph(id="freq-chart", figure=go.Figure()),
    html.Div(id="freq-verses-table"),
])


@callback(
    Output("freq-chart", "figure"),
    Output("freq-verses-table", "children"),
    Input("freq-search-btn", "n_clicks"),
    State("freq-search-input", "value"),
    State("freq-volume-picker", "value"),
    State("freq-normalize", "value"),
    State("freq-sort", "value"),
    prevent_initial_call=True,
)
def search_scripture_frequency(n_clicks, search_term, selected_volumes, normalize, sort_by):
    if not search_term or not selected_volumes:
        return go.Figure(), ""

    norm = normalize == "Per 1000 words"
    freq = get_scripture_frequency(search_term, volumes=selected_volumes, normalize=norm)

    if not freq:
        return go.Figure(), html.P("No results found.")

    df = pd.DataFrame(freq)

    if sort_by == "Values":
        df = df.sort_values("count", ascending=False)
    else:
        df = df.sort_values("book_id")

    fig = go.Figure(go.Bar(x=df["book"], y=df["count"]))
    fig.update_layout(
        xaxis_title="", yaxis_title="",
        template="plotly_white",
        xaxis={"categoryorder": "array", "categoryarray": df["book"].tolist()},
    )

    verses = search_scriptures(search_term, volumes=selected_volumes)
    if verses:
        vdf = pd.DataFrame(verses)
        table = dash_table.DataTable(
            data=vdf[["verse_ref", "text"]].to_dict("records"),
            columns=[
                {"name": "Reference", "id": "verse_ref"},
                {"name": "Text", "id": "text"},
            ],
            page_size=20,
            filter_action="native",
            sort_action="native",
            style_cell={"textAlign": "left", "padding": "8px",
                         "fontFamily": "Calibri, sans-serif"},
            style_header={"fontWeight": "bold"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
            ],
        )
    else:
        table = ""

    return fig, table
```

- [ ] **Step 2: Test the page**

Navigate to `/scripture-frequency`. Select "Book of Mormon", search "faith", toggle between Raw counts and Per 1000 words, toggle sort.

- [ ] **Step 3: Commit**

```bash
git add pages/scripture_frequency.py
git commit -m "feat: add scripture frequency page with bar chart and verse table"
```

---

## Task 13: Scripture Words in Context Page

**Files:**
- Create: `pages/scripture_context.py`

- [ ] **Step 1: Write pages/scripture_context.py**

```python
import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from db.queries import search_scriptures, get_scripture_volumes
from services.text_analysis import top_ngrams_from_texts, top_window_words_from_texts

dash.register_page(__name__, path="/scripture-context", name="Words in Context")

volumes = get_scripture_volumes()

layout = html.Div([
    html.Br(),
    html.H2("Words in Context"),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.Label("Select Volume"),
            dcc.Dropdown(
                id="ctx-volume-picker",
                options=[{"label": v, "value": v} for v in volumes],
                multi=True, placeholder="Select volumes...",
            ),
            html.Br(),
            html.Label("Window width"),
            dbc.Input(id="ctx-window", type="number", value=3, min=1, step=1),
            html.Br(),
            html.Label("Window type"),
            dbc.Select(
                id="ctx-direction",
                options=[{"label": d, "value": d} for d in ["Both", "Before", "After"]],
                value="Both",
            ),
        ], width=3),
        dbc.Col([
            html.Label("Focal word/phrase"),
            dcc.Textarea(id="ctx-search-input", style={"width": "400px", "height": "35px"}),
        ], width=4),
        dbc.Col([
            dbc.Button("Search", id="ctx-search-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2, className="offset-2"),
    ]),
    html.Hr(),
    dbc.Row([
        dbc.Col([
            html.P("Top phrases in verse", style={"fontSize": "20px", "fontWeight": "bold"}),
            dcc.Graph(id="ctx-verse-chart", figure=go.Figure(),
                      style={"height": "600px"}),
        ], width=6),
        dbc.Col([
            html.P("Top words in window", style={"fontSize": "20px", "fontWeight": "bold"}),
            dcc.Graph(id="ctx-window-chart", figure=go.Figure(),
                      style={"height": "600px"}),
        ], width=6),
    ]),
])


def make_horizontal_bar(data: list[dict], x_col: str = "count", y_col: str = "phrase") -> go.Figure:
    if not data:
        return go.Figure()
    phrases = [d[y_col] for d in reversed(data)]
    counts = [d[x_col] for d in reversed(data)]
    fig = go.Figure(go.Bar(x=counts, y=phrases, orientation="h"))
    fig.update_layout(
        yaxis_title="", xaxis_title="",
        template="plotly_white",
        margin=dict(l=200),
    )
    return fig


@callback(
    Output("ctx-verse-chart", "figure"),
    Output("ctx-window-chart", "figure"),
    Input("ctx-search-btn", "n_clicks"),
    State("ctx-search-input", "value"),
    State("ctx-volume-picker", "value"),
    State("ctx-window", "value"),
    State("ctx-direction", "value"),
    prevent_initial_call=True,
)
def search_context(n_clicks, search_term, selected_volumes, window, direction):
    if not search_term or not selected_volumes:
        return go.Figure(), go.Figure()

    verses = search_scriptures(search_term, volumes=selected_volumes)
    if not verses:
        return go.Figure(), go.Figure()

    texts = [v["text"] for v in verses]

    verse_ngrams = top_ngrams_from_texts(texts, ns=[2, 3], top_n=25)
    verse_chart = make_horizontal_bar(verse_ngrams)

    window_words = top_window_words_from_texts(
        texts, focal_word=search_term, window=int(window),
        direction=direction, top_n=25,
    )
    window_chart = make_horizontal_bar(window_words)

    return verse_chart, window_chart
```

- [ ] **Step 2: Test the page**

Navigate to `/scripture-context`. Select "Book of Mormon", search "faith", set window to 3, direction Both. Verify two side-by-side horizontal bar charts appear.

- [ ] **Step 3: Commit**

```bash
git add pages/scripture_context.py
git commit -m "feat: add scripture words-in-context page with ngram analysis"
```

---

## Task 14: Unified Chat Page

**Files:**
- Create: `pages/chat.py`

- [ ] **Step 1: Write pages/chat.py**

```python
import dash
from dash import html, dcc, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc
from db.queries import get_similar_talks, get_similar_scriptures
from services.openai_client import (
    get_embeddings, chat_completion, DEFAULT_SYSTEM_PROMPT,
)

dash.register_page(__name__, path="/chat", name="Chat")

layout = html.Div([
    html.Br(),
    html.H2("Chat"),
    html.Hr(),

    # Collapsible system prompt editor
    dbc.Accordion([
        dbc.AccordionItem([
            dcc.Textarea(
                id="system-prompt-input",
                value=DEFAULT_SYSTEM_PROMPT,
                style={"width": "100%", "height": "100px", "fontFamily": "Calibri, sans-serif"},
            ),
            dbc.Button("Reset to default", id="reset-prompt-btn", color="link", size="sm",
                       className="mt-1"),
        ], title="System Prompt", item_id="sys-prompt"),
    ], start_collapsed=True, className="mb-3"),

    # Chat output
    dbc.Row([
        dbc.Col([
            html.P("Chat", style={"fontSize": "20px", "fontWeight": "bold"}),
        ], width=10),
        dbc.Col([
            dbc.Button("Clear", id="clear-chat-btn", color="secondary",
                       style={"width": "100%"}),
        ], width=2),
    ]),
    html.Div(id="chat-output", style={"minHeight": "200px", "marginBottom": "20px"}),

    # Chat input
    dbc.Row([
        dbc.Col([
            dbc.Input(id="chat-input", type="text", placeholder="Enter prompt here",
                      style={"width": "100%"}),
        ], width=10),
        dbc.Col([
            dbc.Button(
                html.I(className="fas fa-comments"),
                id="chat-submit-btn", color="secondary", style={"width": "100%"},
            ),
        ], width=2),
    ]),

    # Stores for conversation state
    dcc.Store(id="chat-history-store", data=[]),
])


def format_context(talks: list[dict], scriptures: list[dict]) -> str:
    parts = []
    for t in talks:
        parts.append(
            f"[{t['speaker']}, {t['conference']} - \"{t['title']}\"]\n{t['paragraph']}"
        )
    for s in scriptures:
        parts.append(f"[{s['verse_ref']}]\n{s['text']}")
    return "\n\n---\n\n".join(parts)


def render_chat_history(history: list[dict]) -> list:
    children = []
    for msg in history:
        if msg["role"] == "user":
            children.append(
                html.Div(html.Strong(msg["content"]), className="chat-message-user")
            )
        else:
            children.append(
                html.Div(
                    dcc.Markdown(msg["content"]),
                    className="chat-message-assistant",
                )
            )
    if not children:
        children.append(html.P("Ask a question about the gospel.", className="text-muted"))
    return children


@callback(
    Output("system-prompt-input", "value"),
    Input("reset-prompt-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_system_prompt(n_clicks):
    return DEFAULT_SYSTEM_PROMPT


@callback(
    Output("chat-output", "children"),
    Output("chat-history-store", "data"),
    Output("chat-input", "value"),
    Input("chat-submit-btn", "n_clicks"),
    Input("clear-chat-btn", "n_clicks"),
    State("chat-input", "value"),
    State("system-prompt-input", "value"),
    State("chat-history-store", "data"),
    prevent_initial_call=True,
)
def handle_chat(submit_clicks, clear_clicks, user_input, system_prompt, history):
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "clear-chat-btn":
        return render_chat_history([]), [], ""

    if trigger == "chat-submit-btn":
        if not user_input or not user_input.strip():
            return no_update, no_update, no_update

        # Get embeddings for the question
        query_embedding = get_embeddings([user_input])[0]

        # RAG: find similar content
        similar_talks = get_similar_talks(query_embedding, limit=5)
        similar_scriptures = get_similar_scriptures(query_embedding, limit=10)

        # Build context
        context = format_context(similar_talks, similar_scriptures)
        augmented_prompt = (
            f"{system_prompt}\n\n"
            f"Use the following sources to inform your answer. "
            f"Cite the speaker and year for conference talks, and book/chapter/verse for scriptures.\n\n"
            f"{context}"
        )

        # Build message list from history
        messages = list(history) + [{"role": "user", "content": user_input}]

        # Get response (non-streaming for simplicity in Dash)
        response = chat_completion(messages, system_prompt=augmented_prompt)

        # Update history
        new_history = list(history)
        new_history.append({"role": "user", "content": user_input})
        new_history.append({"role": "assistant", "content": response})

        return render_chat_history(new_history), new_history, ""

    return no_update, no_update, no_update
```

- [ ] **Step 2: Test the chat page**

Navigate to `/chat`. Expand system prompt, verify it shows the default. Type "What has President Nelson taught about faith?" and submit. Verify a response appears with citations. Click Clear to reset.

- [ ] **Step 3: Commit**

```bash
git add pages/chat.py
git commit -m "feat: add unified RAG chat page with editable system prompt"
```

---

## Task 15: Conference Scraper Service

**Files:**
- Create: `services/scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: Write tests/test_scraper.py**

```python
import pytest
from services.scraper import clean_speaker, clean_title, is_excluded_title


def test_clean_speaker_removes_prefix():
    assert clean_speaker("By Elder Jeffrey R. Holland") == "Jeffrey R. Holland"
    assert clean_speaker("President Russell M. Nelson") == "Russell M. Nelson"
    assert clean_speaker("Bishop W. Christopher Waddell") == "W. Christopher Waddell"


def test_clean_speaker_trims():
    assert clean_speaker("  Russell M. Nelson  ") == "Russell M. Nelson"


def test_clean_title_removes_unicode():
    assert "﻿" not in clean_title("﻿Faith in Every Footstep")


def test_is_excluded_title():
    assert is_excluded_title("Sustaining of Church Officers")
    assert is_excluded_title("Church Auditing Department Report, 2023")
    assert is_excluded_title("Statistical Report, 2023")
    assert not is_excluded_title("Faith in Every Footstep")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/test_scraper.py -v
```

- [ ] **Step 3: Write services/scraper.py**

```python
"""Conference talk scraper. Ports logic from R's scrape new talks.R."""
import re
import time
import httpx
from bs4 import BeautifulSoup
from db.connection import get_connection
from services.openai_client import get_embeddings


EXCLUDED_PATTERNS = [
    "Sustaining of Church Officers",
    "Sustaining of General Authorities",
    "Church Audit Committee Report",
    "Church Auditing Department Report",
    "Statistical Report",
]

BASE_URL = "https://www.churchofjesuschrist.org"


def clean_speaker(speaker: str) -> str:
    if not speaker:
        return ""
    speaker = re.sub(r"^(By |Elder |President |Bishop |Presented by )", "", speaker)
    return speaker.strip()


def clean_title(title: str) -> str:
    if not title:
        return ""
    title = title.replace("﻿", "").replace("<>", "")
    title = re.sub(r'""', '"', title)
    return title.strip()


def is_excluded_title(title: str) -> bool:
    return any(pat in title for pat in EXCLUDED_PATTERNS)


def split_into_paragraphs(text: str, min_words: int = 30, max_words: int = 500) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    paragraphs = []
    current = []
    word_count = 0

    for sentence in sentences:
        s_words = len(sentence.split())
        if word_count + s_words > max_words and current:
            paragraphs.append(" ".join(current))
            current = [sentence]
            word_count = s_words
        else:
            current.append(sentence)
            word_count += s_words

    if current:
        last = " ".join(current)
        if paragraphs and word_count < min_words:
            paragraphs[-1] += " " + last
        else:
            paragraphs.append(last)

    return paragraphs


def fetch_with_retry(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
        except httpx.HTTPError:
            pass
        time.sleep(2)
    return None


def scrape_conference_links(year: int, month: int) -> list[str]:
    month_str = f"{month:02d}"
    url = f"{BASE_URL}/study/general-conference/{year}/{month_str}?lang=eng"
    html_text = fetch_with_retry(url)
    if not html_text:
        return []

    soup = BeautifulSoup(html_text, "html.parser")
    link_elements = soup.select('[class*="item-"]')
    if not link_elements:
        link_elements = soup.select('#main .doc-map a')

    links = []
    for el in link_elements:
        href = el.get("href")
        if href and "/study/general-conference/" in href:
            full = href if href.startswith("http") else BASE_URL + href
            links.append(full)

    return list(dict.fromkeys(links))


def scrape_talk(url: str) -> dict | None:
    html_text = fetch_with_retry(url)
    if not html_text:
        return None

    soup = BeautifulSoup(html_text, "html.parser")

    title_el = soup.select_one("h1")
    title = clean_title(title_el.get_text() if title_el else "")
    if not title or is_excluded_title(title):
        return None

    speaker_el = soup.select_one('[class="author-name"]') or soup.select_one("#p1")
    speaker = clean_speaker(speaker_el.get_text() if speaker_el else "")

    role_el = soup.select_one('[class="author-role"]')
    speaker_role = role_el.get_text().strip() if role_el else None
    if speaker_role:
        speaker_role = re.sub(r"^Of the ", "", speaker_role)

    body_el = soup.select_one("#content article div div")
    if not body_el:
        return None

    texts = []
    for node in body_el.find_all(string=True):
        text = node.strip()
        if text:
            texts.append(text)
    full_text = " ".join(texts)
    full_text = re.sub(r"\s+", " ", full_text).strip()

    if not full_text or not speaker:
        return None

    return {
        "title": title,
        "speaker": speaker,
        "speaker_role": speaker_role,
        "link": url,
        "text": full_text,
    }


def scrape_and_insert_conference(year: int, month: int) -> int:
    month_name = "April" if month == 4 else "October"
    conference = f"{month_name} {year}"

    links = scrape_conference_links(year, month)
    if not links:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    inserted = 0

    for link in links:
        talk = scrape_talk(link)
        if not talk:
            continue

        paragraphs = split_into_paragraphs(talk["text"])

        # Generate embeddings for paragraphs
        embeddings = get_embeddings([p[:8000] for p in paragraphs])

        for i, (para, emb) in enumerate(zip(paragraphs, embeddings), start=1):
            cur.execute("""
                INSERT INTO talks (conference, year, month, session, speaker,
                                   speaker_role, title, link, paragraph_num,
                                   paragraph, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                conference, year, month, None, talk["speaker"],
                talk["speaker_role"], talk["title"], talk["link"],
                i, para, emb,
            ))
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    return inserted
```

- [ ] **Step 4: Run tests**

Run:
```bash
python -m pytest tests/test_scraper.py -v
```
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add services/scraper.py tests/test_scraper.py
git commit -m "feat: add conference talk scraper with BeautifulSoup"
```

---

## Task 16: Final Integration & Vercel Deployment

**Files:**
- Modify: `app.py` (verify all pages are discovered)
- Verify: `vercel.json`

- [ ] **Step 1: Run all tests**

Run:
```bash
python -m pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 2: Run the full app locally and test every page**

Run:
```bash
python app.py
```

Test checklist:
1. **Home** (`/`): Image, quote, stats load. "Update database" button opens modal.
2. **Trends** (`/trends`): Keyword search "faith" returns chart + table. Proximity search "faith" near "works" works. Fuzzy mode works. Multi-term "faith;hope" shows correlation matrix.
3. **Promises** (`/promises`): Unfiltered search returns results. Filter by speaker works. Year slider works.
4. **Invitations** (`/invitations`): Same checks as Promises.
5. **Questions** (`/questions`): Same checks as Promises.
6. **Scripture Frequency** (`/scripture-frequency`): Select Book of Mormon, search "faith". Bar chart and verse table appear. Toggle normalize and sort.
7. **Words in Context** (`/scripture-context`): Select Book of Mormon, search "faith", window 3. Two horizontal bar charts appear.
8. **Chat** (`/chat`): Ask "What has been taught about prayer?" Response appears with citations. Edit system prompt. Clear chat works.

- [ ] **Step 3: Set environment variables in Vercel**

Go to Vercel dashboard → project settings → Environment Variables. Add:
- `DATABASE_URL` = your Neon connection string
- `OPENAI_API_KEY` = your new rotated key

- [ ] **Step 4: Deploy to Vercel**

Run:
```bash
git add -A
git commit -m "feat: complete gospel study migration to Dash on Vercel"
git push origin main
```

Or deploy via Vercel CLI:
```bash
npx vercel --prod
```

- [ ] **Step 5: Verify production deployment**

Open the Vercel URL. Run the same test checklist from Step 2 against the production deployment.

- [ ] **Step 6: Rotate the old OpenAI API key**

The key `sk-3kZD5t...` hardcoded in the R app's `global.R` is exposed. Go to `platform.openai.com` → API Keys → revoke that key.

---

## Summary

| Task | What it builds | Dependencies |
|------|----------------|-------------|
| 1 | Project scaffolding | None |
| 2 | DB connection + schema | Task 1 |
| 3 | Data export + seed scripts | Task 2 |
| 4 | Embedding generation | Task 3 |
| 5 | Database query layer | Task 3 |
| 6 | Text analysis service | None |
| 7 | App shell + sidebar + CSS | Task 1 |
| 8 | Reusable filter component | Task 5 |
| 9 | Home page | Tasks 5, 7 |
| 10 | Trends page | Tasks 5, 7 |
| 11 | Promises/Invitations/Questions | Tasks 5, 7, 8 |
| 12 | Scripture frequency page | Tasks 5, 7 |
| 13 | Scripture context page | Tasks 5, 6, 7 |
| 14 | Chat page | Tasks 4, 5, 7 |
| 15 | Scraper service | Tasks 2, 4 |
| 16 | Integration + deployment | All |
