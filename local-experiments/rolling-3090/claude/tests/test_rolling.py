"""Replay and acceptance tests for the evidence ledger, the rolling plan and the self-tests.

    python3 -I -B -m unittest discover -s tests -p "test_rolling.py" -v

Each decision test builds the ledger from a real prefix of an archived run (official cells, organizer
partition diagnostics, accepted sources and recorded lineage) and the branching search control's
recorded choice for that prefix. Outcomes after a changed decision are unknown: these tests check
decisions and evidence, never a physical score. Nothing here calls a model, the bridge or a GPU.
"""

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import replay  # noqa: E402  (also puts the Agent directory on sys.path)
import ledger as L  # noqa: E402
import rolling_plan as P  # noqa: E402
import self_test as T  # noqa: E402

ORIGINAL, EVIDENCE = replay.RUNS["claude-original"], replay.RUNS["ours-new"]


class MeasuredFeedback(unittest.TestCase):
    def test_orientation_carried_mixed_opening_gets_one_control_from_the_official_parent(self):
        evidence = replay.ledger_for(ORIGINAL[:2])
        start, opening = evidence["entries"][:2]
        opening["pairs"] = {}
        for index, key in enumerate(evidence["schedule"]):
            base, row = start["cells"][key], opening["cells"][key]
            change = 1.0 if index % 2 == 0 else 0.0
            row.update(vs_start=change, score=base["score"] + 4 * change)
        opening["score"] = start["score"] + 2.0
        parent = opening["candidate_id"]
        baseline = (parent, "decoder_only", {"reason": "extend_best", "component": "decoder", "incumbent_id": parent})
        plan = P.plan_next(evidence, baseline, 6, 8)
        control = plan["choice"]
        self.assertEqual((control["kind"], control["parent_candidate"]), ("orientation_control", start["candidate_id"]))
        packet = P.generation_packet(plan, control, evidence)
        self.assertEqual(len(packet["experiment"]["opening_evidence"]), len(evidence["schedule"]))
        self.assertIn("distinguishes", packet["experiment"])

    def test_published_deep_cuda_error_survives_wrapper_and_score_stays_intact(self):
        import tempfile
        import paired_feedback as paired
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rid = "e-test"
            stage = root / rid / "cells/x/10/result/retained_artifacts/algorithm/30_placement/stages/02_global_place"
            stage.mkdir(parents=True)
            (stage / "run.log").write_text("RuntimeError: No CUDA GPUs are available\n")
            row = {"case": "x", "seed": 10, "status": "penalized", "score": -100,
                   "diagnostics": [{"source": "stage.log", "excerpt": "command failed with code 1"}]}
            failure = paired.published_failure({"request_id": rid, "artifacts_dir": str(root / rid)}, row, root)
            self.assertEqual(failure["kind"], "runtime_environment")
            self.assertIn("02_global_place", failure["diagnostics"][0]["source"])
            self.assertEqual(row["score"], -100)
            (stage / "run.log").write_text("GPU is in use\n")
            self.assertEqual(paired.published_failure({"request_id": rid, "artifacts_dir": str(root / rid)},
                                                     row, root)["kind"], "physical_penalty")

    def test_unprotected_measured_designs_have_explicit_parent_floors(self):
        data = replay.ledger_for(ORIGINAL[:2])
        tol = L.tolerances(data)
        review = P.review_anchor(data, "S", tol)
        contract = P.make_contract(review, "decoder", tol)
        self.assertEqual({r["case"] for r in contract["protect"]}, set(tol) - {contract["target"]["case"]})
        self.assertTrue(all(r["strength"] == "parent_floor" for r in contract["protect"]))
    def test_generation_feedback_keeps_floor_timing_terms_and_tier_orientation(self):
        terms = {"wns_points": 2, "tns_points": -25, "score_floor_delta_points": 18}
        row = {"case": "example", "seed": "1", "score": -100, "raw_score": -118}
        pair = {"case": "example", "seed": "1", "score_delta": -5, "score_delta_terms": terms,
                "assignment": {"changed_fraction": 1.0, "flip_adjusted_changed_fraction": 0.0}}
        trial = P.compact_trial({"cells": [row], "parent_comparison": {"cells": [pair]}})
        paired = trial["parent_comparison"]["cells"][0]
        self.assertEqual(trial["cells"][0]["raw_score_before_floor"], -118)
        self.assertEqual(paired["score_delta_terms"], terms)
        self.assertEqual(paired["labels_changed_fraction"], 1)
        self.assertEqual(paired["grouping_changed_fraction_up_to_tier_exchange"], 0)


def considered(rows):
    return {(f["loss"], f["decoder"]) for f in (L.factor_ids(row["source"]) for row in rows)}


def plan_after(run, rounds, remaining=None, baseline=None, attempts=None, extra_rows=()):
    rows = list(replay.RUNS[run][:rounds]) + list(extra_rows)
    evidence = replay.ledger_for(rows, attempts)
    plan = P.plan_next(evidence, baseline or replay.baseline(run, rounds),
                       10 - len(rows) if remaining is None else remaining, 10, considered(rows))
    return evidence, plan


def shifted(row, request_id, deltas, source=None, attempt=None, partition=None):
    """A copy of a real receipt with per-cell score shifts (a hypothetical outcome for decision tests)."""
    new = copy.deepcopy(row)
    new.update(request_id=request_id, candidate_id="cand-" + request_id)
    for cell in new["cells"]:
        cell["score"] += deltas.get("%s/%s" % (cell["case"], cell["seed"]), 0.0)
    new["score"] = replay.official_score(new["cells"])
    if source is not None:
        new["source"] = source
    if attempt is not None:
        new["attempt"] = attempt
    if partition is not None:
        new["partition"] = partition
    return new


class LedgerFacts(unittest.TestCase):

    def test_exact_factors_follow_the_recorded_lineage(self):
        evidence = replay.ledger_for(ORIGINAL)
        r2, r4, r6 = (L.entry(evidence, label) for label in ("R2", "R4", "R6"))
        self.assertEqual(r4["factors"]["loss"], r2["factors"]["loss"])      # R4 edited only the decoder
        self.assertNotEqual(r6["factors"]["decoder"], r4["factors"]["decoder"])  # R6 is new decoder code
        self.assertEqual(L.contrast(evidence, "R4", "S")["varies"], ["loss", "decoder"])

    def test_round_6_repeats_round_4_without_label_proof(self):
        evidence = replay.ledger_for(ORIGINAL[:6])
        self.assertEqual(L.duplicate_of(evidence, "R6"), {"same_as": "R4", "basis": "timing_only"})
        same = {row["request_id"]: {(cell["case"], cell["seed"]): {"labels": "x" + cell["case"] + cell["seed"],
                                                                   "grouping": "g" + cell["case"] + cell["seed"]}
                                    for cell in row["cells"]} for row in ORIGINAL[:6] if row["round"] in (4, 6)}
        verified = replay.ledger_for(ORIGINAL[:6], fingerprints=same)
        self.assertEqual(L.duplicate_of(verified, "R6"), {"same_as": "R4", "basis": "labels"})

    def test_round_4_gain_over_round_2_is_carried_by_exchanged_dies(self):
        evidence = replay.ledger_for(ORIGINAL[:4])
        result = L.contrast(evidence, "R4", "R2")
        self.assertEqual(L.gain_reading(result), "orientation_carried")
        cells = {(row["case"], row["seed"]): row for row in result["cells"]}
        self.assertEqual(cells["ariane133-ng45", "1001"]["relation"], "exchange")
        self.assertAlmostEqual(result["official_delta"], 5.3272, places=3)
        self.assertGreater(result["orientation_share"], 0.8)

    def test_sensitivity_is_calibrated_per_design(self):
        tol = L.tolerances(replay.ledger_for(ORIGINAL))
        self.assertTrue(all(row["source"] == "calibrated" for row in tol.values()))
        self.assertGreater(tol["ariane133-ng45"]["cell"], 3 * tol["bp-ng45"]["cell"])
        few = L.tolerances(replay.ledger_for(ORIGINAL[:1]))
        self.assertEqual(few["bp_fe-ng45"], {"cell": round(L.DEFAULT_TOLERANCE * 3 ** 0.5, 3),
                                              "case_mean": L.DEFAULT_TOLERANCE, "pairs": 0, "source": "default"})

    def test_start_cells_measured_on_this_host_replace_published_values(self):
        start = L.entry(replay.ledger_for(EVIDENCE[:3]), "S")
        host = sorted("/".join(key) for key, cell in start["cells"].items() if cell["measured_on"] == "this_host")
        self.assertEqual(host, ["ariane133-ng45/1003", "bp-ng45/1001", "bp-ng45/1002", "bp-ng45/1003",
                                "bp_fe-ng45/1002", "bp_fe-ng45/1003"])
        self.assertAlmostEqual(start["cells"]["bp-ng45", "1002"]["score"], -24.4909, places=3)

    def test_without_a_start_reference_the_branching_choice_is_kept(self):
        views = replay.summaries(EVIDENCE[:1])
        start_id = EVIDENCE[0]["attempt"]["parent_id"]
        evidence = L.build_ledger(views, replay.sources(EVIDENCE[:1]), replay.schedule(EVIDENCE),
                                  {"candidate_id": start_id, "feedback": {"score": None, "cells": []}}, replay.INITIAL)
        plan = P.plan_next(evidence, (start_id, "loss_only", {"reason": "complementary_opening_with_first_receipt",
                                                              "component": "loss"}), 9, 10)
        self.assertEqual({key: plan["choice"][key] for key in ("id", "kind", "parent_candidate", "component", "contract")},
                         {"id": "X1", "kind": "edit", "parent_candidate": start_id, "component": "loss", "contract": None})

    def test_degraded_summaries_keep_official_scores(self):
        rows = copy.deepcopy(EVIDENCE[:3])
        for row in rows:
            row["partition"] = {}
        views = replay.summaries(rows)
        start = L.same_host_start(replay.published_start(replay.schedule(rows), rows[0]["attempt"]["parent_id"]), views)
        evidence = L.build_ledger(views, {}, replay.schedule(rows), start, replay.INITIAL)
        self.assertEqual([row["score"] for row in evidence["entries"][1:]], [row["score"] for row in rows])
        self.assertIsNone(L.entry(evidence, "R3")["factors"])
        P.plan_next(evidence, replay.baseline("ours-new", 3), 7, 10)  # still plans, without factors


class ReuseMeasuredControls(unittest.TestCase):
    """Acceptance 1 and 2: controls anywhere in the run are reused; missing ones become suggestions."""

    def test_an_early_removal_is_found_after_many_later_rounds_and_not_resubmitted(self):
        evidence = replay.ledger_for(ORIGINAL)
        controls = {(row["component"], row["origin"]): row for row in L.removal_controls(evidence, "R4")}
        self.assertEqual(controls["decoder", "start"]["entry"], "R2")  # measured in round 2
        r4 = ORIGINAL[3]["candidate_id"]
        plan = P.plan_next(evidence, (r4, "decoder_only", {"reason": "extend_best", "component": "decoder"}),
                           3, 13, considered(ORIGINAL))
        self.assertEqual([option["kind"] for option in plan["options"]], ["edit"])
        packet = P.generation_packet(plan, plan["choice"], evidence)
        self.assertIn("R4-R2", [row["evidence"] for row in packet["comparisons"]])

    def test_the_missing_loss_removal_is_proposed_not_credited(self):
        evidence, plan = plan_after("claude-original", 4)
        choice = plan["choice"]
        self.assertEqual((choice["kind"], choice["parent"], choice["component"]), ("removal", "R4", "loss"))
        self.assertEqual(choice["factors"], {"loss": L.entry(evidence, "S")["factors"]["loss"],
                                             "decoder": L.entry(evidence, "R4")["factors"]["decoder"]})
        self.assertEqual(choice["donors"], {"loss": "S", "decoder": "R4"})
        self.assertIn("if_within_tolerance", choice["decides"])
        self.assertFalse([effect for effect in L.case_effects(evidence) if "R4-S" in effect["evidence"]])
        self.assertFalse(L.contrast(evidence, "R4", "S")["exact"])  # the bundled diff names no single factor

    def test_a_removal_splice_record_needs_no_target(self):
        # Regression: the measurement contract of a removal has no target design.
        _, plan = plan_after("claude-original", 4)
        record = P.splice_hypothesis(plan["choice"])
        self.assertIsNone(plan["choice"]["contract"]["target"])
        self.assertIn("scores within", record["falsifier"])
        self.assertEqual(record["mechanism"], "removal splice: loss from S")

    def test_no_removal_without_a_slot_to_act_on_it(self):
        _, plan = plan_after("claude-original", 4, remaining=1)
        self.assertEqual(plan["choice"]["kind"], "edit")

    def test_removal_outcome_selects_the_next_parent(self):
        removal_source = P.splice_source(replay.INITIAL, ORIGINAL[3]["source"])
        attempt = {"parent_id": ORIGINAL[3]["candidate_id"], "policy_action": "removal",
                   "experiment": {"kind": "removal", "parent": "R4", "component": "loss"}}
        for delta, parent, component in ((-1.0, "R5", "loss"), (-20.0, "R4", "decoder")):
            row = shifted(ORIGINAL[3], "removal", {key: delta for key in
                                                    ["%s/%s" % (c["case"], c["seed"]) for c in ORIGINAL[3]["cells"]]},
                          source=removal_source, attempt=attempt)
            baseline = (ORIGINAL[3]["candidate_id"], "loss_only", {"reason": "extend_best", "component": "loss"})
            _, plan = plan_after("claude-original", 4, baseline=baseline, extra_rows=[row])
            finding = next(item for item in plan["lessons"] if item["finding"] == "removal")
            self.assertEqual((plan["choice"]["parent"], plan["choice"]["component"]), (parent, component), finding)


class InteractionAndProtection(unittest.TestCase):
    """Acceptance 3: no additive reading of AB; a target gain is reported with protected regressions."""

    def test_same_host_factorial_is_antagonistic_and_keeps_the_stronger_singleton(self):
        evidence = replay.ledger_for(replay.factorial_rows())
        squares = L.factorial_squares(evidence)
        self.assertEqual(len(squares), 1)
        square = squares[0]
        self.assertEqual(square["verdict"], "antagonistic")
        self.assertAlmostEqual(square["interaction"], -58.964, places=2)
        self.assertAlmostEqual(square["loss_effect"]["with_P_decoder"], 34.691, places=2)
        self.assertAlmostEqual(square["loss_effect"]["with_AB_decoder"], -24.273, places=2)
        self.assertAlmostEqual(square["decoder_effect"]["with_AB_loss"], -22.085, places=2)
        self.assertEqual(square["arms"][square["keep"]], "R3")  # B, the stronger singleton
        b = replay.factorial_rows()[2]["candidate_id"]
        plan = P.plan_next(evidence, (b, "loss_only", {"reason": "extend_best", "component": "loss"}), 6, 10,
                           considered(replay.factorial_rows()))
        lesson = next(row for row in plan["lessons"] if row["finding"] == "factorial")
        self.assertEqual((lesson["verdict"], lesson["keep"]), ("antagonistic", "R3"))
        self.assertIn("antagonistic_combination", plan["hard"])
        self.assertEqual(plan["choice"]["parent"], "R3")
        self.assertNotIn("merge", [option["kind"] for option in plan["options"]])

    def test_round_4_repair_reports_its_target_gain_and_the_two_protected_regressions(self):
        before = replay.ledger_for(EVIDENCE[:3])
        tol = L.tolerances(before)
        contract = P.make_contract(P.review_anchor(before, "R3", tol), "loss", tol)
        self.assertEqual(contract["target"]["case"], "bp_fe-ng45")
        self.assertEqual(sorted(rule["case"] for rule in contract["protect"]), ["ariane133-ng45", "bp-ng45"])
        verdict = P.judge(replay.ledger_for(EVIDENCE[:4]), contract, "R4")
        self.assertTrue(verdict["target"]["met"])
        target = {row["cell"]: row["delta"] for row in verdict["target"]["cells"]}
        self.assertAlmostEqual(target["bp_fe-ng45/1001"], 16.4217, places=3)
        regressions = {row["cell"]: row["delta"] for row in verdict["protected_regressions"]}
        self.assertAlmostEqual(regressions["ariane133-ng45/1002"], -16.8586, places=3)
        self.assertAlmostEqual(regressions["ariane133-ng45/1003"], -30.6802, places=3)
        self.assertAlmostEqual(verdict["official_delta"], -1.4819, places=3)

    def test_the_contract_is_stored_with_the_attempt_and_judged_next_round(self):
        before = replay.ledger_for(EVIDENCE[:3])
        tol = L.tolerances(before)
        contract = P.make_contract(P.review_anchor(before, "R3", tol), "loss", tol)
        attempts = {EVIDENCE[3]["request_id"]: {"experiment": {"kind": "edit", "parent": "R3", "contract": contract}}}
        _, plan = plan_after("ours-new", 4, attempts=attempts)
        verdict = next(row for row in plan["lessons"] if row["finding"] == "plan_verdict")
        self.assertEqual((verdict["target"]["case"], verdict["anchor"]), ("bp_fe-ng45", "R3"))

    def test_a_weak_design_gets_a_transplant_from_a_low_scoring_candidate(self):
        # Hypothetical receipts on the real ours-new matrix: X improves bp_fe and ariane through its loss
        # but leaves bp's labels alone; Y scores worse overall, yet its decoder lifts bp on all seeds.
        base = EVIDENCE[1]
        start = replay.ledger_for(EVIDENCE[:2])["entries"][0]
        keys = ["%s/%s" % (c["case"], c["seed"]) for c in base["cells"]]
        def to(targets):
            return {key: targets[key] - next(c["score"] for c in base["cells"] if "%s/%s" % (c["case"], c["seed"]) == key)
                    for key in keys}
        on_start = {key: start["cells"][tuple(key.split("/"))]["score"] for key in keys}
        x_scores = {key: on_start[key] + (0.0 if key.startswith("bp-") else 20.0) for key in keys}
        y_scores = {key: on_start[key] + (6.0 if key.startswith("bp-") else -30.0) for key in keys}
        x_part = {key: {"partition_assignment_changed_count": 0 if key.startswith("bp-") else 300,
                        "partition_assignment_changed_fraction": 0.0 if key.startswith("bp-") else 0.01} for key in keys}
        y_part = {key: {"partition_assignment_changed_count": 300, "partition_assignment_changed_fraction": 0.01}
                  for key in keys}
        loss = replay.INITIAL.replace("F.logsigmoid(-negative_scores).sum()", "0.9 * F.logsigmoid(-negative_scores).sum()")
        decoder = replay.INITIAL.replace("    return reference_global_two_way(",
                                         "    return 0 + reference_global_two_way(")
        start_id = base["attempt"]["parent_id"]
        x = shifted(base, "x", to(x_scores), source=loss, partition=x_part,
                    attempt={"parent_id": start_id, "changed_components": {"loss": {}}})
        y = shifted(base, "y", to(y_scores), source=decoder, partition=y_part,
                    attempt={"parent_id": start_id, "changed_components": {"decoder": {}}})
        evidence = replay.ledger_for([x, y])
        plan = P.plan_next(evidence, (x["candidate_id"], "decoder_only", {"reason": "extend_best",
                                                                          "component": "decoder"}), 8, 10,
                           considered([x, y]))
        choice = plan["choice"]
        self.assertEqual(plan["review"]["weak"]["case"], "bp-ng45")
        self.assertEqual((choice["kind"], choice["parent"], choice["component"]), ("transplant", "R1", "decoder"))
        self.assertEqual(choice["donors"], {"loss": "R1", "decoder": "R2"})
        self.assertEqual(choice["contract"]["target"]["case"], "bp-ng45")
        self.assertLess(L.entry(evidence, "R2")["score"], L.entry(evidence, "R1")["score"])
        # The same splice is never offered twice, and the last slot still allows it (it can win).
        repeat = P.plan_next(evidence, (x["candidate_id"], "decoder_only", {"reason": "extend_best",
                                                                            "component": "decoder"}), 1, 10,
                             considered([x, y]) | {(choice["factors"]["loss"], choice["factors"]["decoder"])})
        self.assertEqual(repeat["choice"]["kind"], "edit")


def two_branches(x_gain, y_gain):
    """Hypothetical receipts on the real ours-new matrix: X edits the loss and leaves bp's labels alone,
    Y edits the decoder and leaves bp_fe's and ariane's labels alone, so every start cell is measured."""
    base = EVIDENCE[1]
    keys = ["%s/%s" % (c["case"], c["seed"]) for c in base["cells"]]
    host = {key: c["score"] for key, c in zip(keys, replay.published_start(replay.schedule(EVIDENCE))["feedback"]["cells"])}
    def receipt(name, gains, moved, source, component):
        part = {key: {"partition_assignment_changed_count": 300 if moved(key) else 0,
                      "partition_assignment_changed_fraction": 0.01 if moved(key) else 0.0} for key in keys}
        deltas = {key: host[key] + gains(key) - next(c["score"] for k, c in zip(keys, base["cells"]) if k == key)
                  for key in keys}
        return shifted(base, name, deltas, source=source, partition=part,
                       attempt={"parent_id": base["attempt"]["parent_id"], "changed_components": {component: {}}})
    loss = replay.INITIAL.replace("F.logsigmoid(-negative_scores).sum()", "0.9 * F.logsigmoid(-negative_scores).sum()")
    decoder = replay.INITIAL.replace("    return reference_global_two_way(", "    return 0 + reference_global_two_way(")
    x = receipt("x", lambda key: 0.0 if key.startswith("bp-") else x_gain, lambda key: not key.startswith("bp-"), loss, "loss")
    y = receipt("y", lambda key: y_gain if key.startswith("bp-") else 0.0, lambda key: key.startswith("bp-"), decoder, "decoder")
    return x, y


class OptionRules(unittest.TestCase):

    def test_two_credited_single_function_gains_are_merged_once(self):
        x, y = two_branches(12.0, 8.0)
        evidence = replay.ledger_for([x, y])
        self.assertTrue(all(cell["measured_on"] == "this_host" for cell in L.entry(evidence, "S")["cells"].values()))
        self.assertTrue(L.credited_gain(L.contrast(evidence, "R1", "S")))
        self.assertTrue(L.credited_gain(L.contrast(evidence, "R2", "S")))
        plan = P.plan_next(evidence, (x["candidate_id"], "decoder_only", {"reason": "extend_best", "component": "decoder"}),
                           8, 10, considered([x, y]))
        self.assertEqual([option["kind"] for option in plan["options"]], ["merge", "edit"])  # the transplant is the same program
        merge = plan["choice"]
        self.assertEqual((merge["parent"], merge["component"], merge["donors"]), ("R1", "decoder", {"loss": "R1", "decoder": "R2"}))
        self.assertEqual(merge["evidence"], ["R1-S", "R2-S"])

    def test_a_dose_change_is_labelled_coefficients_only(self):
        evidence, plan = plan_after("ours-new", 4)
        self.assertEqual(L.entry(evidence, "R4")["footprint"], {"loss": "coefficients_only", "decoder": "unchanged"})
        reading = next(row for row in plan["lessons"] if row["finding"] == "paired_reading")
        self.assertEqual(reading["edit"]["loss"], "coefficients_only")

    def test_transplant_needs_a_gain_over_the_anchors_own_function(self):
        # R8's loss beat its sibling R7 on bp_fe, but it is worse than R2's own loss there (R8-R4: -9.4).
        evidence, plan = plan_after("claude-original", 8)
        self.assertEqual(plan["baseline"]["reason"], "switch_branch")
        self.assertNotIn("transplant", [option["kind"] for option in plan["options"]])
        self.assertTrue([effect for effect in L.case_effects(evidence)
                         if effect["from"] == "R8" and effect["versus"] == "R7" and effect["case"] == "bp_fe-ng45"])

    def credible_repair(self):
        """A branching repair of R4 whose protected gain clears bp_fe's measured cell sensitivity."""
        r4 = ORIGINAL[3]["candidate_id"]
        return (r4, "loss_only", {"reason": "targeted_repair", "component": "loss", "incumbent_id": r4,
                                  "protect_gain": {"case": "bp_fe-ng45", "seed": "1002", "score_delta": 12.0},
                                  "repair_regression": {"case": "bp-ng45", "seed": "1002", "score_delta": -19.5}})

    def test_a_credible_repair_keeps_its_own_target_and_offers_no_removal(self):
        evidence, plan = plan_after("claude-original", 4, baseline=self.credible_repair())
        self.assertLess(L.tolerances(evidence)["bp_fe-ng45"]["cell"], 12.0)
        self.assertIsNone(plan["decision_override"])
        self.assertEqual([option["kind"] for option in plan["options"]], ["edit"])  # removals only extend the best
        contract = plan["choice"]["contract"]
        self.assertEqual(contract["target"]["case"], "bp-ng45")
        self.assertIn("bp_fe-ng45", [rule["case"] for rule in contract["protect"]])

    def test_a_repair_around_a_gain_inside_the_measured_sensitivity_is_declined(self):
        # Rounds 7 and 9 each made a loss edit of R4 that lost ground; branching then protects one
        # ariane133 gain (+13.2, +15.1) that is smaller than ariane133's measured cell sensitivity.
        for rounds in (7, 9):
            evidence, plan = plan_after("claude-original", rounds)
            self.assertEqual(plan["baseline"]["reason"], "targeted_repair")
            declined = next(row for row in plan["lessons"] if row["finding"] == "repair_declined")
            self.assertIn("ariane133-ng45", declined["conclusion"])
            self.assertEqual((plan["choice"]["parent"], plan["choice"]["component"]), ("R4", "decoder"))
            self.assertEqual(plan["decision_override"]["reason"], "extend_best")
            self.assertEqual(L.tolerances(evidence)["ariane133-ng45"]["source"], "calibrated")


class BudgetAndTriggers(unittest.TestCase):

    def test_splices_never_run_twice_in_a_row(self):
        attempts = {ORIGINAL[3]["request_id"]: {"experiment": {"kind": "merge", "parent": "R2"}}}
        _, plan = plan_after("claude-original", 4, attempts=attempts)
        self.assertEqual(plan["choice"]["kind"], "edit")

    def test_splices_are_capped_at_a_third_of_the_budget(self):
        attempts = {row["request_id"]: {"experiment": {"kind": "transplant", "parent": "R1"}}
                    for row in ORIGINAL[:3]}
        _, plan = plan_after("claude-original", 4, attempts=attempts)
        self.assertEqual(plan["budget"]["splices_used"], 3)
        self.assertEqual(plan["choice"]["kind"], "edit")

    def test_duplicate_and_stall_trigger_a_planning_call_with_a_real_choice(self):
        _, plan = plan_after("claude-original", 6)
        self.assertEqual(plan["hard"], ["duplicate_outcome", "stalled_branch"])
        self.assertEqual([(option["id"], option["parent"], option["component"]) for option in plan["options"]],
                         [("X1", "R2", "decoder"), ("X2", "R4", "loss")])  # the branch switch, or the champion
        _, quiet = plan_after("claude-original", 2)
        self.assertEqual((quiet["hard"], len(quiet["options"])), ([], 1))

    def test_a_protected_cell_beyond_its_sensitivity_triggers_a_planning_call(self):
        before = replay.ledger_for(EVIDENCE[:3])
        tol = L.tolerances(before)
        contract = P.make_contract(P.review_anchor(before, "R3", tol), "loss", tol, EVIDENCE[2]["candidate_id"])
        attempts = {EVIDENCE[3]["request_id"]: {"experiment": {"kind": "edit", "parent": "R3", "contract": contract}}}
        _, plan = plan_after("ours-new", 4, attempts=attempts)
        verdict = next(row for row in plan["lessons"] if row["finding"] == "plan_verdict")
        beyond = [row["cell"] for row in verdict["protected_regressions"] if row["beyond_cell_tolerance"]]
        self.assertEqual(beyond, ["bp-ng45/1003"])  # ariane's -16.9 and -30.7 lie inside its measured sensitivity
        labels = {row["cell"]: row["evidence"] for row in verdict["protected_regressions"]}
        self.assertEqual(labels["ariane133-ng45/1003"], "within_sensitivity")  # plan-time tolerance, not refitted
        self.assertEqual(verdict["verdict"], "target_met_protection_held")
        self.assertIn("protected_regression", plan["hard"])

    def test_openings_and_failures_keep_the_branching_decision(self):
        _, plan = plan_after("ours-new", 1)
        self.assertEqual((plan["choice"]["kind"], plan["choice"]["parent"], plan["choice"]["component"]),
                         ("edit", "S", "loss"))
        self.assertEqual(plan["hard"], [])

    def test_planning_reply_must_choose_an_offered_option(self):
        _, plan = plan_after("claude-original", 4)
        reply = json.dumps({"choice": "X2", "explanations": ["the loss carries ariane", "the decoder exchange does"],
                            "discriminating_prediction": "ariane stays within 15 points", "falsifier": "bp drops",
                            "edit_brief": "scale the star term", "probe": {"kind": "loss_ratio_vs_parent", "max": 500}})
        parsed = P.parse_plan_reply("Plan:\n" + reply, plan)
        self.assertEqual(parsed["choice"], "X2")
        self.assertEqual(T.accept_spec(parsed["probe"]), {"kind": "loss_ratio_vs_parent", "max": 100.0})
        for bad in ('{"choice": "X9", "explanations": ["a", "b"]}', '{"choice": "X1", "explanations": ["a"]}', "no json"):
            with self.assertRaises(ValueError):
                P.parse_plan_reply(bad, plan)
        with self.assertRaises(ValueError):
            T.accept_spec({"kind": "run_my_code", "source": "import os"})


class CompactPacket(unittest.TestCase):

    def test_generation_packet_replaces_the_long_receipt_views(self):
        recorded = json.loads((HERE / "fixtures" / "ours_new_round4_request.json").read_text(encoding="utf-8"))["request"]
        evidence, plan = plan_after("ours-new", 3)
        packet = P.generation_packet(plan, plan["choice"], evidence)
        labels = {row["candidate_id"]: row["id"] for row in evidence["entries"]}
        assembled = P.assemble_request(recorded, packet, None, labels, parent_is_last=True)
        size, before = len(json.dumps(assembled, ensure_ascii=False)), len(json.dumps(recorded, ensure_ascii=False))
        self.assertLess(size, 0.7 * before, (size, before))
        self.assertEqual(len(assembled["experiment"]["anchor_review"]["rows"]), 9)
        self.assertEqual(sorted(row["case"] for row in assembled["experiment"]["contract"]["protect"]),
                         ["ariane133-ng45", "bp-ng45"])
        scores = {(c["case"], c["seed"]): c["score"] for c in assembled["last_trial"]["cells"]}
        self.assertEqual(len(scores), 9)
        self.assertAlmostEqual(scores["bp_fe-ng45", "1001"], 22.9925, places=4)
        self.assertEqual(assembled["parent_program"], recorded["parent_program"])
        self.assertEqual(assembled["parent_feedback"], {"same_as": "last_trial"})


class SelfTests(unittest.TestCase):
    """Acceptance 4: each failure gives a diagnostic; an unavailable probe is skipped, not failed."""

    STARTER = "reference_global_two_way(embeddings, node_areas, seed, max_iterations, balance_target)"

    def decoder(self, body):
        return replay.INITIAL.replace("    return " + self.STARTER, body)

    def test_manifest_mismatch_blocks_submission(self):
        loss_edit = replay.INITIAL.replace("F.logsigmoid(-negative_scores).sum()", "0.5 * F.logsigmoid(-negative_scores).sum()")
        findings = {row["check"]: row for row in T.static_checks(loss_edit, replay.INITIAL, {"component": "decoder"},
                                                                 replay.schedule(EVIDENCE))}
        self.assertEqual(findings["manifest"]["status"], "fail")
        self.assertIn("declares ['decoder'] but the program changes ['loss']", findings["manifest"]["detail"])

    def test_spliced_program_matches_its_declared_donors(self):
        source = P.splice_source(ORIGINAL[2]["source"], ORIGINAL[3]["source"])
        factors = {"loss": L.factor_ids(ORIGINAL[2]["source"])["loss"], "decoder": L.factor_ids(ORIGINAL[3]["source"])["decoder"]}
        self.assertEqual(L.factor_ids(source), factors)
        findings = T.static_checks(source, ORIGINAL[3]["source"], {"component": "loss", "factors": factors},
                                   replay.schedule(ORIGINAL))
        self.assertEqual([row["check"] for row in findings if row["status"] == "fail"], [])

    def test_identity_rules_flag_seed_dispatch_but_not_seeded_initialisation(self):
        schedule = replay.schedule(ORIGINAL)
        self.assertEqual(T.identity_rules(ORIGINAL[3]["source"], schedule), [])  # int(seed) % n_nodes
        dispatch = self.decoder("    labels = " + self.STARTER + "\n    if seed == 1002:\n        return 1 - labels\n"
                                "    return labels")
        self.assertEqual(len(T.identity_rules(dispatch, schedule)), 3)  # branch, comparison, seed value
        named = self.decoder('    tag = "bp-ng45"\n    return ' + self.STARTER)
        self.assertEqual(T.identity_rules(named, schedule), ["line 31 names a training design"])

    def test_newer_syntax_and_oversized_programs_fail(self):
        newer = self.decoder("    match seed:\n        case _:\n            pass\n    return " + self.STARTER)
        self.assertEqual(T.static_checks(newer, replay.INITIAL, {}, [])[0]["status"], "fail")
        padded = self.decoder("    pad = " + repr("x" * 18000) + "\n    return " + self.STARTER)
        self.assertIn("program_bytes", [row["check"] for row in T.static_checks(padded, replay.INITIAL, {}, [])
                                        if row["status"] == "fail"])

    def test_unavailable_probe_runtime_is_reported_as_skipped(self):
        with mock.patch.object(T, "_module", return_value=None):
            results = T.run_probes(replay.INITIAL, replay.INITIAL, {"loss", "decoder"})
        self.assertEqual([(row["probe"], row["status"]) for row in results],
                         [("decoder_contract", "skipped"), ("loss_contract", "skipped")])
        self.assertIn("not importable", results[0]["reason"])

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is not installed in this interpreter")
    def test_decoder_probe_rejects_invalid_labels(self):
        import numpy
        import probe_helper
        helper = probe_helper.make_reference(numpy)  # a test double; the Agent ships no copy of the helper
        cases = {
            "    return " + self.STARTER: "pass",
            "    return 1 - " + self.STARTER: "pass",
            "    return embeddings[:, 0] * 0.0 + 2": "fail",
            "    return np.ones(node_areas.shape[0], dtype=np.int64)": "fail",
            "    return embeddings[:, 0] > 9.0": "fail",
            "    return (embeddings[:, 0] > 0.0) * 1.0": "fail",
        }
        for body, expected in cases.items():
            result = T.decoder_probe(self.decoder(body), replay.INITIAL, helper)
            self.assertEqual(result["status"], expected, (body, result))
        exchanged = T.decoder_probe(self.decoder("    return 1 - " + self.STARTER), replay.INITIAL, helper)
        self.assertEqual((exchanged["change_vs_parent"], exchanged["change_vs_parent_up_to_exchange"]), (1.0, 0.0))
        # A planner's paper check runs only through the fixed probe and stays advisory.
        spec = {"kind": "decoder_change_vs_parent", "min_fraction": 0.05}
        results = T.run_probes(self.decoder("    return 1 - " + self.STARTER), replay.INITIAL, {"decoder"}, spec, helper)
        self.assertEqual(results[-1]["status"], "note")
        self.assertFalse(results[-1]["expectation_held"])  # an exchange keeps the grouping

    @unittest.skipUnless(importlib.util.find_spec("numpy"), "NumPy is not installed in this interpreter")
    def test_without_a_supported_helper_only_custom_decoders_are_probed(self):
        self.assertEqual(T.HELPER_PROVIDERS, ())  # nothing copied from the evaluator ships in the Agent
        helper_decoder = T.decoder_probe(self.decoder("    return 1 - " + self.STARTER), replay.INITIAL)
        self.assertEqual(helper_decoder["status"], "skipped")
        self.assertIn("no supported provider", helper_decoder["reason"])
        # R4 of the original run is a custom NumPy decoder: it runs, and its helper-calling parent is not compared.
        custom = T.decoder_probe(ORIGINAL[3]["source"], ORIGINAL[1]["source"])
        self.assertEqual(custom["status"], "pass", custom)
        self.assertIsNone(custom["change_vs_parent"])
        broken = T.decoder_probe(ORIGINAL[3]["source"].replace("return labels", "return labels * 2.5"),
                                 ORIGINAL[1]["source"])
        self.assertEqual(broken["status"], "fail")

    def test_probes_run_candidates_with_the_interpreters_builtins(self):
        # The archived formal run rejected a decoder with "KeyError: '__import__'": NumPy's lazy imports
        # read __import__ from the calling frame, which a restricted builtins table does not have.
        import builtins
        loss, decoder = T._load(replay.INITIAL, {})
        self.assertIs(loss.__globals__["__builtins__"], builtins)
        self.assertIs(decoder.__globals__["__builtins__"], builtins)

    def test_an_import_problem_inside_a_probe_is_skipped_not_failed(self):
        failing = self.decoder("    return " + "np.missing_attribute_for_test(embeddings)")
        fake = type("FakeNumpy", (), {"__getattr__": lambda self, name: (_ for _ in ()).throw(ImportError(name))})()
        with mock.patch.object(T, "_module", return_value=fake), mock.patch.object(T, "_decoder_fixture",
                                                                                   return_value=(None, None)):
            result = T.decoder_probe(failing, replay.INITIAL)
        self.assertEqual(result["status"], "skipped")
        self.assertIn("probe environment", result["reason"])

    def test_runtime_capabilities_are_reported(self):
        capabilities = T.runtime_capabilities()
        self.assertEqual(capabilities["python"].split(".")[:2], [str(v) for v in sys.version_info[:2]])
        self.assertIsNone(capabilities["reference_helper"])
        with mock.patch.object(T, "_module", return_value=None):
            self.assertEqual((T.runtime_capabilities()["decoder_probe"], T.runtime_capabilities()["loss_probe"]),
                             ("skipped", "skipped"))

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed in this interpreter")
    def test_loss_probe_rejects_nan_and_detached_losses(self):
        def loss(expression):
            return replay.INITIAL.replace("""    return -(
        F.logsigmoid(positive_scores).sum()
        + F.logsigmoid(-negative_scores).sum()
    ) / max(1, source_batch_size)""", "    return " + expression)
        self.assertEqual(T.loss_probe(replay.INITIAL, replay.INITIAL)["status"], "pass")
        nan = T.loss_probe(loss("positive_scores.sum() * float('nan')"), replay.INITIAL)
        self.assertEqual((nan["status"], nan["reason"]), ("fail", "returned a non-finite loss"))
        detached = T.loss_probe(loss("torch.zeros_like(positive_scores).sum()"), replay.INITIAL)
        self.assertEqual(detached["reason"], "returned a loss detached from the embeddings")
        vector = T.loss_probe(loss("F.logsigmoid(positive_scores)"), replay.INITIAL)
        self.assertEqual(vector["reason"], "did not return one scalar tensor")

    def test_new_modules_pass_the_python_38_gate(self):
        spec = importlib.util.spec_from_file_location("py38_gate", HERE.parent / "tools" / "py38_gate.py")
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        for name in ("ledger.py", "rolling_plan.py", "self_test.py"):
            self.assertEqual(gate.scan(replay.AGENT_DIR / name), [], name)


if __name__ == "__main__":
    unittest.main()
