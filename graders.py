"""evals-kit slice 1 — graders. Contract: SPEC.md §2. Written by hand by the author, Oct 3, 2026.

grade(output: str, expected: dict) -> (passed: bool, reason: str)
Check: python test_runner.py   (the first twelve lines are the grader tests)
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


def grade_exact(output: str, expected: dict) -> Verdict:
    """Passes when the whole output equals `value`."""
    if normalize(expected["value"]) == output:
        return True, "ok"
    else:
        return False, f"expected exactly {expected['value']}, got {output}"


def check_has_values(expected: dict) -> None:
    """Raises ValueError when `values` is empty: with nothing to look for, any output passes."""
    if len(expected["values"]) == 0:
        raise ValueError(f"grader {expected['grader']} needs at least one value, got an empty list")


def grade_contains_all(output: str, expected: dict) -> Verdict:
    """Passes when every one of `values` is in the output."""
    check_has_values(expected)
    out_of_res = [normalize(i) for i in expected["values"] if normalize(i) not in output]
    if len(out_of_res) == 0:
        return True, "ok"
    else:
        return (
            False,
            f"expected to contain all of {expected['values']}, didn't contain {out_of_res}",
        )


def grade_contains_none(output: str, expected: dict) -> Verdict:
    """Passes when none of `values` is in the output."""
    check_has_values(expected)
    in_res = [normalize(i) for i in expected["values"] if normalize(i) in output]
    if len(in_res) == 0:
        return True, "ok"
    else:
        return (
            False,
            f"expected to contain none of {expected['values']}, contained {in_res}",
        )


def grade_numeric(output: str, expected: dict) -> Verdict:
    """Passes when some number in the output is within `tol` of `value`."""
    numbers = re.findall(r"-?\d+(?:\.\d+)?", output.replace(",", ""))
    numbers = [float(i) for i in numbers]
    tol = float(expected.get("tol", 0))
    for n in numbers:
        if abs(expected["value"] - n) <= tol + 1e-9:
            return True, "ok"
    return (
        False,
        f"expected to contain {expected['value']} with tolerance {tol} but was equal to {output}",
    )


def grade_abstains(output: str, expected: dict) -> Verdict:
    """Passes when the output contains a phrase of `refusal_list`."""
    if any(i in output for i in refusal_list):
        return True, "ok"
    else:
        return False, f'output "{output}" has no sentence from refusal list: {refusal_list}'


# Grader name -> function. Each function gets the output already normalized. A new grader is one
# function above and one entry here.
GRADERS = {
    "exact": grade_exact,
    "contains_all": grade_contains_all,
    "contains_none": grade_contains_none,
    "numeric": grade_numeric,
    "abstains": grade_abstains,
}


def grade(output: str, expected: dict) -> Verdict:
    """Grades one output against the `expected` object of one golden case.

    Args:
        output: The text the system under test returned.
        expected: The grader name under "grader", and that grader's arguments (SPEC.md §2).

    Returns:
        Whether the output passed, and the reason. The reason is "ok" on a pass.

    Raises:
        ValueError: The grader name is not in `GRADERS`.
    """
    output = normalize(output)
    # Looked up in a list of the names: a name that is not text (a list, a number) is then
    # simply not found, where the table itself would stop on it with a TypeError.
    if expected["grader"] in list(GRADERS):
        return GRADERS[expected["grader"]](output, expected)
    else:
        raise ValueError(
            f"grader {expected['grader']} not one of expected values: {list(GRADERS)} "
        )
