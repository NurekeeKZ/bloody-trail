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

    def match(self, text):
        """Allowlist phrase, alone or inside a short utterance; free questions return None."""
        tokens = tokenize(text)
        joined = ' ' + ' '.join(tokens) + ' '
        # Up to two extra words ("Нурс, покажи улики, пожалуйста"); longer speech is a question.
        for phrase in sorted(self.exact, key=len, reverse=True):
            if len(tokens) <= len(phrase.split()) + 2 and ' ' + phrase + ' ' in joined:
                return self.exact[phrase]
        return None
