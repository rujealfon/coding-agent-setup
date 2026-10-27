from pathlib import Path
import difflib
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICIES = [
    "claude/rules/delegation.md",
    "codex/AGENTS.md",
    "opencode/AGENTS.md",
    "grok/rules/delegation.md",
]
CHIEF_INSPECTORS = [
    "claude/chief-inspector.md",
    "codex/chief-inspector.toml",
    "opencode/chief-inspector.md",
    "grok/chief-inspector.md",
]
ESCALATION_PHRASES = [
    "if a failure would be silent or irreversible",
    "concurrency, ordering, or cache invalidation",
    "large cross-module diffs",
    "a fix for a bug that two attempts have not fixed",
    "verdict that is uncertain or disputed",
    "`chief-inspector`",
    "once, on the final diff before the PR",
    "without asking first",
    "not the earlier `inspector`'s findings",
    "only if the fix itself is high-risk",
    "A user's approval of a plan does not replace review.",
]
INDEPENDENCE = "Review independently; you will not receive earlier review findings."
PREAMBLE_START = INDEPENDENCE + " Look for"
PREAMBLE_END = "bypasses of checks, and silent or irreversible failures."
INTENDED_KEYS = r"^(name|description|model|effort)\s*[:=]"


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def read_lines(relative):
    return (ROOT / relative).read_text().splitlines()


def unsure_index(lines, relative):
    for index, line in enumerate(lines):
        if line.strip().startswith("When unsure, treat a change as high-risk"):
            return index
    raise AssertionError(f"{relative}: no 'When unsure' paragraph found")


def high_risk_items(relative):
    lines = read_lines(relative)
    end = unsure_index(lines, relative)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    start = end
    item_indent = None
    while start > 0:
        line = lines[start - 1]
        marker = re.match(r"^(\s+)- ", line)
        if marker:
            item_indent = len(marker.group(1))
        elif item_indent is not None and not (
            line.strip() and len(line) - len(line.lstrip()) > item_indent
        ):
            break
        elif item_indent is None and not re.match(r"^\s+\S", line):
            break
        start -= 1
    items = []
    for line in lines[start:end]:
        marker = re.match(r"^(\s+)- (.*)", line)
        if marker and len(marker.group(1)) == item_indent:
            items.append(marker.group(2))
        else:
            items[-1] += " " + line
    items = [normalize(item) for item in items]
    if not items:
        raise AssertionError(f"{relative}: no nested high-risk list found")
    return items


def escalation_paragraph(relative):
    lines = read_lines(relative)
    paragraph = []
    for line in lines[unsure_index(lines, relative):]:
        if line.startswith("- ") or (paragraph and not line.strip()):
            break
        paragraph.append(line)
    return normalize(" ".join(paragraph))


def without_intended_differences(lines, drop_preamble):
    lines = [line for line in lines if not re.match(INTENDED_KEYS, line)]
    if drop_preamble:
        start = next(
            (i for i, line in enumerate(lines) if line.startswith(PREAMBLE_START)), None
        )
        if start is None or not lines[start + 2].startswith(PREAMBLE_END):
            raise AssertionError("independence preamble not found")
        del lines[start : start + 3]
    return lines


class PolicySyncTests(unittest.TestCase):
    def test_high_risk_lists_are_identical(self):
        reference = high_risk_items(POLICIES[0])
        for relative in POLICIES[1:]:
            items = high_risk_items(relative)
            diff = "\n".join(
                difflib.unified_diff(reference, items, POLICIES[0], relative, lineterm="")
            )
            self.assertEqual(items, reference, f"{relative} high-risk list differs:\n{diff}")

    def test_escalation_paragraph_shares_phrases(self):
        for relative in POLICIES:
            paragraph = escalation_paragraph(relative)
            for phrase in ESCALATION_PHRASES:
                self.assertIn(phrase, paragraph, f"{relative} is missing: {phrase!r}")

    def test_chief_inspectors_require_independence(self):
        for relative in CHIEF_INSPECTORS:
            text = normalize((ROOT / relative).read_text())
            self.assertIn(INDEPENDENCE, text, f"{relative} lacks the independence instruction")

    def test_chief_inspectors_copy_their_inspector(self):
        for chief in CHIEF_INSPECTORS:
            inspector = chief.replace("chief-inspector", "inspector")
            with self.subTest(chief=chief):
                expected = without_intended_differences(read_lines(inspector), False)
                actual = without_intended_differences(read_lines(chief), True)
                diff = "\n".join(
                    difflib.unified_diff(expected, actual, inspector, chief, lineterm="")
                )
                self.assertEqual(actual, expected, f"{chief} differs from {inspector}:\n{diff}")


if __name__ == "__main__":
    unittest.main()
