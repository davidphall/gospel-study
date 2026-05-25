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
