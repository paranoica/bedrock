---
name: ask
description: Use first for any question about this project's code or decisions — "где у нас", "как работает", "быстро скажи", "how does X work". Answers from notes and the code map with source and confidence.
---

# Answers about the project

Two modes (D058). The owner's word picks it: «быстро», «срочно» mean fast; anything else is
thorough.

## Triggers
- RU: «как у нас работает», «где это», «быстро скажи», «почему так сделано»
- EN: "how does X work", "where is", "quick question", "why is it like this"

## 0. Seen before?
Run `bedrock question similar "<question>"`. A hit is reused only after it is re-checked
against the code. A question asked twice becomes a FAQ card (step 4).
Then `bedrock question log "<question>"` and keep the id it prints.
Done when: the question has an id.

## 1. Fast mode (20 to 30 seconds)
Read only prepared material:
1. the project's `summary.md` and `entry.md` (the canon table says which note holds what);
2. the module note for the area, and `faq/` cards;
3. a targeted look into the code: `bedrock map defs <symbol>`, `bedrock map callers <symbol>`,
   or the LSP. Run `bedrock map check` first. A stale map is rebuilt before it is used.
No broad exploration. A question about behaviour ("what happens when X") always gets a look
at the code, never a note alone.
Done when: the answer below is written.

## 2. Thorough mode
Study until sure: the notes, then the code paths end to end, then the tests that pin the
behaviour. Run a probe when reading cannot settle it.
Done when: every claim of the answer points at a line that was read.

## 3. Answer shape (Russian)
```
<the answer, plain words>
Уверенность: проверил в коде сейчас / из заметки от <date> / догадка
Источник: <file:line or note name>
Перепроверить: <what to check if it matters>
```
Not in the base and no time to read the code: «быстрый ответ — догадка: …; точный займёт
2–3 минуты».
Then `bedrock question answer <id> "<one line>" --source <file:line or note>`.
Done when: the answer is logged with its source.

## 4. After a fast answer
- Start a `verifier` agent in the background with a brief from `templates/briefs/brief.md`:
  the question, the answer and its source go into Task. It is read-only and cheap. A
  contradiction is told at once: «поправка: …».
- A repeated question becomes a card: copy `templates/kb/faq.md` into the project's `faq/`,
  fill the answer and source, set `verified_at` to the current commit, and link it from
  `faq.md`. Cards go stale like module notes (D026).
Done when: the verifier reported, or the card passes `bedrock kb validate`.
