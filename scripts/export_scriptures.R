load("C:/Users/dave2/OneDrive/Desktop/gospel-study-v4/data/scriptures.Rdata")

# Inspect column names
cat("Columns:", paste(names(scriptures), collapse=", "), "\n")
cat("Rows:", nrow(scriptures), "\n")

write.csv(
  scriptures[, c("volume_title", "book_title", "book_id",
                  "chapter_number", "verse_number", "verse_title",
                  "text", "book_word_count")],
  file = "C:/Users/dave2/projects/gospel-study/data/scriptures.csv",
  row.names = FALSE
)

cat("Exported", nrow(scriptures), "verses to data/scriptures.csv\n")
