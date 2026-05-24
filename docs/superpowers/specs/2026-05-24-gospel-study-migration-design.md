# Gospel Study App Migration: R Shiny to Dash on Vercel

**Date:** 2026-05-24
**Status:** Draft
**Goal:** Migrate the Gospel Study R Shiny app from shinyapps.io to Vercel using Python Dash, Neon Postgres, and OpenAI — preserving identical user experience and design while improving speed and scalability.

---

## 1. Architecture

### Stack

| Layer | Current (R Shiny) | New (Dash) |
|-------|-------------------|------------|
| Framework | Shiny + shinydashboard | Dash + dash-bootstrap-components |
| Language | R | Python |
| Charts | Plotly (R) | Plotly (Python) — identical output |
| Tables | DT (DataTables) | Dash DataTable |
| Text analysis | quanteda (kwic, tokens, dfm) | Postgres FTS (tsvector, tsquery) |
| Embeddings | RcppHNSW + OpenAI text-embedding-3-large | Postgres pgvector + OpenAI text-embedding-3-small |
| Chat | OpenAI GPT-4-turbo via httr2 | OpenAI GPT-4o via openai Python SDK |
| Database | In-memory .Rdata files | Neon Postgres (existing `gospel-study` project) |
| Hosting | shinyapps.io | Vercel (Python serverless) |
| Secrets | Hardcoded in global.R | Environment variables |

### Project Structure

```
gospel-study-r/
├── app.py                        # Main Dash app entry point
├── pages/                        # Multi-page Dash app (one file per tab)
│   ├── home.py
│   ├── trends.py
│   ├── promises.py
│   ├── invitations.py
│   ├── questions.py
│   ├── scripture_frequency.py
│   ├── scripture_context.py
│   └── chat.py                   # Unified chat (conference + scriptures)
├── components/                   # Reusable UI components
│   ├── sidebar.py
│   └── filters.py                # Conference/speaker/year filter row
├── db/
│   ├── connection.py             # Neon Postgres connection
│   └── queries.py                # All SQL queries
├── services/
│   ├── openai_client.py          # OpenAI API wrapper
│   ├── scraper.py                # Conference talk scraper
│   └── search.py                 # Text search helpers
├── scripts/
│   ├── export_scriptures.R       # One-time: export .Rdata to CSV
│   ├── seed_talks.py             # Load talks CSV into Postgres
│   ├── seed_scriptures.py        # Load scriptures CSV into Postgres
│   └── generate_embeddings.py    # Batch embedding generation
├── assets/
│   ├── custom.css                # Dashboard styling (ported from current)
│   ├── Jesus_color.jpg
│   └── Jesus_bnw.jpg
├── requirements.txt
├── vercel.json                   # Vercel deployment config
└── .env.local                    # Local secrets (gitignored)
```

---

## 2. Database Schema

Connect to the existing Neon project `gospel-study`. Drop existing tables and recreate with the new schema.

### Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### `talks` table — one row per paragraph

```sql
CREATE TABLE talks (
  id              SERIAL PRIMARY KEY,
  conference      TEXT NOT NULL,         -- "April 2024", "October 2023"
  year            INT NOT NULL,
  month           INT NOT NULL,          -- 4 or 10
  session         TEXT,                  -- "Saturday Morning", "Sunday Afternoon", etc.
  speaker         TEXT NOT NULL,
  speaker_role    TEXT,
  title           TEXT NOT NULL,
  link            TEXT,                  -- churchofjesuschrist.org URL
  paragraph_num   INT NOT NULL,          -- ordering within the talk
  paragraph       TEXT NOT NULL,         -- individual paragraph text
  fts             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', paragraph)) STORED,
  embedding       VECTOR(1536)           -- per-paragraph for RAG retrieval
);

CREATE INDEX talks_year_idx ON talks (year);
CREATE INDEX talks_month_idx ON talks (month);
CREATE INDEX talks_speaker_idx ON talks (speaker);
CREATE INDEX talks_conference_idx ON talks (conference);
CREATE INDEX talks_fts_idx ON talks USING GIN (fts);
CREATE INDEX talks_embedding_idx ON talks USING hnsw (embedding vector_cosine_ops);
```

### `scriptures` table — one row per verse

```sql
CREATE TABLE scriptures (
  id              SERIAL PRIMARY KEY,
  volume          TEXT NOT NULL,         -- "Book of Mormon", "Doctrine and Covenants", etc.
  book            TEXT NOT NULL,         -- "1 Nephi", "Genesis", etc.
  book_id         INT NOT NULL,          -- canonical sort order
  chapter         INT NOT NULL,
  verse           INT NOT NULL,
  verse_ref       TEXT NOT NULL,         -- "1 Nephi 3:7"
  text            TEXT NOT NULL,
  book_word_count INT NOT NULL,          -- for per-1000 normalization
  fts             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
  embedding       VECTOR(1536)
);

CREATE INDEX scriptures_volume_idx ON scriptures (volume);
CREATE INDEX scriptures_book_idx ON scriptures (book);
CREATE INDEX scriptures_bookid_idx ON scriptures (book_id);
CREATE INDEX scriptures_fts_idx ON scriptures USING GIN (fts);
CREATE INDEX scriptures_embedding_idx ON scriptures USING hnsw (embedding vector_cosine_ops);
```

### Design Decisions

- **Paragraph-level rows for talks**: Better RAG chunks than sentences (more context) or full talks (too diluted). FTS still finds keyword matches within paragraphs.
- **Embeddings per paragraph**: Gives the chat targeted, relevant context for retrieval.
- **`text-embedding-3-small` (1536 dims)**: Half the storage of the current `text-embedding-3-large` (3072 dims), faster vector search, negligible quality difference for this corpus.
- **Generated tsvector columns**: Auto-maintained by Postgres, no manual updates needed.
- **`book_word_count` on every scripture row**: Avoids joins for the normalization toggle.
- **`session` is nullable**: Older conferences (pre-2000) may not have session metadata available.

---

## 3. Feature Mapping

### Home Page

- Jesus image (`Jesus_color.jpg`) + D&C 123:17 quote in same container layout
- Corpus stats: conference count, year count, speaker count, talk count — from `SELECT COUNT(DISTINCT ...)` queries
- "Update database" button (see Section 5)

### Trends (Keyword/Phrase Search)

**Keyword search** — replaces quanteda `kwic()` + `tokens_select()`:
- **Exact mode:** `WHERE fts @@ plainto_tsquery('english', :term)` — adds implicit word boundaries
- **Fuzzy mode:** `WHERE fts @@ to_tsquery('english', :term || ':*')` — prefix matching (e.g., "faith" matches "faithful")
- **Multi-term (semicolon-separated):** Parse terms, run each as a separate FTS query, aggregate counts by year

**Proximity search** — replaces regex lookahead pattern:
- **Ordered:** `WHERE fts @@ to_tsquery('english', :word1 <:window> :word2)`
- **Unordered:** Run both orderings and union the results

**Outputs:**
- **Trend chart:** Plotly line/scatter chart, frequency by year, blue palette (`#08306b` through `#e6eaf0`)
- **Correlation matrix:** `numpy.corrcoef()` on year-count vectors, rendered as a table
- **Sentences table:** Dash DataTable — Year | Speaker | Title (hyperlinked to churchofjesuschrist.org) | Sentence — with column filters, search highlighting, 5 rows per page

### Promises

Filter by conference (multi-select), speaker (multi-select), year range (slider, 1971–current).

```sql
WHERE paragraph ~* 'I promise you|I promise that|I leave you a promise|I leave with you a promise|
  I leave you this promise|I can promise you|I can promise that|if you will'
  AND year BETWEEN :year_min AND :year_max
  [AND conference IN (:conferences)]
  [AND speaker IN (:speakers)]
```

Results in Dash DataTable: Year | Speaker | Title (linked) | Sentence. 5 rows per page.

### Invitations

Same filter pattern as Promises.

```sql
WHERE paragraph ~* 'I invite you|I encourage you|I recommend|I plead with you|
  I challenge you|I ask you to|I encourage everyone|I urge you'
  AND year BETWEEN :year_min AND :year_max
  [AND conference IN (:conferences)]
  [AND speaker IN (:speakers)]
```

Same table output.

### Questions

Same filter pattern. Searches for paragraphs containing question marks.

```sql
WHERE paragraph LIKE '%?%'
  AND year BETWEEN :year_min AND :year_max
  [AND conference IN (:conferences)]
  [AND speaker IN (:speakers)]
```

Same table output.

### Scripture Frequency

- **Volume picker:** Multi-select with "Select All" toggle (replaces shinyWidgets `pickerInput`)
- **Keyword search:** `WHERE text ~* :pattern AND volume IN (:volumes)`
- **Normalize toggle:**
  - Raw counts: `GROUP BY book, book_id → COUNT(*)`
  - Per 1000 words: `(COUNT(*) / book_word_count) * 1000`
- **Sort toggle:** By value (descending) or by `book_id` (canonical order)
- **Plotly bar chart** of occurrences by book
- **Dash DataTable** of matching verses (verse_ref, text), 20 rows per page

### Scripture Words in Context

- **Inputs:** Volume picker, focal word/phrase, window width (numeric), window type (Both/Before/After)
- **Implementation:** Query matching verses, then in Python:
  1. Tokenize verse text, remove stopwords (same custom list: "pass", "came", "yea", "ye", "behold", "shall", "unto", etc.)
  2. Generate 2-3 word ngrams from full verse text → "Top phrases in verse" (top 25)
  3. Extract words within the specified window around the focal word → "Top words in window" (top 25)
- **Output:** Two side-by-side horizontal Plotly bar charts (600px height each)

### Chat (Unified — New)

Consolidates the current conference chat and scripture chat (commented out) into a single sidebar item.

**RAG flow:**
1. User sends a message
2. Embed the question via OpenAI `text-embedding-3-small`
3. Cosine similarity search across both tables:
   - `SELECT paragraph, speaker, title, year FROM talks ORDER BY embedding <=> :query_embedding LIMIT 5`
   - `SELECT text, verse_ref, volume FROM scriptures ORDER BY embedding <=> :query_embedding LIMIT 10`
4. Format retrieved context as structured text with source labels
5. Send to GPT-4o with system prompt + context + conversation history
6. Stream response to the UI

**System prompt:**
- Default: "You are a faithful member of the Church of Jesus Christ of Latter-Day Saints (LDS). You always provide answers in line with LDS beliefs. In all responses, cite references from scriptures and modern Prophets in your answers. Be concise and format as a table when making comparisons."
- **Editable:** Collapsible "System Prompt" section above the chat input. User can edit the text. Edits apply to the next message. "Reset to default" button. Resets on page refresh.

**Chat UI:**
- Message bubbles: user prompts bolded (matching current HTML bold formatting)
- Chat history maintained in session memory (resets on refresh)
- "Clear" button resets conversation history and system prompt
- Text input + submit button (comment icon)

---

## 4. Styling & UI Parity

### Layout

Dash Bootstrap Components with a custom sidebar replicating shinydashboard:
- Collapsible sidebar, starts collapsed on load (matching current `addClass("sidebar-collapse")`)
- White content area (`background-color: #fff`)

### Color Scheme

```css
/* Navbar and sidebar */
--sidebar-bg: #051c2c;              /* Dark navy */
--sidebar-link: #8aa4af;            /* Light blue-gray */
--sidebar-link-hover: #fff;
--content-bg: #fff;                 /* White */

/* Chart palette (10 blues) */
--chart-1: #08306b;
--chart-2: #204479;
--chart-3: #395988;
--chart-4: #526e97;
--chart-5: #6a82a6;
--chart-6: #8397b5;
--chart-7: #9cacc3;
--chart-8: #b4c0d2;
--chart-9: #cdd5e1;
--chart-10: #e6eaf0;
```

### Typography

Font stack: `Calibri, "Segoe UI", Tahoma, Geneva, Verdana, sans-serif`

### Sidebar Menu

| Section | Item | Icon |
|---------|------|------|
| — | Home | `fa-home` |
| Conference | Trends | `fa-chart-line` |
| Conference | Promises | `fa-place-of-worship` |
| Conference | Invitations | `fa-check-circle` |
| Conference | Questions | `fa-question-circle` |
| Scriptures | Frequency | `fa-chart-simple` |
| Scriptures | Words in Context | `fa-book` |
| — | Chat | `fa-comments` |

### Tables

Dash DataTable configured to match DT behavior:
- Column filters on top
- Search highlighting
- 5 rows per page (20 for scripture verses)
- Hyperlinked titles open in new tab
- Row striping

### Images

`Jesus_color.jpg` on home page, 500px width, same positioning.

---

## 5. Data Pipeline

### Initial Seed (One-Time)

1. **Export scriptures:** Run `scripts/export_scriptures.R` to convert `scriptures.Rdata` to `scriptures.csv` (Python can't read Rdata natively)
2. **Drop existing tables** in Neon `gospel-study` project, enable extensions, create new schema
3. **Seed talks:** Parse `talk_df.csv`, split `text` column into paragraphs (split on double-newlines — verify delimiter in actual CSV during implementation), bulk insert via `psycopg2 COPY`
4. **Seed scriptures:** Parse exported `scriptures.csv`, bulk insert
5. **Generate embeddings:** Batch calls to `text-embedding-3-small` (200 items per request), update `embedding` column. Estimated cost: ~$0.10 total.
6. **Build indexes:** Create GIN, HNSW, and B-tree indexes after data load

### In-App "Update Database" Button

**Timeout note:** Vercel serverless functions have a 60s timeout (free tier) or 300s (Pro). Scraping a single conference (~30 talks) + generating embeddings should fit within 300s. If it doesn't, the scraper can be split into two steps: (1) scrape and insert text, (2) generate embeddings in a separate request. Vercel Pro is recommended.

1. User clicks "Update database" on Home page
2. App computes all possible conference year-month combos up to current date
3. Compares against `SELECT DISTINCT year, month FROM talks`
4. **If missing conferences found:** Show modal listing them ("Would you like to load the following conferences?") with Import and Cancel buttons
5. **If none missing:** Show "The database is up to date!" modal
6. On confirm:
   - Scrape talk pages from `churchofjesuschrist.org/study/general-conference/{year}/{month}` using `beautifulsoup4` + `httpx`
   - Extract session info from page metadata
   - Split into paragraphs
   - Generate embeddings for new paragraphs
   - Insert into Postgres
   - 3 retries per page on failure
7. Show completion modal: "Added X talks from [Conference Name]"
8. Home page stats refresh

### Scraper

Port existing R scraper (`scrape new talks.R` / `scrape all talks.R`) to Python:
- Same URL pattern and xpath selectors
- `beautifulsoup4` for HTML parsing (replaces `rvest`)
- `httpx` for HTTP requests (replaces `httr2`)
- Same retry logic (3 attempts per page)
- New: extract session metadata from page structure

---

## 6. Environment & Deployment

### Environment Variables

```
DATABASE_URL=postgresql://...@ep-xxx.us-east-2.aws.neon.tech/gospel-study
OPENAI_API_KEY=sk-...   (new key — current key in global.R must be rotated)
```

Stored in Vercel project settings for production, `.env.local` for local dev (gitignored).

### Vercel Configuration

`vercel.json`:
```json
{
  "builds": [
    { "src": "app.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "app.py" }
  ]
}
```

### Dependencies (`requirements.txt`)

```
dash
dash-bootstrap-components
plotly
psycopg2-binary
openai
httpx
beautifulsoup4
pandas
numpy
python-dotenv
gunicorn
```

### Local Development

```bash
python app.py
# Runs Dash dev server with hot reload on http://localhost:8050
```

### Security

- API keys in environment variables only (not in source code)
- Current hardcoded key (`sk-3kZD5t...` in `global.R`) must be rotated immediately
- `.env.local` in `.gitignore`

---

## 7. What Changes vs. What Stays the Same

### Changes (Backend Only)

- R → Python
- In-memory .Rdata → Neon Postgres
- quanteda text analysis → Postgres FTS
- RcppHNSW → pgvector HNSW
- GPT-4-turbo → GPT-4o
- text-embedding-3-large → text-embedding-3-small
- Two separate chat tabs → one unified chat tab
- shinyapps.io → Vercel
- Hardcoded API key → environment variable

### Stays the Same

- Visual design: layout, colors, fonts, images
- Sidebar structure (Conference/Scriptures sections with sub-items)
- All 7 original feature tabs (Trends, Promises, Invitations, Questions, Scripture Frequency, Scripture Words in Context, Chat)
- Plotly charts (same library, same palette, same chart types)
- DataTable behavior (filters, pagination, search, linked titles)
- Chat system prompt content
- Conference scraper logic
- Home page layout and corpus stats
- "Update database" flow with confirmation modals

### New Features

- Editable system prompt in chat
- Unified chat searching both conference talks and scriptures
- Chat streaming responses (current app waits for full response)
