"""evals-kit slice 1 — graders. Contract: SPEC.md §2. Written from a blank file, Sat Oct 3.

grade(output: str, expected: dict) -> (passed: bool, reason: str)
Check: python test_runner.py   (the first ten lines are the grader tests)
"""

import re

Verdict = tuple[bool, str]  # (passed, the reason)

refusal_list = [
    "i don't know",
    "i don't have",
    "i do not know",
    "i do not have",
    "i can't help with",
    "i cannot help with",
]


def normalize(text: object) -> str:
    """Returns the text in lower case, with every run of whitespace turned into one space."""
    return " ".join(str(text).lower().split())


def grade(output: str, expected: dict) -> Verdict:  # noqa: C901
    """Grades one output against the `expected` object of one golden case.

    Args:
        output: The text the system under test returned.
        expected: The grader name under "grader", and that grader's arguments (SPEC.md §2).

    Returns:
        Whether the output passed, and the reason. The reason is "ok" on a pass.

    Raises:
        ValueError: The grader name is not one of the five.
    """
    output = normalize(output)
    if expected["grader"] in ["exact", "contains_all", "contains_none", "numeric", "abstains"]:
        if expected["grader"] == "exact":
            if normalize(expected["value"]) == output:
                return True, "ok"
            else:
                return False, f"expected exactly {expected['value']}, got {output}"
        if expected["grader"] == "contains_all":
            out_of_res = [normalize(i) for i in expected["values"] if normalize(i) not in output]
            if len(out_of_res) == 0:
                return True, "ok"
            else:
                return (
                    False,
                    f"expected to contain all of {expected['values']}, didn't contain {out_of_res}",
                )
        if expected["grader"] == "contains_none":
            in_res = [normalize(i) for i in expected["values"] if normalize(i) in output]
            if len(in_res) == 0:
                return True, "ok"
            else:
                return (
                    False,
                    f"expected to contain none of {expected['values']}, contained {in_res}",
                )
        if expected["grader"] == "numeric":
            numbers = re.findall(r"-?\d+(?:\.\d+)?", output.replace(",", ""))
            numbers = [float(i) for i in numbers]
            tol = float(expected.get("tol", 0))
            for n in numbers:
                if abs(expected["value"] - n) <= tol + 1e-9:
                    return True, "ok"
            return (
                False,
                f"expected to contain {expected['value']} with tolerance {tol} "
                f"but was equal to {output}",
            )
        if expected["grader"] == "abstains":
            if any(i in output for i in refusal_list):
                return True, "ok"
            else:
                return False, f'output "{output}" has no sentence from refusal list: {refusal_list}'
    else:
        names = ["exact", "contains_all", "contains_none", "numeric", "abstains"]
        raise ValueError(f"grader {expected['grader']} not one of expected values: {names} ")
