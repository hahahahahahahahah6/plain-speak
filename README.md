# plain-speak

You can spot AI-written text in three seconds: the 60-word sentence that never lands, the "leverage the robust tapestry" filler, the "furthermore / moreover / additionally" drumbeat, the hedge pile ("might arguably perhaps be"). Grammar checkers don't catch any of this — the grammar is perfect; the *register* is the problem. **plain-speak** is a tiny readability linter that scores text on plainness and flags the offending lines, so you (or your agent) can de-slop a draft before it ships.

## Install

```bash
pip install plain-speak
```

Or just grab the single file — it's stdlib-only, no dependencies:

```bash
curl -O https://raw.githubusercontent.com/hahahahahahahahah6/plain-speak/main/plain_speak.py
python3 plain_speak.py check draft.txt
```

Python 3.9+.

## Usage

```bash
plain-speak check draft.txt          # check a file
cat draft.txt | plain-speak check     # or pipe stdin
plain-speak check draft.txt --json   # machine-readable output
plain-speak check draft.txt --fail-under 80   # exit 1 when score < 80 (for CI)
```

What it checks:

1. **Long sentences** — anything over 25 words gets flagged (`long-sentence`).
2. **AI-tell buzzwords** — ~45 built-in words/phrases (`leverage`, `delve`, `tapestry`, `robust`, `furthermore`, `in today's fast-paced`, `unlock the potential`, …), case-insensitive, reported with the offending word (`buzzword`).
3. **Reading ease** — Flesch-style score via a simple vowel-group syllable heuristic, folded into the plainness score.
4. **Hedge density** — `maybe`, `perhaps`, `generally`, `arguably`, `somewhat`, and friends (`hedge`).

Example:

```
$ plain-speak check draft.txt
plainness: 45/100 (slop)
sentences: 3  words: 80  reading ease: 30.7
long sentences: 2  buzzwords: 24  hedges: 2

findings:
LINE   RULE           DETAIL
----   ----           ------
1      long-sentence  Sentence has 32 words (limit 25)
1      buzzword       AI-tell buzzword: "In today's fast-paced"
1      buzzword       AI-tell buzzword: "landscape"
1      buzzword       AI-tell buzzword: "crucial"
1      buzzword       AI-tell buzzword: "leverage"
1      buzzword       AI-tell buzzword: "cutting-edge"
1      buzzword       AI-tell buzzword: "unlock"
1      buzzword       AI-tell buzzword: "foster"
1      buzzword       AI-tell buzzword: "seamless"
1      buzzword       AI-tell buzzword: "robust"
1      buzzword       AI-tell buzzword: "comprehensive"
1      buzzword       AI-tell buzzword: "holistic"
2      long-sentence  Sentence has 41 words (limit 25)
2      buzzword       AI-tell buzzword: "Furthermore"
2      buzzword       AI-tell buzzword: "elevate"
2      buzzword       AI-tell buzzword: "delve"
2      buzzword       AI-tell buzzword: "intricate"
2      buzzword       AI-tell buzzword: "tapestry"
2      buzzword       AI-tell buzzword: "meticulously"
2      buzzword       AI-tell buzzword: "navigate"
2      buzzword       AI-tell buzzword: "ever-evolving"
2      buzzword       AI-tell buzzword: "synergy"
2      buzzword       AI-tell buzzword: "testament"
2      buzzword       AI-tell buzzword: "dynamic"
2      buzzword       AI-tell buzzword: "vibrant"
2      buzzword       AI-tell buzzword: "realm"
2      hedge          Hedge word: "might"
2      hedge          Hedge word: "arguably"
```

And a plain passage:

```
$ echo "Cats sleep most of the day. Give your cat fresh water every day." | plain-speak check
plainness: 100/100 (plain)
sentences: 2  words: 14  reading ease: 97.0
long sentences: 0  buzzwords: 0  hedges: 0

No findings. Nice and plain.
```

CI gate example — fail the build when a generated doc is too sloppy:

```bash
plain-speak check release-notes.md --fail-under 80
```

## Differentiation

Grammar checkers (Grammarly, LanguageTool) fix grammar. That's a different problem: AI slop is *grammatically flawless*. What plain-speak targets is the AI **register** — the specific constellation of marathon sentences, abstraction buzzwords, and hedge piles that makes generated text instantly recognizable.

It's also built for agents, not just humans:

- `--json` and `--fail-under` make it a CI gate for generated docs.
- The repo ships a **`SKILL.md`** agent skill with a reading-level ladder (ELI5 / engineer / one-liner): prompt templates an agent uses to *rewrite* flagged text. The CLI detects; the skill rewrites. Pair them in a loop: `plain-speak check` → rewrite with the skill → check again until the score passes.

## License

MIT — see [LICENSE](LICENSE).
