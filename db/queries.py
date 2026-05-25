"""All database queries for the Gospel Study app."""
import datetime
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
    sql = """
        SELECT speaker, title, year, conference, link, paragraph
        FROM talks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(emb)s::vector
        LIMIT %(limit)s
    """
    return [dict(r) for r in execute_query(sql, {"emb": str(embedding), "limit": limit})]


def get_similar_scriptures(embedding: list[float], limit: int = 10) -> list[dict]:
    sql = """
        SELECT verse_ref, volume, book, text
        FROM scriptures
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(emb)s::vector
        LIMIT %(limit)s
    """
    return [dict(r) for r in execute_query(sql, {"emb": str(embedding), "limit": limit})]


def get_existing_conferences() -> set[tuple[int, int]]:
    rows = execute_query("SELECT DISTINCT year, month FROM talks")
    return {(r["year"], r["month"]) for r in rows}


def get_missing_conferences() -> list[dict]:
    current_year = datetime.date.today().year
    existing = get_existing_conferences()

    missing = []
    for year in range(1971, current_year + 1):
        for month in [4, 10]:
            if (year, month) not in existing:
                name = f"{'April' if month == 4 else 'October'} {year}"
                missing.append({"year": year, "month": month, "name": name})
    return missing
