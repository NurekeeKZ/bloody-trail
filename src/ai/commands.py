"""Shared voice/text command resolution; engine-independent allowlist."""
from src.ai.intents import tokenize


class CommandRouter:
    def __init__(self, commands, classifier):
        self.commands, self.classifier = commands, classifier
        self.exact = {' '.join(tokenize(p)): intent for intent, phrases in commands.items() for p in phrases}

    @property
    def phrases(self):
        return list(self.exact)

    def resolve(self, text, voice=False):
        exact = self.exact.get(' '.join(tokenize(text)))
        # Speech is constrained to the allowlist; [unk] is never an action.
        return exact if voice else exact or self.classifier.predict(text)
