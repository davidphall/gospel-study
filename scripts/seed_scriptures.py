"""Load scriptures.csv into the scriptures table."""
import csv
from db.connection import get_connection


INSERT_SQL = """
    INSERT INTO scriptures (volume, book, book_id, chapter, verse,
                            verse_ref, text, book_word_count)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def main():
    csv_path = "C:/Users/dave2/projects/gospel-study/data/scriptures.csv"
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
