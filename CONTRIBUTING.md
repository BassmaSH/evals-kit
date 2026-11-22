# Contributing

Eleven guidelines for the code in this repo, and how each one is checked. They follow Google's
Python Style Guide and "Good Enough Practices in Scientific Computing" (Wilson et al., 2017).

## Before you push

Python 3.12 or later. The kit itself has no dependency; the two tools below are only for checking.

```bash
pip install ruff==0.17.5 pytest
ruff format .            # rewrites the files in the agreed style
ruff check .             # reports what breaks a rule
python test_runner.py    # 39 checks, no network, no API key
pytest -q                # the same 39 checks under pytest
python runner.py         # the example: must print the table of SPEC.md §7 and "exit 2"
```

The same steps run on every push (`.github/workflows/check.yml`), together with `pip install .`
and an import from outside the repo. The settings are in `pyproject.toml`.

## The guidelines

| # | guideline | checked by |
|---|---|---|
| 1 | One job per function, about 40 lines at most | ruff: 40 statements, 10 branches, 6 arguments |
| 2 | A choice between named things is a table, not an `if` chain (`GRADERS`) | review |
| 3 | Nothing runs at import: what a script does sits under `if __name__ == "__main__":` | review |
| 4 | Each piece of logic lives in one place | review |
| 5 | A file opens with what it does and which section of `SPEC.md` is its contract | ruff: a docstring is required |
| 6 | Comments say why, never what | review |
| 7 | Every rule in `SPEC.md` has a test, and a test says in its message why the rule exists | review; the tests run on every push |
| 8 | A formatter and a linter decide style | ruff, 100 characters |
| 9 | A grader is a pure function: no network, file, clock, randomness or model | `test_graders_are_pure`; review |
| 10 | Standard library only | review; `dependencies = []` in `pyproject.toml` |
| 11 | Type hints on every function; a docstring with `Args:` and `Returns:` where the names do not say it | ruff |

"Review" means a person reads the change against the guideline: no tool checks it.

## Where things are

| file | role |
|---|---|
| `SPEC.md` | the contract: what each function must do, and why each choice was made |
| `graders.py` | the five graders and the table `GRADERS` |
| `runner.py` | reading the golden file, running the cases, the table and the exit code |
| `test_runner.py` | the checks, as a script or under pytest: plain asserts, no pytest feature |
| `fake_system.py`, `examples/` | a scripted assistant and 12 cases, so that the runner runs with no model |

`pip install .` installs `graders` and `runner` only.

## Changing behaviour

`SPEC.md` comes first. A change to what a grader accepts, to a status, or to a number in the table
is a change to the contract, so it needs three things in the same commit:

- the rule in `SPEC.md`, tagged **[CHOICE]** with the reason, or **[CONVENTION]**;
- a test that fails before the change and passes after it;
- if the example table changes, the new table in `SPEC.md` §7 and in the README.

A behaviour that is known and kept goes in the "known limit" column of `SPEC.md` §2, with a test
that pins it.

Keep style changes (formatter, renames, type hints) in their own commit, apart from commits that
change behaviour.

## Adding a grader

1. Write `grade_<name>(output, expected) -> (passed, reason)` in `graders.py`. The output it
   receives is already normalized. It always returns a reason, and it raises `ValueError` when the
   case itself is wrong.
2. Add one entry to `GRADERS`. `grade`, its error message and the name check in `load_golden`
   all read the table.
3. Add a row to the table in `SPEC.md` §2, with the known limit.
4. Add a test in both directions: an answer that must pass and one that must fail.

An eval with graders of its own does not need to change this repo: it passes its `grade` function
to `run`, and that function's names to `load_golden(path, grader_names=...)`.
