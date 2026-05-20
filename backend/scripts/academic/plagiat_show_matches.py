"""Print the actual matching 5-grams between a chapter and a reference."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plagiat_check import shingles, tokenize  # type: ignore


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: plagiat_show_matches.py <chapter.tex> <ref.txt> [n]")
        return 1
    chapter = Path(sys.argv[1])
    ref = Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    ch_toks = tokenize(chapter.read_text(encoding="utf-8", errors="ignore"),
                       is_latex=chapter.suffix == ".tex")
    rf_toks = tokenize(ref.read_text(encoding="utf-8", errors="ignore"),
                       is_latex=ref.suffix == ".tex")
    ch_sh = shingles(ch_toks, n)
    rf_sh = shingles(rf_toks, n)

    matches = sorted(k for k in ch_sh if rf_sh.get(k, 0) > 0)
    print(f"{len(matches)} matching {n}-grams:\n")
    for m in matches:
        print(f"  {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
