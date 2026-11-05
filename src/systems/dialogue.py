class DialogueManager:
    def __init__(self, conversations):
        self.conversations = conversations

    def get(self, name, evidence_ids, flags=()):
        node = self.conversations[name]
        return node, [choice for choice in node['choices']
                      if set(choice.get('requires', [])).issubset(evidence_ids)
                      and set(choice.get('requires_flags', [])).issubset(flags)]
