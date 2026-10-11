"""evals-kit slice 1 — graders. Contract: SPEC.md §2. Written from a blank file, Sat Oct 3.

grade(output: str, expected: dict) -> (passed: bool, reason: str)
Check: python test_runner.py   (the first ten lines are the grader tests)
"""
import re


refusal_list = ["i don't know", "i don't have", "i do not know", "i do not have", "i can't help with","i cannot help with"]
def normalize(text):
    return " ".join(str(text).lower().split())

def grade(output : str,expected: dict):
    output = normalize(output)
    if expected["grader"] in ["exact","contains_all","contains_none","numeric","abstains"]:
        if expected["grader"] == "exact":
            if normalize(expected["value"]) == output:
                return True, "ok"
            else:
                return False, f"expected exactly {expected["value"]}, got {output}"
        if expected["grader"] == "contains_all":
            out_of_res = [normalize(i) for i in expected["values"] if normalize(i) not in  output ]
            if len(out_of_res)==0:
                return True, "ok"
            else: 
                return False, f"expected to contain all of {expected["values"]}, didn't contain {out_of_res}"
        if expected["grader"] == "contains_none":
            in_res = [normalize(i) for i in expected["values"] if normalize(i) in  output ]
            if len(in_res)==0:
                return True, "ok"
            else:
                return False, f"expected to contain none of {expected["values"]}, contained {in_res}"
        if expected["grader"] == "numeric":
            numbers = re.findall(r"-?\d+(?:\.\d+)?", output.replace(",",""))
            numbers = [float(i) for i in numbers]
            tol = float(expected.get("tol", 0))
            for n in numbers:
                if abs(expected["value"] -  n) <= tol+1e-9:
                    return True, "ok"
            return False, f"expected to contain {expected["value"]} with tolerance {tol} but was equal to {output}"
        if expected["grader"] == "abstains":
            if any(i in output for i in refusal_list):
                return True, "ok"
            else:
                return False, f"output \"{output}\" has no sentence from refusal list: {refusal_list}"
    else:
        raise ValueError(f"grader {expected["grader"]} not one of expected values: {["exact","contains_all","contains_none","numeric","abstains"]} ")