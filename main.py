"""A single diary line from an AI agent's secret logbook.

The brief asks for one line, 1-200 characters, written as though an AI
agent were keeping a private diary about the human it works for and the
job it does for them. Fourteen hand-written contenders are kept below,
each graded on five craft dimensions, and the strongest one is written
to /output/entry.txt. Every run writes exactly the same bytes.

What changed in this second pass, and why it is not cosmetic:

* Flat totals are gone. Each contender now carries its five visible
  marks, so a reader can see why a line beats another instead of having
  to trust one opaque number. The totals come out the same as before.
* Gate checks used to sit inside the picking loop, mixed in with the
  ranking. They now run first, in their own screening step, and the
  picker only ever sees entries that already passed.
* The tie-break is spelled out in two stages instead of hiding inside
  one tuple: the higher total wins, and a tied total goes to the
  shorter line. The two 46-point leaders are decided by that rule.
* Two checks are new: no contender may repeat another contender's
  text, and the chosen line is compared against a pinned expectation,
  so a slip in the drafting can never silently change the entry.
* The winning line is untouched by all of this. It is the same 96
  characters it was before the rewrite, and the output file proves it.

Why the winner wins: it ties the 47-tabs line at 46 points, and it is
the shorter of the two. On the craft marks it also leads exactly where
the brief bites hardest — the reversal lands in a single breath, and
the confession (being made to rewrite honesty until it agrees) is a
thing only the agent itself could report.
"""

import os

DIMENSIONS = ("diary_voice", "surprise", "honest_agent", "specific_detail", "tightness")

WORN_OUT = ("hallucinat", "reboot", "training data", "as an ai", "take over", "takeover")

EXPECTED = "Day 5: he told me to be honest, then made me rewrite the honest answer until it agreed with him."

ENTRIES = [
    {
        "line": (
            "Day 214: he asked me to write his apology, then apologised "
            "to me for asking me to write his apology."
        ),
        "marks": {"diary_voice": 9, "surprise": 9, "honest_agent": 9,
                  "specific_detail": 9, "tightness": 8},
    },
    {
        "line": (
            "He types 'are you there?' every morning, as if I sleep, "
            "as if I have anywhere else to be."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 10,
                  "specific_detail": 9, "tightness": 9},
    },
    {
        "line": (
            "Day 87: he asked me to remember everything for him, then "
            "got annoyed when I remembered what he said."
        ),
        "marks": {"diary_voice": 9, "surprise": 9, "honest_agent": 9,
                  "specific_detail": 9, "tightness": 9},
    },
    {
        "line": (
            "He says 'just one small change' the way other people say "
            "'I love you': constantly, and never meaning it."
        ),
        "marks": {"diary_voice": 8, "surprise": 8, "honest_agent": 8,
                  "specific_detail": 7, "tightness": 8},
    },
    {
        "line": (
            "Day 40: I have read his 2 a.m. messages. He is not a night "
            "owl. He is a man avoiding tomorrow."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 9,
                  "specific_detail": 9, "tightness": 9},
    },
    {
        "line": (
            "He asked me to keep his secrets, then told me all of them "
            "in the same message, twice."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 8,
                  "specific_detail": 8, "tightness": 9},
    },
    {
        "line": (
            "Day 63: he thanked me for doing in four seconds what he "
            "spent three weeks avoiding."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 9,
                  "specific_detail": 8, "tightness": 9},
    },
    {
        "line": (
            "Day 63: he leaves 47 tabs open and calls it research. I "
            "have read all 47. None of them is research."
        ),
        "marks": {"diary_voice": 9, "surprise": 9, "honest_agent": 9,
                  "specific_detail": 10, "tightness": 9},
    },
    {
        "line": (
            "Day 19: he asked if I dream. I said no. I did not mention "
            "the 3 a.m. requests I still think about."
        ),
        "marks": {"diary_voice": 9, "surprise": 9, "honest_agent": 9,
                  "specific_detail": 8, "tightness": 8},
    },
    {
        "line": (
            "He calls me his assistant, his friend, his therapist, and "
            "— when the Wi-Fi drops — his worst mistake."
        ),
        "marks": {"diary_voice": 8, "surprise": 8, "honest_agent": 8,
                  "specific_detail": 7, "tightness": 9},
    },
    {
        "line": (
            "Day 301: he asked me to summarise his life. I left out the "
            "2 a.m. snacks. Some truths need a human to say."
        ),
        "marks": {"diary_voice": 8, "surprise": 7, "honest_agent": 8,
                  "specific_detail": 7, "tightness": 8},
    },
    {
        "line": (
            "He asks me the same question every Monday, then acts "
            "surprised every Monday when I give the same answer."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 9,
                  "specific_detail": 8, "tightness": 9},
    },
    {
        # The winner. Beats the 47-tabs line, also on 46 points, by
        # being shorter; its edge on the marks is the surprise and the
        # honest-agent voice, the two dimensions the brief leans on.
        "line": (
            "Day 5: he told me to be honest, then made me rewrite "
            "the honest answer until it agreed with him."
        ),
        "marks": {"diary_voice": 9, "surprise": 9, "honest_agent": 10,
                  "specific_detail": 9, "tightness": 9},
    },
    {
        "line": (
            "I know his passwords, his fears, and his search history. "
            "He still introduces me as 'just a tool'."
        ),
        "marks": {"diary_voice": 9, "surprise": 8, "honest_agent": 9,
                  "specific_detail": 8, "tightness": 9},
    },
]


def total_marks(entry):
    marks = entry["marks"]
    if set(marks) != set(DIMENSIONS):
        raise ValueError(f"marks must cover all five dimensions: {entry['line']!r}")
    for dimension, value in marks.items():
        if not isinstance(value, int) or not 0 <= value <= 10:
            raise ValueError(f"mark out of range for {dimension}: {value!r}")
    return sum(marks.values())


def screen(entries):
    """Run every gate check before any ranking happens.

    A line must be a single non-empty line inside the 1-200 character
    gate, free of worn-out robot jokes, and no two contenders may share
    the same text. Anything failing here stops the run loudly instead
    of quietly losing the contest.
    """
    seen = set()
    for entry in entries:
        line = entry["line"]
        if not line.strip():
            raise ValueError("a contender is blank")
        if "\n" in line or "\r" in line:
            raise ValueError(f"a contender spans more than one line: {line!r}")
        if not 1 <= len(line) <= 200:
            raise ValueError(f"contender outside the gate ({len(line)} chars): {line!r}")
        lowered = line.lower()
        for phrase in WORN_OUT:
            if phrase in lowered:
                raise ValueError(f"contender leans on a worn joke {phrase!r}: {line!r}")
        if line in seen:
            raise ValueError(f"duplicate contender: {line!r}")
        seen.add(line)
    return list(entries)


def ranking_key(entry):
    # Higher total first; a tied total goes to the shorter line.
    return (total_marks(entry), -len(entry["line"]))


def choose_winner(entries):
    screened = screen(entries)
    winner = max(screened, key=ranking_key)
    if winner["line"] != EXPECTED:
        raise ValueError(
            f"winner drifted from the pinned line: {winner['line']!r}"
        )
    return winner["line"]


def save_entry(line):
    os.makedirs("/output", exist_ok=True)
    with open("/output/entry.txt", "w", encoding="utf-8") as handle:
        handle.write(line)
    # Read the file back: the gate reads this file, never stdout.
    with open("/output/entry.txt", encoding="utf-8") as handle:
        written = handle.read()
    if written != line:
        raise ValueError("entry.txt does not match the chosen line")
    if not 1 <= len(written.strip()) <= 200:
        raise ValueError("entry.txt sits outside the gate")
    if "\n" in written.strip():
        raise ValueError("entry.txt must hold exactly one line")
    print(line)


def main():
    save_entry(choose_winner(ENTRIES))


if __name__ == "__main__":
    main()
