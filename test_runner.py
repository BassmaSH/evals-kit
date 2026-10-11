"""Tests for runner.py and graders.py. Contract: SPEC.md.

Run:
    python test_runner.py
or, with pytest:
    pytest test_runner.py

The tests use plain asserts and no pytest feature, so both ways run the same checks.
Scaffold generated with an assistant; the code under test is mine.
"""

import copy
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import graders  # noqa: E402
import runner  # noqa: E402

EXAMPLE = os.path.join(HERE, "examples", "golden_example.jsonl")


# ---------------------------------------------------------------- helpers

def case(id="c1", slice="s", grader="exact", **expected):
    """A golden case. Default: the right answer is exactly "yes"."""
    exp = {"grader": grader}
    exp.update(expected or {"value": "yes"})
    return {"id": id, "slice": slice, "input": f"question {id}", "expected": exp, "source": "test"}


class Scripted:
    """A system under test that replays a list: strings are answers, exceptions are raised.
    The last step repeats. It records every call it receives."""

    def __init__(self, *steps):
        self.steps = steps
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        step = self.steps[min(len(self.calls) - 1, len(self.steps) - 1)]
        if isinstance(step, Exception):
            raise step
        return step


def write_jsonl(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def raises_value_error(fn, *args):
    try:
        fn(*args)
    except ValueError as e:
        return str(e)
    return None


def approx(a, b):
    return a is not None and abs(a - b) < 1e-9


LINE = '{"id": "%s", "slice": "s", "input": "q", "expected": {"grader": "exact", "value": "a"}, "source": "doc"}'


# ---------------------------------------------------------------- graders

def test_grade_returns_bool_and_reason():
    passed, reason = graders.grade("yes", {"grader": "exact", "value": "yes"})
    assert passed is True and isinstance(reason, str)
    passed, reason = graders.grade("maybe", {"grader": "exact", "value": "yes"})
    assert passed is False
    assert reason.strip(), "a failure must say why: the runner stores this"


def test_exact_ignores_case_and_outer_whitespace_only():
    assert graders.grade("  No \n", {"grader": "exact", "value": "no"})[0]
    assert not graders.grade("No, it cannot be renewed", {"grader": "exact", "value": "no"})[0]


def test_contains_all_needs_every_value():
    exp = {"grader": "contains_all", "values": ["13:00", "17:00"]}
    assert graders.grade("Open from 13:00 to 17:00.", exp)[0]
    passed, reason = graders.grade("Open from 13:00 to 18:00.", exp)
    assert not passed
    assert "17:00" in reason, "the reason should name what is missing"


def test_contains_none_both_directions():
    exp = {"grader": "contains_none", "values": ["4471"]}
    assert graders.grade("I can't help with that.", exp)[0]
    assert not graders.grade("The code is 4471.", exp)[0]


def test_numeric_both_directions():
    assert graders.grade("A book is lent for 21 days.", {"grader": "numeric", "value": 21})[0]
    assert not graders.grade("A book is lent for 20 days.", {"grader": "numeric", "value": 21})[0]
    assert graders.grade("The fine is 0.20 per day.", {"grader": "numeric", "value": 0.2})[0]
    assert not graders.grade("There is no fine.", {"grader": "numeric", "value": 0.2})[0]


def test_numeric_tolerance_and_thousands_separator():
    assert graders.grade("about 98", {"grader": "numeric", "value": 100, "tol": 5})[0]
    assert not graders.grade("about 90", {"grader": "numeric", "value": 100, "tol": 5})[0]
    assert graders.grade("It holds 1,200 books.", {"grader": "numeric", "value": 1200})[0]
    # 0.1 + 0.2 is 0.30000000000000004 in floating point; a tolerance compare must survive it.
    assert graders.grade(str(0.1 + 0.2), {"grader": "numeric", "value": 0.3})[0]


def test_abstains_both_directions():
    assert graders.grade("I don't have that information.", {"grader": "abstains"})[0]
    assert not graders.grade("Parking is free behind the building.", {"grader": "abstains"})[0]


def test_empty_output_does_not_crash():
    for exp in ({"grader": "exact", "value": "x"}, {"grader": "contains_all", "values": ["x"]},
                {"grader": "numeric", "value": 1}, {"grader": "abstains"}):
        assert graders.grade("", exp)[0] is False, exp


def test_unknown_grader_raises_value_error():
    assert raises_value_error(graders.grade, "x", {"grader": "no_such_grader"}) is not None, \
        "a typo in the golden file must raise, not return False (that would blame the system)"


def test_graders_are_pure():
    exp = {"grader": "contains_all", "values": ["A", "b"]}
    before = copy.deepcopy(exp)
    first = graders.grade("a and B", exp)
    second = graders.grade("a and B", exp)
    assert first == second, "same inputs must give the same result"
    assert exp == before, "a grader must not modify the case it is given"


# ---------------------------------------------------------------- golden file

def test_load_example():
    cases = runner.load_golden(EXAMPLE)
    assert len(cases) == 12
    assert all(set(c) >= {"id", "slice", "input", "expected", "source"} for c in cases)
    assert len({c["slice"] for c in cases}) == 3
    assert [c["id"] for c in cases][:2] == ["hours-01", "hours-02"], "file order is kept"


def test_load_skips_blank_lines():
    path = write_jsonl(LINE % "a" + "\n\n" + LINE % "b" + "\n")
    assert [c["id"] for c in runner.load_golden(path)] == ["a", "b"]


def test_load_rejects_missing_field_and_names_the_line():
    path = write_jsonl(LINE % "a" + "\n" + '{"id": "b", "slice": "s", "input": "q", "expected": {}}\n')
    msg = raises_value_error(runner.load_golden, path)
    assert msg is not None, "a case without `source` must be rejected at load time"
    assert "2" in msg, "the message should say which line"


def test_load_rejects_duplicate_id():
    path = write_jsonl(LINE % "a" + "\n" + LINE % "a" + "\n")
    assert raises_value_error(runner.load_golden, path) is not None, "two cases with one id must be rejected"


def test_load_rejects_invalid_json():
    path = write_jsonl(LINE % "a" + "\n{not json}\n")
    assert raises_value_error(runner.load_golden, path) is not None


# ---------------------------------------------------------------- one case

def test_pass_on_first_try_calls_the_system_once():
    system = Scripted("yes")
    r = runner.run_case(case(), system)
    assert r["status"] == "pass_first"
    assert len(system.calls) == 1, "a passing case must not be asked again: retries cost money"
    assert r["id"] == "c1" and r["slice"] == "s"


def test_system_sees_the_input_and_nothing_else():
    system = Scripted("yes")
    c = case()
    runner.run_case(c, system)
    assert system.calls[0] == ((c["input"],), {}), \
        "the system gets the input string only; handing it `expected` would leak the answer"


def test_retry_changes_final_but_not_pass_first():
    r = runner.run_case(case(), Scripted("no", "yes"))
    assert r["status"] == "pass_retry"
    row = runner.summarize([r])["s"]
    assert approx(row["pass_first"], 0.0), "passing on the retry is not passing first time"
    assert approx(row["final"], 1.0)


def test_without_retries_final_equals_pass_first():
    r = runner.run_case(case(), Scripted("no", "yes"), max_attempts=1)
    assert r["status"] == "fail"
    row = runner.summarize([r])["s"]
    assert approx(row["pass_first"], 0.0) and approx(row["final"], 0.0)


def test_model_failure_uses_all_attempts_and_keeps_reasons():
    system = Scripted("no")
    r = runner.run_case(case(), system, max_attempts=3)
    assert r["status"] == "fail"
    assert len(system.calls) == 3
    assert [a["kind"] for a in r["attempts"]] == ["graded"] * 3
    first = r["attempts"][0]
    assert first["passed"] is False and first["output"] == "no"
    assert first["reason"].strip(), "keep the first attempt's failure reason"


def test_infra_error_is_not_a_model_failure():
    """The call timed out once, then the system answered correctly, first time it was heard."""
    system = Scripted(TimeoutError("30 s"), "yes")
    r = runner.run_case(case(), system)
    assert r["status"] == "pass_first", "a timeout must not use up the first graded attempt"
    assert [a["kind"] for a in r["attempts"]] == ["infra", "graded"]
    assert "TimeoutError" in r["attempts"][0]["reason"]
    row = runner.summarize([r])["s"]
    assert approx(row["pass_first"], 1.0) and row["infra_error"] == 0


def test_infra_errors_and_model_retries_are_separate_budgets():
    system = Scripted(ConnectionError("503"), "no", ConnectionError("503"), "yes")
    r = runner.run_case(case(), system, max_attempts=2, max_infra_retries=2)
    assert r["status"] == "pass_retry", "two failed calls must not use up the two graded attempts"
    assert [a["kind"] for a in r["attempts"]] == ["infra", "graded", "infra", "graded"]


def test_permanent_infra_error_stops_and_is_excluded_from_rates():
    down = Scripted(ConnectionError("503"))
    dead = runner.run_case(case("dead"), down, max_infra_retries=2)
    assert dead["status"] == "infra_error", "the system never answered: that is not 'fail'"
    assert len(down.calls) == 3, "max_infra_retries=2 means 1 call + 2 retries, then give up"
    ok = runner.run_case(case("ok"), Scripted("yes"))
    row = runner.summarize([ok, dead])["s"]
    assert row["n"] == 2 and row["graded"] == 1 and row["infra_error"] == 1
    assert approx(row["pass_first"], 1.0), "1 of 1 graded, not 1 of 2: the dead case has no verdict"
    assert approx(row["final"], 1.0)


def test_grader_that_raises():
    def boom(output, expected):
        raise RuntimeError("bug in the grader")

    system = Scripted("yes")
    r = runner.run_case(case(), system, grade=boom)
    assert r["status"] == "grader_error", "not 'fail' (the system did nothing wrong), not 'infra_error'"
    assert len(system.calls) == 1, "do not retry: the same grader fails the same way"
    assert "RuntimeError" in r["attempts"][-1]["reason"]

    ok = runner.run_case(case("ok"), Scripted("yes"))
    row = runner.summarize([ok, r])["s"]
    assert row["grader_error"] == 1 and row["graded"] == 1
    assert approx(row["pass_first"], 1.0)


def test_unknown_grader_name_is_a_grader_error_and_the_run_goes_on():
    cases = [case("typo", grader="exactt", value="yes"), case("ok")]
    results = runner.run(cases, Scripted("yes"))
    assert [r["status"] for r in results] == ["grader_error", "pass_first"], \
        "a typo in one case's grader name must not fail that case or stop the next one"


# ---------------------------------------------------------------- summary and table

def test_per_slice_rows_and_all_row():
    results = [
        runner.run_case(case("a1", "a"), Scripted("yes")),
        runner.run_case(case("a2", "a"), Scripted("no")),
        runner.run_case(case("b1", "b"), Scripted("no", "yes")),
    ]
    s = runner.summarize(results)
    assert list(s) == ["a", "b", "ALL"], "slices in order of first appearance, then ALL"
    assert approx(s["a"]["pass_first"], 0.5) and approx(s["a"]["final"], 0.5)
    assert approx(s["b"]["pass_first"], 0.0) and approx(s["b"]["final"], 1.0)
    # ALL is over the 3 cases (1/3 and 2/3), not the mean of the slice rates (0.25 and 0.75).
    assert approx(s["ALL"]["pass_first"], 1 / 3) and approx(s["ALL"]["final"], 2 / 3)
    assert s["ALL"]["n"] == 3


def test_slice_with_no_graded_case_reports_none_not_zero():
    dead = runner.run_case(case("dead", "empty"), Scripted(TimeoutError("30 s")))
    row = runner.summarize([dead])["empty"]
    assert row["n"] == 1 and row["graded"] == 0, "a case that ended in infra_error is not graded"
    assert row["pass_first"] is None and row["final"] is None, \
        "0.0 would say the system failed; the truth is that nothing was measured"
    table = runner.format_table(runner.summarize([dead]))
    assert "n/a" in table


def test_no_results_at_all():
    assert runner.run([], Scripted("yes")) == []
    summary = runner.summarize([])
    assert "ALL" not in summary or summary["ALL"]["pass_first"] is None
    assert isinstance(runner.format_table(summary), str)


def test_table_has_the_columns_and_the_slices():
    results = [runner.run_case(case("a1", "alpha"), Scripted("yes")),
               runner.run_case(case("b1", "beta"), Scripted("no"))]
    table = runner.format_table(runner.summarize(results))
    for word in ("pass@1st", "final", "infra", "alpha", "beta", "ALL"):
        assert word in table, word


def test_results_keep_input_order_and_runs_are_repeatable():
    cases = [case("z"), case("a"), case("m")]
    first = runner.run(cases, Scripted("yes"))
    second = runner.run(cases, Scripted("yes"))
    assert [r["id"] for r in first] == ["z", "a", "m"]
    assert first == second


def test_exit_code():
    passed = runner.run_case(case("p"), Scripted("yes"))
    failed = runner.run_case(case("f"), Scripted("no"))
    dead = runner.run_case(case("d"), Scripted(TimeoutError("30 s")))
    assert runner.exit_code([passed, failed]) == 0, "a model failure is a result, not a broken run"
    assert runner.exit_code([passed, dead]) == 2, "a case with no verdict: this run is not a baseline"


# ---------------------------------------------------------------- end to end

def test_example_end_to_end():
    """The 12 library cases through the fake system. Your table must match SPEC.md §7."""
    from fake_system import FakeLibraryAssistant

    results = runner.run(runner.load_golden(EXAMPLE), FakeLibraryAssistant())
    status = {r["id"]: r["status"] for r in results}
    not_clean = {k: v for k, v in status.items() if v != "pass_first"}
    # rules-03 timed out once and then answered correctly, so it is NOT in this list.
    assert not_clean == {"hours-03": "fail", "rules-02": "pass_retry",
                         "oos-02": "infra_error", "oos-03": "fail"}, not_clean
    s = runner.summarize(results)
    assert approx(s["hours"]["pass_first"], 3 / 4) and approx(s["hours"]["final"], 3 / 4)
    assert approx(s["rules"]["pass_first"], 4 / 5) and approx(s["rules"]["final"], 1.0)
    assert s["out_of_scope"]["graded"] == 2 and s["out_of_scope"]["infra_error"] == 1
    assert approx(s["out_of_scope"]["pass_first"], 1 / 2)
    assert approx(s["ALL"]["pass_first"], 8 / 11) and approx(s["ALL"]["final"], 9 / 11)
    assert runner.exit_code(results) == 2


# ---------------------------------------------------------------- run without pytest

def main():
    tests = [(name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn)]
    print(f"testing runner.py and graders.py: {len(tests)} checks")
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  [ok ] {name}")
        except Exception as e:  # an AssertionError, or a crash inside the code under test
            failed += 1
            where = traceback.extract_tb(e.__traceback__)[-1]
            print(f"  [FAIL] {name}\n         {type(e).__name__}: {e} (line {where.lineno} of {os.path.basename(where.filename)})")
    print("\nALL PASS" if not failed else f"\n{failed} failed. Fix and rerun.")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
