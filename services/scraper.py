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
    speaker = re.sub(r"^(By |Presented by )", "", speaker)
    speaker = re.sub(r"^(Elder |President |Bishop |Sister )", "", speaker)
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
