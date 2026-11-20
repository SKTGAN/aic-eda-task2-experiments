"""Exercise Task 2 scoring and candidate selection with synthetic results."""

from itertools import islice
from statistics import mean


SEEDS = (1001, 1002, 1003)
MAX_EVALUATIONS = 10
FAILURE_SCORE = -100.0


def seed_score(slack, reference):
    if slack is None:
        return FAILURE_SCORE

    wns, tns = slack
    ref_wns, ref_tns = reference
    wns_improvement = 1 - max(0.0, -wns) / ref_wns
    tns_improvement = 1 - max(0.0, -tns) / ref_tns
    return max(FAILURE_SCORE, 100 * (0.4 * wns_improvement + 0.6 * tns_improvement))


def training_score(results, references):
    expected = {(case, seed) for case in references for seed in SEEDS}
    if results.keys() != expected:
        raise ValueError("Expected one result or explicit failure per case and seed")

    return mean(
        mean(seed_score(results[case, seed], reference) for seed in SEEDS)
        for case, reference in references.items()
    )


def select_candidate(candidates, evaluate, references):
    best_id = None
    best_score = float("-inf")
    for attempt, candidate_id in enumerate(islice(candidates, MAX_EVALUATIONS), 1):
        results = evaluate(candidate_id)
        if results is None:
            print(f"{attempt:2d}/{MAX_EVALUATIONS} {candidate_id}: rejected")
            continue

        score = training_score(results, references)
        print(f"{attempt:2d}/{MAX_EVALUATIONS} {candidate_id}: {score:+.2f}")
        if score > best_score:
            best_id, best_score = candidate_id, score

    return best_id, best_score


def main():
    references = {"case-a": (1.0, 10.0), "case-b": (2.0, 15.0), "case-c": (3.0, 25.0)}
    attempts = []

    def mock_evaluate(candidate_id):
        attempts.append(candidate_id)
        if candidate_id == "rejected":
            return None

        wns_ratio, tns_ratio = {
            "initial": (1.0, 1.0),
            "strong-but-one-failure": (0.95, 0.75),
            "steady-improvement": (0.90, 0.85),
            "regression": (1.2, 1.3),
            "over-budget": (0.0, 0.0),
        }[candidate_id]
        results = {
            (case, seed): (-wns_ratio * ref_wns, -tns_ratio * ref_tns)
            for case, (ref_wns, ref_tns) in references.items()
            for seed in SEEDS
        }
        if candidate_id == "strong-but-one-failure":
            results["case-b", 1002] = None
        return results

    assert seed_score((0.01, 0.0), (1.0, 10.0)) == 100.0
    assert seed_score((-10.0, -100.0), (1.0, 10.0)) == FAILURE_SCORE
    assert seed_score(None, (1.0, 10.0)) == FAILURE_SCORE

    candidates = ["initial", "rejected", "strong-but-one-failure", "steady-improvement"]
    candidates.extend(["regression"] * 6 + ["over-budget"])
    print("Synthetic evaluator results (no EDA execution or model calls)")
    candidate_id, score = select_candidate(candidates, mock_evaluate, references)
    assert attempts == candidates[:MAX_EVALUATIONS]
    assert candidate_id == "steady-improvement" and abs(score - 13.0) < 1e-9
    print(f"Selected {candidate_id} at {score:+.2f}; {len(attempts)} attempts used")


if __name__ == "__main__":
    main()
