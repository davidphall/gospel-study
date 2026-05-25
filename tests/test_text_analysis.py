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
