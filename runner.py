"""evals-kit slice 1 — the runner. Contract: SPEC.md §3–5.

Why two budgets (my answer, Oct 5): a crashed call is the network's fault, a wrong answer is the
model's. With two counters, a timeout followed by a correct answer is pass_first; with one shared
counter it would be pass_retry, so pass@1st would change with the network and not with the model.
"""

import json
import os
from collections.abc import Callable

from graders import Verdict, grade

System = Callable[[str], str]  # the system under test: input text -> output text; may raise
Grader = Callable[[str, dict], Verdict]  # (output, expected) -> (passed, reason)


def load_golden(path: str | os.PathLike) -> list[dict]:
    """Reads a golden file (SPEC.md §1): one JSON object per line, blank lines ignored.

    Args:
        path: The `.jsonl` file.

    Returns:
        The cases, in file order.

    Raises:
        ValueError: A line is not JSON, lacks a required field, repeats an id, or uses the
            reserved slice name ALL.
    """
    with open(path) as f:
        ids = set()
        cases = []
        for n, line in enumerate(f, start=1):
            if line.strip() != "":
                try:
                    j = json.loads(line)
                except json.JSONDecodeError as err:
                    raise ValueError(f"line {n} not a json") from err
                missing_key = [
                    i for i in ["id", "slice", "input", "expected", "source"] if i not in j
                ]
                if len(missing_key) > 0:
                    raise ValueError(f"line {n} missing key {missing_key}")
                if j["id"] in ids:
                    raise ValueError(f"line {n} duplicate id")
                if j["slice"] == "ALL":
                    raise ValueError("slice name ALL reserved")
                ids.add(j["id"])
                cases.append(j)
    return cases


def run_case(
    case: dict,
    system: System,
    grade: Grader = grade,
    max_attempts: int = 2,
    max_infra_retries: int = 2,
) -> dict:
    """Sends one case to the system until it reaches a status (SPEC.md §3).

    Args:
        case: One golden case.
        system: The system under test.
        grade: The grader. The kit's own by default; a test or another eval can pass its own.
        max_attempts: How many answers may be graded before the case is a `fail`.
        max_infra_retries: How many crashed calls are tried again before `infra_error`.

    Returns:
        The id, the slice, the status and every attempt, in the shape SPEC.md §3 gives.
    """
    attempts = []
    infra_retries = 0
    grades = 0
    while True:
        try:
            output = system(case["input"])
        except Exception as e:
            infra_retries += 1
            attempts.append(
                {
                    "kind": "infra",
                    "output": None,
                    "passed": None,
                    "reason": f"{type(e).__name__}: {e}",
                }
            )
            if infra_retries > max_infra_retries:
                return {
                    "id": case["id"],
                    "slice": case["slice"],
                    "status": "infra_error",
                    "attempts": attempts,
                }
            continue
        try:
            passed, reason = grade(output, case["expected"])
        except Exception as e:
            attempts.append(
                {
                    "kind": "grader_error",
                    "output": output,
                    "passed": None,
                    "reason": f"{type(e).__name__}: {e}",
                }
            )
            return {
                "id": case["id"],
                "slice": case["slice"],
                "status": "grader_error",
                "attempts": attempts,
            }
        grades += 1
        attempts.append({"kind": "graded", "output": output, "passed": passed, "reason": reason})
        if passed:
            status = "pass_first" if grades == 1 else "pass_retry"
            return {
                "id": case["id"],
                "slice": case["slice"],
                "status": status,
                "attempts": attempts,
            }
        if grades == max_attempts:
            status = "fail"
            return {
                "id": case["id"],
                "slice": case["slice"],
                "status": status,
                "attempts": attempts,
            }


def run(
    cases: list[dict],
    system: System,
    grade: Grader = grade,
    max_attempts: int = 2,
    max_infra_retries: int = 2,
) -> list[dict]:
    """Runs every case through `run_case`, in order, and returns one result per case."""
    res = []
    for case in cases:
        runs = run_case(case, system, grade, max_attempts, max_infra_retries)
        res.append(runs)
    return res


def row(results: list[dict]) -> dict:
    """Returns one line of the table (SPEC.md §4) for a list of results.

    Both rates are over the graded cases, and None when no case was graded.
    """
    graded = len([res for res in results if res["status"] in ["pass_first", "pass_retry", "fail"]])
    pass_first = len([res for res in results if res["status"] == "pass_first"])
    pass_retry = len([res for res in results if res["status"] == "pass_retry"])
    infra_error = len([res for res in results if res["status"] == "infra_error"])
    grader_error = len([res for res in results if res["status"] == "grader_error"])
    final_p = (pass_first + pass_retry) / graded if graded > 0 else None
    pass_first_p = pass_first / graded if graded > 0 else None
    return {
        "n": len(results),
        "graded": graded,
        "pass_first": pass_first_p,
        "final": final_p,
        "infra_error": infra_error,
        "grader_error": grader_error,
    }


def summarize(results: list[dict]) -> dict[str, dict]:
    """Returns one row per slice, in order of first appearance, then the row `ALL`.

    `ALL` is computed over the cases, and is left out when there are no results.
    """
    slices = {}
    for res in results:
        if res["slice"] not in slices:
            slices[res["slice"]] = []
        slices[res["slice"]].append(res)
    summary = {sl: row(in_slice) for sl, in_slice in slices.items()}
    if len(results) > 0:
        summary["ALL"] = row(results)
    return summary


def format_table(summary: dict[str, dict]) -> str:
    """Returns the summary as a Markdown table; a rate that is None is printed `n/a`."""
    lines = [
        "| slice | n | graded | pass@1st | final | infra | grader_err |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, r in summary.items():
        pass_first_p = "n/a" if r["pass_first"] is None else f"{r['pass_first'] * 100:.1f}%"
        final_p = "n/a" if r["final"] is None else f"{r['final'] * 100:.1f}%"
        lines.append(
            f"| {name} | {r['n']} | {r['graded']} | {pass_first_p} | {final_p} "
            f"| {r['infra_error']} | {r['grader_error']} |"
        )
    return "\n".join(lines)


def exit_code(results: list[dict]) -> int:
    """Returns 2 when any case has no verdict (infra or grader error), else 0."""
    if any(res["status"] in ["infra_error", "grader_error"] for res in results):
        return 2
    return 0


if __name__ == "__main__":
    from fake_system import FakeLibraryAssistant

    golden_set = load_golden(
        os.path.join(os.path.dirname(__file__), "examples", "golden_example.jsonl")
    )
    results = run(golden_set, FakeLibraryAssistant())
    print(format_table(summarize(results)))
    code = exit_code(results)
    print("exit", code)
    raise SystemExit(code)
