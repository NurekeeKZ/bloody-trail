"""Conversational N.U.R.S. on a local Ollama model. Never imports Pygame; never mutates GameState.

The model sees only facts the player has already uncovered. Its reply is checked in code:
out-of-world words, guarded plot terms absent from those facts and invented codes are replaced
by an in-character line, so a small model can neither break immersion nor spoil the case.
"""
import json
import os
import re
import threading
import urllib.request

OLLAMA_URL = os.environ.get('BLOODYTRAIL_OLLAMA_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.environ.get('BLOODYTRAIL_OLLAMA_MODEL', 'qwen2.5:3b')
HISTORY_TURNS = 6
REPLY_LIMIT = 280
JOURNAL_LIMIT = 6
# Chase QTE entries are technical step names, not facts N.U.R.S. could retell.
TECHNICAL_JOURNAL = ('Пройдено:', 'Ошибка:')
FOREIGN_SCRIPT = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]')
NUMBER = re.compile(r'(?<!\d)\d{3,}(?!\d)')


def normalize(text):
    return str(text).lower().replace('ё', 'е')


def term_pattern(term):
    return re.compile(r'(?<![а-яa-z])' + re.escape(term))


class OllamaClient:
    """Minimal blocking client for the local Ollama chat API; callers run it off the UI thread."""

    def __init__(self, url=OLLAMA_URL, model=OLLAMA_MODEL, timeout=25):
        self.url, self.model, self.timeout = url.rstrip('/'), model, timeout

    def chat(self, messages):
        """Send the dialogue and return the raw reply text. Raises OSError/ValueError on failure."""
        body = json.dumps({'model': self.model, 'messages': messages, 'stream': False, 'keep_alive': '15m',
                           'options': {'temperature': 0.4, 'num_predict': 160, 'num_ctx': 4096}},
                          ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self.url + '/api/chat', data=body,
                                         headers={'Content-Type': 'application/json; charset=utf-8'})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8'))['message']['content']


class NursRequest:
    """One question answered in the background; the scene polls `done` instead of blocking a frame.

    status: 'pending' → 'answer' (filtered model reply), 'blocked' (reply replaced by an
    in-character line) or 'offline' (model unavailable, caller falls back to commands).
    """

    def __init__(self, question):
        self.question = question
        self.reply = ''
        self.status = 'pending'
        self.done = False
        self.thread = None


class NursBrain:
    """Builds the plot-safe context, asks the model and keeps a short in-memory dialogue history.

    History lives only for the current GameState: it is not saved and resets on new game or load.
    """

    def __init__(self, state, catalog, rules, worlds, chapters, puzzles, persona, client=None):
        self.state, self.catalog, self.rules, self.worlds = state, catalog, rules, worlds
        self.chapters, self.puzzles, self.persona = chapters, puzzles, persona
        self.client = client or OllamaClient()
        self.history = []
        self.meta = [re.compile(pattern) for pattern in persona['meta_patterns']]
        self.guarded = [term_pattern(normalize(term)) for term in persona['guarded_terms']]
        self.fallback_index = 0

    def facts(self):
        """Everything N.U.R.S. may know right now, derived from the save only."""
        s = self.state
        chapter = self.chapters.get(str(s.current_day), {}).get('title')
        now = [*self.persona['world_facts'],
               f'Сейчас день {s.current_day} из 3' + (f', этап «{chapter}»' if chapter else '') +
               f'. До передачи дела комиссии осталось {s.time_remaining} ч.',
               'Место: ' + self.worlds[s.location]['title'] + '.',
               'Текущая задача Никиты: ' + s.narrative['objective'].rstrip('.') + '.']
        evidence = []
        for eid in s.evidence_ids:
            item = self.catalog[eid]
            line = f'{item["title"]} ({item["source"]}): {item["text"]}'
            if item.get('nurs'):
                line += ' Ваше замечание: ' + item['nurs']
            if s.evidence_records.get(eid, {}).get('verified'):
                line += ' Связь проверена.'
            evidence.append(line)
        confirmed = [r['text'] for r in self.rules if r['id'] in s.flags]
        open_questions = [r['question'] + ' Материалы: ' + ', '.join(self.catalog[e]['title'] for e in r['requires']) + '.'
                          for r in self.rules
                          if r['id'] not in s.flags and set(r['requires']).issubset(s.evidence_ids)]
        journal = [entry for entry in s.narrative['journal'] if not entry.startswith(TECHNICAL_JOURNAL)][-JOURNAL_LIMIT:]
        hints = [p['title'] + ': ' + ' '.join(p['hints'][:level])
                 for key, level in s.discoveries['hints'].items()
                 if (p := self.puzzles.get(key)) and key not in s.discoveries['solved'] and level > 0]
        solved = [self.puzzles[key]['title'] + ': ' + self.puzzles[key]['success']
                  for key in s.discoveries['solved'] if key in self.puzzles]
        sections = [('Известно сейчас', now), ('Найденные материалы', evidence),
                    ('Подтверждённые выводы на доске', confirmed),
                    ('Можно проверить на доске — пока это только гипотезы', open_questions),
                    ('Журнал расследования', journal), ('Подсказки, которые вы уже давали', hints),
                    ('Открытые замки и решённые задачи', solved)]
        return '\n\n'.join(title + ':\n' + '\n'.join('- ' + line for line in (lines or ['пока нет']))
                           for title, lines in sections)

    def messages(self, question, facts):
        system = '\n'.join(self.persona['persona']) + '\n\n' + facts
        # Plot-free sample exchanges set tone and form better than rules alone for a small model.
        return [{'role': 'system', 'content': system}, *self.persona.get('examples', []), *self.history,
                {'role': 'user', 'content': question}]

    def ask(self, question):
        """Start answering in a daemon thread; the snapshot of facts is taken here, on the caller's thread."""
        request = NursRequest(question)
        facts = self.facts()
        request.thread = threading.Thread(target=self._answer, args=(request, self.messages(question, facts), normalize(facts)),
                                          daemon=True)
        request.thread.start()
        return request

    def _answer(self, request, messages, known):
        try:
            raw = self.client.chat(messages)
        except (OSError, ValueError, KeyError, TypeError):
            request.status = 'offline'
        else:
            reply = self.clean(raw, known)
            request.status, request.reply = ('answer', reply) if reply else ('blocked', self.fallback())
        request.done = True

    def clean(self, raw, known):
        """Return a speakable in-world reply, or '' when the model broke a rule.

        known: normalized facts given to the model; guarded terms and numbers must come from them.
        """
        text = re.sub(r'[*_#`>]+', '', str(raw)).strip()
        text = re.sub(r'^(n\.?u\.?r\.?s\.?|нурс)\s*[:—-]\s*', '', text, flags=re.IGNORECASE)
        text = ' '.join(text.split())
        low = normalize(text)
        if not text or FOREIGN_SCRIPT.search(text):
            return ''
        if len(re.findall(r'[a-z]', low)) > 0.3 * len(re.findall(r'[а-я]', low)):
            return ''
        if any(pattern.search(low) for pattern in self.meta):
            return ''
        if any(pattern.search(low) and not pattern.search(known) for pattern in self.guarded):
            return ''
        if not set(NUMBER.findall(low)).issubset(NUMBER.findall(known)):
            return ''
        return self.shorten(text)

    @staticmethod
    def shorten(text):
        if len(text) <= REPLY_LIMIT:
            return text
        cut = text[:REPLY_LIMIT]
        end = max(cut.rfind(mark) for mark in '.!?…')
        return cut[:end + 1] if end > 40 else cut.rstrip() + '…'

    def fallback(self):
        replies = self.persona['fallback_replies']
        reply = replies[self.fallback_index % len(replies)]
        self.fallback_index += 1
        return reply

    def remember(self, request):
        """Keep only accepted answers so a blocked reply never becomes context for the next one."""
        if request.status != 'answer':
            return
        self.history += [{'role': 'user', 'content': request.question}, {'role': 'assistant', 'content': request.reply}]
        del self.history[:-HISTORY_TURNS * 2]
