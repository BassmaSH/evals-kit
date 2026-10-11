# evals-kit, slice 1 — the contract

A small tool that sends a set of questions with known answers (a *golden set*) through any system, grades
each output with code, and reports per slice how often the system was right. Generic: nothing in it knows
what the system is about. Python, standard library only.

**Written by hand:** `graders.py` and `runner.py` (the README's honest note says which functions were delegated).
**Boilerplate, generated with an assistant:** `fake_system.py`, `examples/`, `test_runner.py`, and this contract.

Every rule below is tagged **[CHOICE]** (a design decision: another option exists, and you should be able to
say why this one) or **[CONVENTION]** (it only has to be the same everywhere; the tests pin it).

## 1. The golden file

One JSON object per line (`.jsonl`), five required fields:

| field | type | meaning |
|---|---|---|
| `id` | string | unique in the file; how two runs are compared case by case |
| `slice` | string | the group the case is reported under |
| `input` | string | what is sent to the system, and the only thing sent |
| `expected` | object | how to grade: `{"grader": "<name>", ...arguments}` |
| `source` | string | where the expected answer comes from (document and section, table row, or "none: …") |

- **[CHOICE]** `source` is required. An expected answer that cannot be traced cannot be defended.
- **[CHOICE]** `expected` names its own grader, per case. The alternative is one grader per slice: fewer
  words in the file, but a slice then cannot mix a number check and an abstention check.
- **[CHOICE]** `load_golden` validates and raises `ValueError` (missing field, duplicate id, invalid JSON),
  naming the line. A bad case is caught before the run, never skipped silently.
- **[CONVENTION]** JSONL; blank lines ignored; file order kept; the slice name `ALL` is reserved.

## 2. Graders (`graders.py`)

```
grade(output: str, expected: dict) -> (passed: bool, reason: str)
```

- **[CHOICE]** A grader is a pure function: no network, file, clock, randomness or model. It can be tested
  alone, in both directions (right answers pass, wrong answers fail), and gives the same verdict on every run.
- **[CHOICE]** It always returns a reason. A failure without a reason has to be rerun to be understood.
- **[CHOICE]** An unknown grader name **raises** `ValueError`. Returning `False` would blame the system for
  a typo in the golden file.
- **[CHOICE]** Text is compared after `normalize`: lower-case, runs of whitespace collapsed. Nothing more
  (no punctuation stripping): every extra rule is another way for a wrong answer to match.

| name | arguments in `expected` | passes when | known limit |
|---|---|---|---|
| `exact` | `value` | the whole output equals `value` | fails free text; for constrained outputs only |
| `contains_all` | `values` | every value is in the output | says nothing about what else is in the output |
| `contains_none` | `values` | no value is in the output | an empty output passes |
| `numeric` | `value`, `tol` (default 0) | some number in the output is within `tol` of `value` | any number can match; `10:00` reads as 10 and 0 |
| `abstains` | — | the output contains a refusal phrase from a fixed list | English only; "I don't know, but probably…" passes |

**[CONVENTION]** the five names and their argument names. **[CHOICE]** which five: enough for facts, numbers,
forbidden content and abstention. Anything about meaning is left to the judge (slice 2).

## 3. The runner (`runner.py`)

A *system under test* is any callable `system(input: str) -> str`. It may raise.

For each case, repeat until a status is reached:

1. Call `system(case["input"])`.
   If it raises (any `Exception`): record an `infra` attempt. If this case has now had more than
   `max_infra_retries` failed calls, status = `infra_error`. Otherwise go back to 1.
2. Call `grade(output, case["expected"])`.
   If the grader raises: record a `grader_error` attempt, status = `grader_error`, stop. No retry.
3. Record a `graded` attempt. Passed: status = `pass_first` if this was the first graded attempt, else
   `pass_retry`. Failed and `max_attempts` graded attempts used: status = `fail`. Otherwise go back to 1.

| status | meaning | counts in the pass rates |
|---|---|---|
| `pass_first` | first graded answer passed | yes |
| `pass_retry` | a later graded answer passed | yes |
| `fail` | the system answered `max_attempts` times, never correctly: a **model failure** | yes |
| `infra_error` | the system never produced an answer to grade | no |
| `grader_error` | the grader crashed: a bug in the eval | no |

- **[CHOICE]** Two budgets. A failed call does not use up a graded attempt, so a timeout followed by a
  correct answer is `pass_first`. With one shared counter, pass@1st would move with the network.
- **[CHOICE]** Any exception from the system is an infra error. A model failure is defined narrowly: there
  was an output and the grader said no. The alternative (a dedicated exception type, everything else crashes
  the run) is stricter but loses the whole run to one bad case.
- **[CHOICE]** A grader error is not retried (a pure function fails the same way) and is neither a model
  failure nor an infra error: the system did nothing wrong, and neither did the network.
- **[CHOICE]** Stop at the first pass. More calls cost money and cannot improve the verdict.
- **[CHOICE]** Every attempt is kept, with its output and reason, including the ones a retry later hid.
- **[CHOICE]** `grade` is a parameter of `run_case` with the real grader as default, so a test can pass its own.
- **[CONVENTION]** Defaults `max_attempts=2`, `max_infra_retries=2`; the status names; no waiting between retries.

Result of one case: `{"id", "slice", "status", "attempts": [{"kind", "output", "passed", "reason"}, …]}`
with `kind` in `graded` / `infra` / `grader_error`; `output` is `None` for `infra`; `passed` is `None` unless
`graded`; an `infra` or `grader_error` reason starts with the exception's class name.

## 4. Metrics and the table

Per slice, and for `ALL`:

| key | value |
|---|---|
| `n` | cases in the slice |
| `graded` | cases whose status is `pass_first`, `pass_retry` or `fail` |
| `pass_first` | `pass_first` cases ÷ `graded` — pass@1st |
| `final` | (`pass_first` + `pass_retry`) cases ÷ `graded` |
| `infra_error`, `grader_error` | counts of cases with that status |

- **[CHOICE]** The denominator is `graded`, not `n`. "We could not ask" is not "it answered wrong".
- **[CHOICE]** `graded == 0` gives `None` (printed `n/a`), never `0.0`. Zero would claim a failure nobody measured.
- **[CHOICE]** Both rates are reported, pass@1st first. `final` is the system with its safety net; pass@1st
  is the system. The gap between them is the cost of the retry (calls, latency) and what it may be hiding.
- **[CHOICE]** Per slice, because the total hides which kind of case fails. `ALL` is computed over cases,
  not as the mean of the slice rates, so a 3-case slice does not weigh as much as a 30-case one.
- **[CHOICE]** `exit_code`: `0` when every case got a verdict, `2` when any is `infra_error` or
  `grader_error` (the run is not a baseline). A model failure does not change the exit code: a finished run
  that reports 60 % has done its job, and whether 60 % is acceptable is a separate decision.
- **[CONVENTION]** Markdown table; columns `slice | n | graded | pass@1st | final | infra | grader_err`;
  slices in order of first appearance, `ALL` last; rates as percentages with one decimal.

## 5. What the tests call

```
graders.grade(output, expected) -> (bool, str)

runner.load_golden(path) -> list[dict]
runner.run_case(case, system, grade=grade, max_attempts=2, max_infra_retries=2) -> dict
runner.run(cases, system, grade=grade, max_attempts=2, max_infra_retries=2) -> list[dict]
runner.summarize(results) -> dict[str, dict]        # slice name -> row of §4, plus "ALL" when there are results
runner.format_table(summary) -> str
runner.exit_code(results) -> int
```

A `__main__` that runs `examples/golden_example.jsonl` through `fake_system.FakeLibraryAssistant()` and
prints the table is boilerplate. The CLI proper is slice 2.

## 6. Not in slice 1

A judge model, latency and cost per call, waiting between retries, several trials per case with a standard
error, a committed baseline and a comparison between two runs, a pass threshold (a gate). Each one is a
question an interviewer can ask as "what is missing?".

## 7. Tests: command and output

The test file runs two ways with the same 32 checks: as a script (no dependency) or under pytest.

```
$ python test_runner.py
testing runner.py and graders.py: 32 checks
  ...
ALL PASS
```

The example run (12 library cases, the fake system, defaults):

```
$ python runner.py
| slice | n | graded | pass@1st | final | infra | grader_err |
|---|---|---|---|---|---|---|
| hours | 4 | 4 | 75.0% | 75.0% | 0 | 0 |
| rules | 5 | 5 | 80.0% | 100.0% | 0 | 0 |
| out_of_scope | 3 | 2 | 50.0% | 50.0% | 1 | 0 |
| ALL | 12 | 11 | 72.7% | 81.8% | 1 | 0 |
exit 2
```

Two things to read in it: one `rules` case timed out on its first call and still counts as a first-try
pass, because its first graded answer was right. `out_of_scope` is 50 % of 2, not 33 % of 3: the third
case got no answer at all, which is why the exit code is 2.
