---
name: doc
description: Documents for people — briefs, reports, root-cause write-ups as Markdown rendered to PDF with folio. Use for "сделай отчёт", "оформи документ", "write a report", "make a PDF".
---

# Documents for people

A document says the result first and holds only what its reader needs. Every document is a
draft: the owner sends it (D057).

## Triggers
- RU: «сделай отчёт», «оформи документ», «нужна pdf-ка»
- EN: "write a report", "make a PDF", "a brief for the client"

## 1. Who reads it
- Client: plain English in the owner's voice (the `humanize` skill), result first.
- Manager: a short status.
- Team: to the point, technical.
Done when: the audience is one line at the top of the draft's front matter.

## 2. Propose the shape, the owner picks
Style is the owner's call. Propose it in one message and wait for his «ок» or his changes:
the audience, the theme, the voice and the outline.
- A call brief: theme `brief`.
- A report: theme `report`.
- A technical note: theme `console`.
- A root-cause report, in this order: the summary, what is lost and how much, the causes
  with k/n, the fixes and their status, the verification evidence, the next steps.
No charts for their own sake: a chart stays only when a table cannot carry the point.
Example: «отчёт для клиента, тема report, твой голос по-английски, 5 разделов: итог, что
потеряно, причины 7/9, что починено, что дальше. Ок?»
Done when: the owner said ок to the proposal, or changed it.

## 3. Write it to folio's conventions
- Front matter with title, date and theme.
- A paragraph that is only bold is a finding: use it for the two or three that matter.
- Numeric table columns hold numbers only, so folio aligns them.
- Every claim carries its source: a file and line, a commit, a call quote, a link.
- Run `bedrock text check <file>` for dashes and filler.
Done when: `bedrock text check` prints `[]`.

## 4. Save both, render
Both files stay, side by side, so the owner can edit the Markdown and render it again:
`~/projects-days/<project>/docs/<YYYY-MM-DD>-<slug>.md` and the same name with `.pdf`.
Outside a project: `~/projects-days/global/docs/`.
`folio <file>.md -t <theme> -o <file>.pdf`. Run `folio doctor` first when a render fails.
Done when: both files exist and the PDF's pages were looked at, or the report says why not.

## 5. Hand it over
Give the owner both paths, the `.md` and the `.pdf`, and one line on what it says. To change
it himself: edit the `.md`, then run the same `folio` line. Nothing is sent by Claude.
Done when: both paths and the line are in the chat.
