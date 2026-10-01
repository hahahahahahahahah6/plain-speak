#!/usr/bin/env python3
"""plain-speak: a readability linter for AI-generated text.

AI output has a recognizable register -- marathon sentences, abstraction
buzzwords ("leverage", "delve", "tapestry", "robust", "furthermore",
"in today's fast-paced ..."), and hedge piles. plain-speak scores text on
plainness and flags the offending lines so a human (or agent) can de-slop
before shipping.

Usage:
    plain-speak check file.txt
    cat file.txt | plain-speak check
    plain-speak check file.txt --json
    plain-speak check file.txt --fail-under 80   # exit 1 if score < 80 (CI)

Stdlib only, Python 3.9+.
"""

import argparse
import io
import json
import re
import sys

VERSION = "0.1.0"

# ----------------------------------------------------------------------------
# Built-in word lists
# ----------------------------------------------------------------------------

# ~45 AI-tell words/phrases, matched case-insensitively with word boundaries.
BUZZWORDS = [
    "additionally", "beacon", "comprehensive", "crucial", "cutting-edge",
    "deep dive", "delve", "delve into", "dynamic", "elevate", "embark",
    "empower", "ever-evolving", "facilitate", "fast-paced", "foster",
    "furthermore", "game-changer", "holistic", "in essence",
    "in today's fast-paced", "intricate", "landscape", "leverage",
    "meticulously", "moreover", "multifaceted", "navigate", "noteworthy",
    "paradigm", "pivotal", "realm", "revolutionize", "robust", "seamless",
    "state-of-the-art", "synergy", "tapestry", "testament", "underscore",
    "unlock", "unlock the potential", "unleash", "utilize", "vibrant",
]

# Hedge words/phrases; density matters more than presence.
HEDGES = [
    "arguably", "generally", "in a sense", "kind of", "maybe", "might",
    "perhaps", "possibly", "potentially", "quite", "rather", "relatively",
    "seems", "somewhat", "sort of", "typically", "usually",
]

LONG_SENTENCE_WORDS = 25  # sentences longer than this get flagged

# ----------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------


def _compile_phrase_list(phrases):
    """Build one case-insensitive regex matching any phrase as whole words.

    Longer phrases first so "unlock the potential" wins over "unlock".
    """
    ordered = sorted(phrases, key=len, reverse=True)
    # re.escape turns spaces into "\ "; swap those for \s+ (whitespace-flexible).
    alts = [re.escape(p).replace("\\ ", r"\s+") for p in ordered]
    return re.compile(r"\b(?:%s)\b" % "|".join(alts), re.IGNORECASE)


_BUZZ_RE = _compile_phrase_list(BUZZWORDS)
_HEDGE_RE = _compile_phrase_list(HEDGES)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+|\n+")
_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def count_syllables(word):
    """Estimate syllables by counting vowel groups (minimum 1)."""
    word = word.lower().strip("'-")
    if not word:
        return 0
    n = len(_VOWEL_GROUP_RE.findall(word))
    # Silent trailing 'e' usually doesn't add a syllable.
    if word.endswith("e") and n > 1 and not word.endswith(("ee", "ye", "oe")):
        n -= 1
    return max(n, 1)


def split_sentences(text):
    """Split text into sentences; each entry is (text, line_number)."""
    sentences = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        for part in _SENTENCE_SPLIT_RE.split(line):
            part = part.strip()
            if part:
                sentences.append((part, line_no))
    return sentences


def find_hits(pattern, text):
    """Return the matched phrase strings (as written in text)."""
    return [m.group(0) for m in pattern.finditer(text)]


def analyze(text):
    """Score text and collect findings.

    Returns (result_dict) with keys: plainness, grade, stats, findings.
    """
    findings = []
    long_sentences = 0
    buzzword_hits = 0
    hedge_hits = 0

    sentences = split_sentences(text)
    total_words = 0
    total_syllables = 0

    for sentence, line_no in sentences:
        words = _WORD_RE.findall(sentence)
        total_words += len(words)
        total_syllables += sum(count_syllables(w) for w in words)

        if len(words) > LONG_SENTENCE_WORDS:
            long_sentences += 1
            findings.append({
                "line": line_no,
                "rule": "long-sentence",
                "message": "Sentence has %d words (limit %d)" % (
                    len(words), LONG_SENTENCE_WORDS),
            })

        seen = set()
        for hit in find_hits(_BUZZ_RE, sentence):
            key = hit.lower()
            if key in seen:
                continue
            seen.add(key)
            buzzword_hits += 1
            findings.append({
                "line": line_no,
                "rule": "buzzword",
                "message": 'AI-tell buzzword: "%s"' % hit,
            })

        for hit in find_hits(_HEDGE_RE, sentence):
            hedge_hits += 1
            findings.append({
                "line": line_no,
                "rule": "hedge",
                "message": 'Hedge word: "%s"' % hit,
            })

    # Flesch-style reading ease from the syllable heuristic.
    if sentences and total_words:
        avg_words = total_words / len(sentences)
        avg_syll = total_syllables / total_words
        reading_ease = 206.835 - 1.015 * avg_words - 84.6 * avg_syll
        reading_ease = round(max(0.0, min(100.0, reading_ease)), 1)
    else:
        reading_ease = 100.0

    # Score: start at 100, deduct.
    score = 100.0
    score -= min(20.0, 4.0 * long_sentences)
    score -= min(30.0, 3.0 * buzzword_hits)
    score -= min(10.0, 1.0 * hedge_hits)
    if reading_ease < 60:
        score -= min(25.0, (60.0 - reading_ease) * 0.5)
    plainness = int(round(max(0.0, min(100.0, score))))

    if plainness >= 90:
        grade = "plain"
    elif plainness >= 75:
        grade = "mostly plain"
    elif plainness >= 60:
        grade = "needs polish"
    else:
        grade = "slop"

    return {
        "plainness": plainness,
        "grade": grade,
        "stats": {
            "sentences": len(sentences),
            "words": total_words,
            "long_sentences": long_sentences,
            "buzzword_hits": buzzword_hits,
            "hedge_hits": hedge_hits,
            "reading_ease": reading_ease,
        },
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------


def format_human(result):
    out = io.StringIO()
    out.write("plainness: %d/100 (%s)\n" % (result["plainness"], result["grade"]))
    s = result["stats"]
    out.write(
        "sentences: %d  words: %d  reading ease: %.1f\n"
        % (s["sentences"], s["words"], s["reading_ease"])
    )
    out.write(
        "long sentences: %d  buzzwords: %d  hedges: %d\n"
        % (s["long_sentences"], s["buzzword_hits"], s["hedge_hits"])
    )
    if result["findings"]:
        out.write("\nfindings:\n")
        out.write("%-6s %-14s %s\n" % ("LINE", "RULE", "DETAIL"))
        out.write("%-6s %-14s %s\n" % ("----", "----", "------"))
        for f in result["findings"]:
            out.write("%-6d %-14s %s\n" % (f["line"], f["rule"], f["message"]))
    else:
        out.write("\nNo findings. Nice and plain.\n")
    return out.getvalue()


def format_json(result):
    return json.dumps(result, indent=2, ensure_ascii=False) + "\n"


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def build_parser():
    p = argparse.ArgumentParser(
        prog="plain-speak",
        description="Readability linter for AI-generated text.",
    )
    p.add_argument("--version", action="version", version="plain-speak " + VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="Check a file (or stdin) for AI-register slop.")
    c.add_argument("file", nargs="?", help="File to check; reads stdin if omitted.")
    c.add_argument("--json", action="store_true", help="Machine-readable JSON output.")
    c.add_argument(
        "--fail-under", type=int, default=None, metavar="N",
        help="Exit 1 when plainness score is below N (for CI).",
    )
    return p


def cmd_check(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    result = analyze(text)

    if args.json:
        sys.stdout.write(format_json(result))
    else:
        sys.stdout.write(format_human(result))

    if args.fail_under is not None and result["plainness"] < args.fail_under:
        return 1
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "check":
        return cmd_check(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
