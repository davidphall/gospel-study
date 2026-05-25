"""Text analysis utilities: tokenization, ngrams, windowing."""
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
    if stopwords is None:
        stopwords = ENGLISH_STOPWORDS
    words = re.findall(r"[a-zA-Z'-]+", text.lower())
    return [w for w in words if w not in stopwords and len(w) > 1]


def generate_ngrams(tokens: list[str], ns: list[int] = None) -> list[str]:
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
