# plain-speak — agent skill: de-slop rewriting

`plain-speak` (CLI, single file `plain_speak.py`) **detects** AI-register slop.
This skill tells you how to **rewrite** what it flags. Workflow:

1. Run `plain-speak check draft.txt` (or `--json`).
2. For each flagged line, pick a rung on the reading-level ladder below and rewrite.
3. Re-run until `plainness` passes your `--fail-under` gate.

## The ladder

Match the rung to the audience. When unsure, default to **engineer**.

### ELI5 — explain it like I'm five

Use for: general readers, docs, landing pages, anything public-facing.

Prompt template:

```
Rewrite the passage below so a smart 10-year-old gets it on first read.
- Max 20 words per sentence. One idea per sentence.
- Replace every abstract noun with a concrete verb or example.
- Delete these words outright: leverage, delve, robust, seamless, holistic,
  synergy, paradigm, landscape, realm, furthermore, moreover, additionally,
  utilize, facilitate, crucial, pivotal, noteworthy, vibrant, intricate,
  meticulously, testament, beacon, dynamic, ever-evolving, cutting-edge.
- No hedge piles: pick one — state it or cut it.
- If a sentence starts with "In today's fast-paced", delete the opener.

PASSAGE:
<flagged text>
```

### Engineer — precise, no filler

Use for: READMEs, code comments, technical docs, commit messages, PR descriptions.

Prompt template:

```
Rewrite the passage below for a working engineer who is skimming.
- Max 25 words per sentence. Short paragraphs.
- Lead with the concrete claim: what does it do, what changed, what breaks.
- Kill buzzwords (leverage→use, utilize→use, facilitate→let/help,
  robust→works when X fails, seamless→no manual steps, holistic→all of it).
- Cut hedges unless the uncertainty is the point; then state it once, plainly.
- Keep technical terms; delete everything that only sounds technical.

PASSAGE:
<flagged text>
```

### One-liner — the whole point in one breath

Use for: TL;DRs, commit subjects, changelog entries, status updates.

Prompt template:

```
Compress the passage below into ONE sentence under 25 words.
- Subject, verb, object. No setup clause, no "in order to".
- Drop every adjective that isn't load-bearing.
- If the result sounds like marketing, you failed — try again drier.

PASSAGE:
<flagged text>
```

## Rules of thumb (all rungs)

- **Buzzword → concrete swap cheat sheet:** leverage→use · utilize→use · delve→dig into / look at · robust→holds up when X · seamless→no extra steps · holistic→whole · synergy→working together · paradigm→model / way · landscape→field · realm→area · furthermore/moreover/additionally→and, or just start the sentence · foster→help grow · elevate→raise / improve · navigate→handle · underscore→show · unlock the potential→makes possible.
- **Long sentence fix:** split at the "and/which/that" joint. If it survives splitting, it wasn't too long.
- **Hedge fix:** "might arguably perhaps" → pick the strongest true claim and state it. If you genuinely don't know, say "unknown" once.
- **Never** add new buzzwords while rewriting. Re-run `plain-speak check` after — the score is the referee, not your taste.
