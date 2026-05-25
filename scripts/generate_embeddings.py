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

        try:
            for row_id, emb in zip(ids, embeddings):
                cur.execute(
                    f"UPDATE {table} SET embedding = %s WHERE id = %s",
                    (emb, row_id),
                )
            conn.commit()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = get_connection()
            cur = conn.cursor()
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
