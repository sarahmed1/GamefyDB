"""Local plagiat check: n-gram overlap between a chapter and reference reports.

Usage:
    python scripts/plagiat_check.py docs/rapport_chapters1_2.tex

Compares the chapter against docs/_ref_ichrak.txt and docs/_ref_amal.txt
(and optionally any other text given via --extra-ref).

Output:
    overall % of chapter shingles that also appear in either reference,
    plus the longest verbatim spans (>= 8 words) shared with each reference.

This is *not* a real plagiat tool (no web/academic corpus access). It only
catches drift toward the two reference reports we used as structural models.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DEFAULT_REFS = [DOCS / "_ref_ichrak.txt", DOCS / "_ref_amal.txt"]

LATEX_CMD = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?")
LATEX_ENV = re.compile(r"\\(begin|end)\{[^}]+\}")
LATEX_BRACES = re.compile(r"[{}]")
LATEX_COMMENT = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
MULTI_WS = re.compile(r"\s+")
NON_WORD = re.compile(r"[^a-zA-Z0-9'\- ]+")


def strip_latex(text: str) -> str:
    text = LATEX_COMMENT.sub(" ", text)
    text = LATEX_ENV.sub(" ", text)
    # repeatedly strip simple commands until stable
    prev = None
    while prev != text:
        prev = text
        text = LATEX_CMD.sub(" ", text)
    text = LATEX_BRACES.sub(" ", text)
    return text


def tokenize(text: str, *, is_latex: bool) -> list[str]:
    if is_latex:
        text = strip_latex(text)
    text = text.lower()
    text = NON_WORD.sub(" ", text)
    text = MULTI_WS.sub(" ", text).strip()
    return text.split()


def shingles(tokens: list[str], n: int) -> Counter:
    return Counter(" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def overlap_pct(chapter: Counter, reference: Counter) -> tuple[float, int, int]:
    if not chapter:
        return 0.0, 0, 0
    matched = sum(min(c, reference.get(k, 0)) for k, c in chapter.items())
    total = sum(chapter.values())
    return 100.0 * matched / total, matched, total


def longest_shared_spans(
    chapter_tokens: list[str], ref_tokens: list[str], min_len: int = 8, top: int = 5
) -> list[tuple[int, str]]:
    ref_text = " " + " ".join(ref_tokens) + " "
    found: dict[str, int] = {}
    i = 0
    while i < len(chapter_tokens) - min_len + 1:
        # binary search the longest k such that the span exists in ref_text
        lo, hi = min_len, min(60, len(chapter_tokens) - i)
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            span = " ".join(chapter_tokens[i : i + mid])
            if f" {span} " in ref_text:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best >= min_len:
            span = " ".join(chapter_tokens[i : i + best])
            found[span] = max(found.get(span, 0), best)
            i += best
        else:
            i += 1
    return sorted(((v, k) for k, v in found.items()), reverse=True)[:top]


def check(chapter_path: Path, refs: list[Path], n: int = 5) -> None:
    chapter_raw = chapter_path.read_text(encoding="utf-8", errors="ignore")
    chapter_tokens = tokenize(chapter_raw, is_latex=chapter_path.suffix == ".tex")
    chapter_shingles = shingles(chapter_tokens, n)
    print(f"\nChapter: {chapter_path.name}")
    print(f"  tokens: {len(chapter_tokens):,}   {n}-gram shingles: {sum(chapter_shingles.values()):,}")

    worst = 0.0
    for ref_path in refs:
        ref_raw = ref_path.read_text(encoding="utf-8", errors="ignore")
        ref_tokens = tokenize(ref_raw, is_latex=ref_path.suffix == ".tex")
        ref_shingles = shingles(ref_tokens, n)
        pct, matched, total = overlap_pct(chapter_shingles, ref_shingles)
        worst = max(worst, pct)
        print(f"\n  vs {ref_path.name}: {pct:5.2f}%   ({matched:,}/{total:,} {n}-grams)")
        spans = longest_shared_spans(chapter_tokens, ref_tokens)
        if spans:
            print(f"    longest shared spans:")
            for length, span in spans:
                snippet = span if len(span) < 140 else span[:137] + "..."
                print(f"      [{length:2d} words] {snippet}")

    flag = "OK" if worst < 15 else "OVER 15% — REVISE"
    print(f"\n  worst overlap: {worst:.2f}%   {flag}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("chapter", type=Path)
    p.add_argument("--ref", action="append", type=Path, default=None,
                   help="reference file (can be given multiple times)")
    p.add_argument("-n", type=int, default=5, help="n-gram size (default 5)")
    args = p.parse_args()

    refs = args.ref if args.ref else DEFAULT_REFS
    refs = [r for r in refs if r.exists()]
    if not refs:
        print("no reference files found", file=sys.stderr)
        return 1
    check(args.chapter, refs, n=args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
