# evals-kit slice 1 — the runner. Contract: SPEC.md §3–5.
# Why two budgets (my answer, Oct 5): a crashed call is the network's fault, a wrong answer is the
# model's. With two counters, a timeout followed by a correct answer is pass_first; with one shared
# counter it would be pass_retry, so pass@1st would change with the network and not with the model.
import json
import os
from graders import grade
def load_golden(path):
    with open(path) as f:
        ids = set()
        l = []
        for n,line in enumerate(f,start=1) :
            if line.strip()!="":
                try:
                    j = json.loads(line)
                except json.JSONDecodeError:
                    raise ValueError(f"line {n} not a json")
                missing_key= [i for i in ["id", "slice", "input", "expected", "source"] if i not in j ]
                if len(missing_key)>0:
                    raise ValueError(f"line {n} missing key {missing_key}")
                if j['id'] in ids:
                    raise ValueError(f"line {n} duplicate id")
                if j['slice'] == "ALL":
                    raise ValueError("slice name ALL reserved")
                ids.add(j['id'])
                l.append(j)
    return l

def run_case(case, system, grade=grade, max_attempts=2, max_infra_retries=2):
    attempts = []
    infra_retries = 0
    grades = 0
    while True:
        try: 
            output = system(case["input"])
        except Exception as e: 
            infra_retries+=1
            attempts.append({"kind":"infra", "output":None, "passed":None, "reason":f"{type(e).__name__}: {e}"})
            if infra_retries>max_infra_retries:
                return {"id":case["id"],"slice":case["slice"],"status":"infra_error","attempts": attempts}
            continue
        try:
            passed, reason = grade(output, case["expected"])
        except Exception as e:
            attempts.append({"kind":"grader_error", "output":output, "passed":None, "reason":f"{type(e).__name__}: {e}"})
            return {"id":case["id"],"slice":case["slice"],"status":"grader_error","attempts": attempts} 
        grades +=1
        attempts.append({"kind":"graded", "output":output, "passed":passed, "reason":reason})
        if passed:
            status = "pass_first" if grades==1 else "pass_retry"
            return {"id":case["id"],"slice":case["slice"],"status":status,"attempts": attempts}  
        if grades == max_attempts:
            status = "fail"
            return {"id":case["id"],"slice":case["slice"],"status":status,"attempts": attempts}  



def run(cases, system, grade=grade, max_attempts=2, max_infra_retries=2):
    res = []
    for case in cases:
        runs = run_case(case,system,grade,max_attempts,max_infra_retries)
        res.append(runs)
    return res

def row(l):
    graded = len([res for res in l if res["status"] in ['pass_first', 'pass_retry','fail']])
    pass_first = len([res for res in l if res["status"] == 'pass_first'])
    pass_retry = len([res for res in l if res["status"] == 'pass_retry'])
    infra_error = len([res for res in l if res["status"] == 'infra_error'])
    grader_error = len([res for res in l if res["status"] == 'grader_error'])
    final_p = (pass_first+pass_retry)/graded if graded>0 else None
    pass_first_p = pass_first/graded if graded>0 else None
    return {"n": len(l), "graded": graded, "pass_first": pass_first_p, "final": final_p, "infra_error": infra_error, "grader_error": grader_error}


def summarize(results):
    slices = {}
    for res in results:
        if res["slice"] not in slices:
            slices[res["slice"]] = []
        slices[res["slice"]].append(res)
    summary = {sl:row(l) for sl,l in slices.items()}
    if len(results)>0:
        summary["ALL"] = row(results)
    return summary


def format_table(summary):
    lines = ["| slice | n | graded | pass@1st | final | infra | grader_err |",
             "|---|---|---|---|---|---|---|"]
    for name, r in summary.items():
        pass_first_p = "n/a" if r['pass_first'] is None else f"{r['pass_first']*100:.1f}%"
        final_p = "n/a" if r['final'] is None else f"{r['final']*100:.1f}%"
        lines.append(f"| {name} | {r['n']} | {r['graded']} | {pass_first_p} | {final_p} | {r['infra_error']} | {r['grader_error']} |")
    return "\n".join(lines)


def exit_code(results):
    if any(res["status"] in ["infra_error", "grader_error"] for res in results):
        return 2
    return 0


if __name__ == "__main__":
    from fake_system import FakeLibraryAssistant
    golden_set = load_golden(os.path.join(os.path.dirname(__file__), "examples", "golden_example.jsonl"))
    results = run(golden_set, FakeLibraryAssistant())
    print(format_table(summarize(results)))
    code = exit_code(results)
    print("exit", code)
    raise SystemExit(code)
