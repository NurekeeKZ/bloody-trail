"""Offline multinomial Naive Bayes trained on the bundled Russian command corpus.

This is text intent classification, not speech recognition or a generative model.
Unknown words and ambiguous predictions are rejected before any game action.
"""
import math
import re
from collections import Counter


def tokenize(text):
    return re.findall(r'[а-яa-z]+', text.lower().replace('ё', 'е'))


class IntentClassifier:
    def __init__(self, corpus):
        self.counts = {label: Counter(token for phrase in phrases for token in tokenize(phrase))
                       for label, phrases in corpus.items()}
        self.vocabulary = set().union(*(set(c) for c in self.counts.values()))

    def predict(self, text):
        tokens = tokenize(text)
        known = [t for t in tokens if t in self.vocabulary]
        if not known or len(known) / max(1, len(tokens)) < 0.5:
            return None
        scores = {}
        for label, counts in self.counts.items():
            denominator = sum(counts.values()) + len(self.vocabulary)
            scores[label] = sum(math.log((counts[t] + 1) / denominator) for t in known)
        ordered = sorted(scores, key=scores.get, reverse=True)
        if scores[ordered[0]] - scores[ordered[1]] < 0.45:
            return None
        return ordered[0]
