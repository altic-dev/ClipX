#!/usr/bin/env python3
"""
Classify Qwen relabel divergences from old gold into failure patterns.

Usage:
    python analyze_qwen_probe.py                           # default: qwen_probe_500
    python analyze_qwen_probe.py --cmp FILE --input FILE   # custom files
    python analyze_qwen_probe.py --reprobe reprobe_20      # compare before/after prompt fix
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def classify(user: str, old: str, new: str) -> list[str]:
    tags = []
    if old == new:
        return ["exact"]
    if not new.strip():
        return ["empty"]

    old_n = re.sub(r"\s+", " ", old).strip()
    new_n = re.sub(r"\s+", " ", new).strip()
    if old_n == new_n:
        tags.append("whitespace_only")
        return tags

    # Number direction
    old_digits = len(re.findall(r"\b\d+\b", old))
    new_digits = len(re.findall(r"\b\d+\b", new))
    if new_digits < old_digits:
        tags.append("digits_to_words")
    elif new_digits > old_digits:
        tags.append("words_to_digits")

    # Casing
    if old.lower() == new.lower() and old != new:
        tags.append("casing_only")

    # Emoji
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2764]")
    if emoji_re.search(old) and not emoji_re.search(new):
        tags.append("emoji_lost")
    elif not emoji_re.search(old) and emoji_re.search(new):
        tags.append("emoji_added")

    # Emoji command echoed instead of executed
    if re.search(r"\b(add|insert)\s+\w+\s+emoji\b", new, re.IGNORECASE):
        tags.append("emoji_command_echoed")

    # Bold/italic command echoed instead of executed
    if re.search(r"\b(add|make|apply)\s+bold\b", new, re.IGNORECASE) and "**" not in new:
        tags.append("bold_command_echoed")
    if re.search(r"\b(add|make|apply)\s+italic\b", new, re.IGNORECASE) and not re.search(r"\*[^*]", new):
        tags.append("italic_command_echoed")

    # Length change (ratio)
    lr = len(new) / max(len(old), 1)
    if lr > 1.3:
        tags.append("longer_30pct")
    elif lr < 0.7:
        tags.append("shorter_30pct")

    # Trailing period diff
    old_has = old.rstrip().endswith((".", "?", "!"))
    new_has = new.rstrip().endswith((".", "?", "!"))
    if old_has != new_has:
        tags.append("trailing_punct_diff")

    # Bullet / list markers
    if ("- " in new and "- " not in old) or ("• " in old and "- " in new):
        tags.append("bullet_change")

    # Starts differently
    old_first = old.strip().split()[0].lower() if old.strip() else ""
    new_first = new.strip().split()[0].lower() if new.strip() else ""
    if old_first and new_first and old_first != new_first:
        tags.append("first_word_change")
        openers = {"hey", "hey,", "hi", "hi,", "hello", "hello,", "yo", "yo,", "so", "so,"}
        if old_first in openers and new_first not in openers:
            tags.append("opener_stripped")
        if new_first in openers and old_first not in openers:
            tags.append("opener_added")

    # Quote style differences
    if ('"' in old) != ('"' in new):
        tags.append("quote_style_diff")

    # "Actually" appearance
    if "actually" not in old.lower() and "actually" in new.lower():
        tags.append("added_actually")

    # Markdown formatting change
    if "**" in old and "**" not in new:
        tags.append("bold_lost")
    elif "**" in new and "**" not in old:
        tags.append("bold_added")
    if ("*" in new and "**" not in new) and not ("*" in old and "**" not in old):
        tags.append("italic_added")

    # Over-aggressive pivot (no-wait / scratch-that wipes whole sentence)
    nw_words = re.compile(r"\b(no wait|scratch that|wait)\b", re.IGNORECASE)
    if nw_words.search(user):
        lr2 = len(new) / max(len(old), 1)
        if lr2 < 0.5:
            tags.append("pivot_over_deleted")

    if not tags:
        tags.append("other_content_diff")
    return tags


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def run_analysis(cmp_path: Path, input_path: Path, reprobe_cmp: Path | None = None) -> None:
    rows = [json.loads(l) for l in cmp_path.open()]
    inputs = [json.loads(l) for l in input_path.open()]
    input_by_idx = {i: obj["messages"][1]["content"] for i, obj in enumerate(inputs)}

    counts: Counter = Counter()
    examples: dict[str, list[tuple[int, str, str, str]]] = {}
    total_diff = 0

    for r in rows:
        idx = r["index"]
        old = r["old_assistant"]
        new = r["new_assistant"]
        user = input_by_idx.get(idx, "")
        if r.get("error"):
            counts["error"] += 1
            continue
        tags = classify(user, old, new)
        for t in tags:
            counts[t] += 1
            examples.setdefault(t, [])
            if len(examples[t]) < 3:
                examples[t].append((idx, user[:80], old[:80], new[:80]))
        if tags != ["exact"]:
            total_diff += 1

    print(f"Total: {len(rows)}, diverged from old gold: {total_diff}\n")
    print(f"{'Pattern':<28} {'Count':>6} {'Pct':>6}")
    print("-" * 44)
    for tag, c in counts.most_common():
        pct = 100 * c / len(rows)
        print(f"{tag:<28} {c:>6} {pct:>5.1f}%")

    priority = [
        "emoji_command_echoed",
        "bold_command_echoed",
        "italic_command_echoed",
        "pivot_over_deleted",
        "digits_to_words",
        "words_to_digits",
        "opener_stripped",
        "opener_added",
        "emoji_lost",
        "emoji_added",
        "added_actually",
        "bold_lost",
        "bullet_change",
        "first_word_change",
        "longer_30pct",
        "shorter_30pct",
        "other_content_diff",
    ]

    print("\n=== Sample examples per pattern ===")
    for tag in priority:
        if tag not in examples:
            continue
        print(f"\n--- {tag} ({counts[tag]} total) ---")
        for idx, user, old, new in examples[tag]:
            print(f"  #{idx}")
            print(f"    user: {user}")
            print(f"    old:  {old}")
            print(f"    new:  {new}")

    # Optional: reprobe comparison
    if reprobe_cmp and reprobe_cmp.is_file():
        reprobe_input_path = reprobe_cmp.parent / reprobe_cmp.name.replace("_compare.jsonl", ".jsonl")
        if not reprobe_input_path.is_file():
            print(f"\nWARNING: reprobe input not found at {reprobe_input_path}", file=sys.stderr)
            return

        print("\n\n=== REPROBE COMPARISON (before vs after prompt fix) ===")
        reprobe_cmp_rows = [json.loads(l) for l in reprobe_cmp.open()]
        reprobe_inp_rows = [json.loads(l) for l in reprobe_input_path.open()]

        # Map old compare by user text
        old_by_user: dict[str, dict] = {}
        for r in rows:
            idx = r["index"]
            user = input_by_idx.get(idx, "")
            old_by_user[user] = r

        fixed = worse = same = total = 0
        # Align by pairing reprobe input rows with their compare rows sequentially
        for i, (inp, cmp_r) in enumerate(zip(reprobe_inp_rows, reprobe_cmp_rows)):
            user = inp["messages"][1]["content"]
            gold = inp["messages"][2]["content"]
            old_r = old_by_user.get(user, {})
            old_label = old_r.get("new_assistant", "")
            new_label = cmp_r.get("new_assistant", "")
            old_sim = similarity(gold, old_label)
            new_sim = similarity(gold, new_label)
            verdict = "FIXED" if new_sim > old_sim + 0.05 else ("WORSE" if new_sim < old_sim - 0.05 else "SAME")
            total += 1
            if verdict == "FIXED":
                fixed += 1
            elif verdict == "WORSE":
                worse += 1
            else:
                same += 1
            print(f"  [{verdict}] #{i} | user: {user[:70]}")
            print(f"         gold:     {repr(gold[:70])}")
            print(f"         old Qwen: {repr(old_label[:70])}")
            print(f"         new Qwen: {repr(new_label[:70])}")
            if cmp_r.get("error"):
                print(f"         ERROR: {cmp_r['error']}")
            print()
        print(f"REPROBE SUMMARY: {total} cases | FIXED={fixed} SAME={same} WORSE={worse}")
        if total:
            print(f"  Improvement rate: {100*fixed/total:.0f}%  Regression rate: {100*worse/total:.0f}%")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cmp", type=Path, default=HERE / "qwen_probe_500_compare.jsonl")
    ap.add_argument("--input", type=Path, default=HERE / "qwen_probe_500.jsonl")
    ap.add_argument(
        "--reprobe",
        type=str,
        default="",
        help="Basename prefix for reprobe files (e.g. 'reprobe_20' → reprobe_20_compare.jsonl)",
    )
    args = ap.parse_args()

    reprobe_cmp: Path | None = None
    if args.reprobe:
        # Support bare basename (resolved relative to --cmp's directory) or full path
        base = Path(args.reprobe)
        if not base.is_absolute():
            base = args.cmp.parent / args.reprobe
        reprobe_cmp = base.parent / f"{base.name}_compare.jsonl"

    run_analysis(args.cmp, args.input, reprobe_cmp)


if __name__ == "__main__":
    main()
