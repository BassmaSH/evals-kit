# evals-kit

## What it is

A small generic evals setup written by hand to wrap my head around more advanced frameworks I am 
producing with a coding assistant. Also a first step into exploring reusable eval kits for common
use cases.

**What goes in:** an agent or system being tested on its outputs, and a golden set (a file of 
questions with expectations on answers).

**What comes out:** a results table, with one line per slice (type of request), and an exit code.

**Who it is for:** someone testing their agent or system on a golden set they built, with graders
that check for an expected word or words, a number, or an abstention. You run it after building,
and rerun after any update to monitor changes in performance.

**Where it stands:** first slice (graders and runner). It has only been run on a fake assistant
with scripted answers so far, not on a real model.

## The table it prints

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

A slice is a type of question. Questions are separated in slices to account for different precision targets
and volumes for different types of questions hidden by the average would hide that.

`graded` can be smaller than `n`: on the `out_of_scope` line one call ended in an infra error (the
call crashed, so there was no answer). It is left out of the rate because otherwise it would
incorrectly grade the system as failing on that input.

`pass@1st` and `final` measure success at the first try versus success after the allowed number of
retries.

Exit 2 means an infra error or a grader error: if we didn't run 12 out of 12, it's not a complete test.

## Choices 

**Both rates are reported, first try before final.** They measure success at the first try versus
success after the allowed number of retries. If the system is always succeeding at the second
try, the final rate can't show whether a change to the prompt helped. 

**Rates are over the cases that were graded, and `n/a` when none were.** A case whose call crashed
is left out, because otherwise it would incorrectly grade the system as failing on that input. When
nothing in a slice was graded the table says `n/a`.

**Two separate budgets: one for crashed calls, one for wrong answers.** A call that crashes is tried
again without using up one of the graded attempts, so a timeout followed by a right answer still
counts as a pass at the first try.

**One line per slice.** A slice is a type of question. We might have different precision targets
and volumes for different types of questions, and the average would hide that. 

## What is missing

judge model, latency and cost per call, baseline, pass threshold.

## How to run

Python 3.12 or later, standard library only.

```bash
python test_runner.py   # 32 checks on the graders and the runner
python runner.py        # the example: 12 cases through a fake assistant
```

To test your own system: write a function that takes a question (a string) and returns an answer (a
string), write your cases in the format of `examples/golden_example.jsonl`, and call
`run(load_golden(path), your_function)`.


## Honest note

Built as self-study. The contract (`SPEC.md`), the tests, the fake assistant and the example cases
were generated with Claude; `graders.py` and `runner.py` are written from that contract with
the tests as the check. 
