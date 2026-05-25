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
