import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.verification import _split_sentences, _cosine, Timer
import time


def test_split_sentences():
    text = "This is one. This is two! Is this three?"
    sentences = _split_sentences(text)
    assert len(sentences) == 3


def test_cosine_identical_vectors():
    v = [1.0, 2.0, 3.0]
    assert abs(_cosine(v, v) - 1.0) < 1e-6


def test_cosine_orthogonal_vectors():
    assert abs(_cosine([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_timer_measures_elapsed_time():
    with Timer() as t:
        time.sleep(0.05)
    assert t.elapsed >= 0.05
