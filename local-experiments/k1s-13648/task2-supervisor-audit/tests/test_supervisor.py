"""Checks for the supervised K1 (K1S) against unmodified K1 on recorded evidence.

    python3 -I -B -m unittest discover -s tests -v          # from the deliverable root

Every replay feeds both Agent directories the same recorded rounds 1-2 of a real run (X = 22120-independent,
Y = 10820-branching): the same candidates, the same official nine-cell receipts, the same opening reviews.
No model, bridge, GPU or physical evaluation is used. Scores are the recorded ones; what is tested is what
each Agent decides and sends next.
"""

import ast
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / "replay"))
import replay  # noqa: E402
import support  # noqa: E402

K1 = ROOT / "baseline-K1" / "AgenticBench" / "agent" / "loss_decoder"
K1S = ROOT / "K1S" / "AgenticBench" / "agent" / "loss_decoder"
X, Y = ROOT / "replay" / "windows" / "X", ROOT / "replay" / "windows" / "Y"
X_ROUND3 = ROOT / "replay" / "after-window" / "X" / "round-03"
X_R1, X_R2 = "ebbb7303ecab06df43dc1de37f8dcc733d4ae6837e1e12df2f7a4f6de5cabfe9", "203e2676d95aed3bcb076441c9947a07c3e70bbe0c0cad0a8e6f0d4ca51c7b1b"
Y_R1, Y_R2 = "ab93edc407d167411e33901f39e5b79bce15bdbff6371832981b6988474fb27e", "057940f3795f03421cbc7c148b8a8c15cdb4ebc0ccc916d543b6e301cd6e5bd3"
OUT = os.environ.get("REPLAY_OUT")   # optional: also write each replay's requests and log here
try:
    import numpy  # noqa: F401  (the Agent's pre-submission decoder probe runs only with NumPy)
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
PROBE_LINE = 'for name in ("abs", "bool", "float", "int", "len", "max", "min", "range", "round", "sum")}'
PROBE_FIXED = 'for name in ("__import__", "abs", "bool", "float", "int", "len", "max", "min", "range", "round", "sum")}'


def with_probe_fix(agent_dir):
    """A temporary copy of an Agent directory with patches/shared-K1-probe-fix.diff applied."""
    copy = Path(support.make_workdir()) / "agent"
    shutil.copytree(agent_dir, copy, ignore=shutil.ignore_patterns("__pycache__"))
    probe = copy / "decoder_probe.py"
    text = probe.read_text(encoding="utf-8")
    assert text.count(PROBE_LINE) == 1
    probe.write_text(text.replace(PROBE_LINE, PROBE_FIXED), encoding="utf-8")
    return copy


def replayed(agent_dir, window, opening=None, followups=(), label=None):
    workdir = support.make_workdir()
    bridge, copy = replay.run(agent_dir, window, workdir, opening, followups)
    if OUT and label:
        replay.write_capture(bridge, copy, Path(OUT) / label)
    return bridge, copy, replay.events(copy)


def of(events, name):
    return [event for event in events if event.get("event") == name]


class XWindow(unittest.TestCase):
    """22120-independent rounds 1-2: loss opening (5.47, labels mostly unchanged), decoder opening (23.42, die swaps)."""

    @classmethod
    def setUpClass(cls):
        cls.k1 = replayed(K1, X, label="X-K1")
        cls.k1s = replayed(K1S, X, label="X-K1S")

    def test_k1_round3_refines_the_die_swap_decoder(self):
        bridge = self.k1[0]
        request = bridge.captured["request"]
        self.assertEqual(bridge.captured["kind"], "generation_request")
        self.assertEqual(request["search_intent"], "refine")
        self.assertEqual(request["decision"], {"reason": "refine_incumbent", "candidate_id": X_R2})
        self.assertEqual(request["parent_id"], X_R2)
        self.assertNotIn("supervisor_note", request)

    def test_k1s_round3_builds_from_the_official_start_with_a_loss_edit(self):
        bridge, copy, events = self.k1s
        request = bridge.captured["request"]
        self.assertEqual(request["parent_id"], "official-initial")
        self.assertEqual(request["parent_program"], replay.official_parent_program(X))
        self.assertEqual(request["search_intent"], "diversify")
        self.assertEqual(request["required_component"], "loss")
        self.assertEqual(request["decision"], {"reason": "supervisor_parent_excluded", "excluded_candidate_id": X_R2})
        self.assertIsNone(request["parent_feedback"])
        self.assertEqual(request["incumbent_feedback"]["candidate_id"], X_R2)   # still shown, still selectable
        note = request["supervisor_note"]
        for fragment in ("+38.26", "-11.31", "ariane133-ng45/1003 at +44.81", "0.155 to 0.158", "6 of 9"):
            self.assertIn(fragment, note)

    def test_review_is_logged_once_with_its_dossier(self):
        bridge, copy, events = self.k1s
        reviews = of(events, "supervisor_review")
        self.assertEqual(len(reviews), 1)
        review = reviews[0]
        self.assertEqual((review["checkpoint"], review["action"], review["rule"]), (2, "exclude_parent", "orientation_only_gain"))
        self.assertEqual(review["candidate_id"], X_R2)
        self.assertEqual(review["policy_step"]["decision"]["reason"], "refine_incumbent")
        dossier = json.loads((copy / "supervisor-dossier-2.json").read_text(encoding="utf-8"))
        text = json.dumps(dossier, sort_keys=True, ensure_ascii=False)
        self.assertEqual(review["dossier_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        # The four sources: requests, replies, parent-child diffs, full nine-cell receipts.
        self.assertEqual([row["role"] for row in dossier["requests"]],
                         ["generation", "opening_alternative", "opening_review"] * 2)
        self.assertEqual(len(dossier["replies"]), 6)
        self.assertEqual([row["candidate_id"] for row in dossier["programs"]], [X_R1, X_R2])
        self.assertTrue(all(row["diff"] for row in dossier["programs"]))
        self.assertEqual([len(summary["cells"]) for summary in dossier["receipts"]], [9, 9])

    def test_rounds_1_and_2_send_identical_requests_in_both_arms(self):
        self.assertEqual(self.k1[0].requests[:6], self.k1s[0].requests[:6])
        self.assertEqual(self.k1[0].captured["system"], self.k1s[0].captured["system"])

    def test_expert_section_still_goes_only_into_the_first_request(self):
        requests = of(self.k1s[2], "model_request")
        self.assertEqual([event["expert_section"] for event in requests], [True] + [False] * 6)
        self.assertIn("supervisor_note", requests[6]["request"])          # the logged round-3 request
        self.assertFalse(any("supervisor_note" in event["request"] for event in requests[:6]))
        note = self.k1s[0].captured["request"]["supervisor_note"]
        self.assertNotIn("Offline Expert Knowledge", note)
        self.assertNotIn("Labels change only when groups cross", note)

    def test_findings(self):
        dossier = json.loads((self.k1s[1] / "supervisor-dossier-2.json").read_text(encoding="utf-8"))
        found = {row["candidate_id"]: row for row in dossier["orientation"]}
        self.assertFalse(found[X_R1]["qualifies"])
        self.assertTrue(found[X_R2]["qualifies"])
        self.assertEqual((found[X_R2]["same_grouping_cells"], len(found[X_R2]["inverted_same_grouping_cells"])), (7, 4))
        self.assertEqual(dossier["identical_labels_with_timing_change"], {X_R1: [], X_R2: []})
        size = dossier["loss_size"][0]
        self.assertEqual((size["candidate_id"], size["control_candidate_id"]), (X_R1, X_R2))
        self.assertAlmostEqual(size["loss_change_min"], 0.1554, places=3)
        self.assertAlmostEqual(size["loss_change_max"], 0.1576, places=3)


class XRestart(unittest.TestCase):
    def test_a_restarted_process_does_not_review_twice(self):
        workdir = support.make_workdir()
        bridge, copy = replay.run(K1S, X, workdir)
        first = bridge.captured["request"]
        for name in ("agent", "paired_feedback", "search_policy", "decoder_probe", "supervisor"):
            sys.modules.pop(name, None)
        sys.path.insert(0, str(copy))
        try:
            again = importlib.import_module("agent")
        finally:
            sys.path.remove(str(copy))
        again.time.sleep = lambda seconds: None
        try:
            again.Agent().run(bridge)
        except replay.Stop:
            pass
        self.assertEqual(len(bridge.later), 2)
        self.assertEqual(bridge.later[1]["request"], first)
        self.assertEqual(len(of(replay.events(copy), "supervisor_review")), 1)
        self.assertEqual(len(bridge.order), 2)   # no second submission, no evaluation spent


class XAfterRound3(unittest.TestCase):
    """Continue with X's real round-3 candidate (also a loss edit of the official start) and its receipt."""

    @classmethod
    def setUpClass(cls):
        cls.bridge, cls.copy, cls.events = replayed(K1S, X, followups=[X_ROUND3], label="X-K1S-after-round3")

    def test_check_records_adoption_and_an_attributable_comparison(self):
        checks = of(self.events, "supervisor_check")
        self.assertEqual(len(checks), 1)
        check = checks[0]
        self.assertTrue(check["adopted"])
        self.assertEqual((check["cells_with_new_grouping"], check["cells"], check["inverted_cells"]), (9, 9, 0))
        self.assertTrue(check["attributable_comparison"])
        self.assertFalse(check["withdraw"])
        self.assertAlmostEqual(check["official_score"], 23.3879, places=3)
        self.assertEqual(check["largest_cell_gain"][0], "ariane133-ng45/1002")
        submitted = of(self.events, "submitted")[2]
        self.assertEqual(submitted["supervised_by"], 2)
        self.assertEqual(submitted["parent_source_sha256"], hashlib.sha256(
            replay.official_parent_program(X).encode("utf-8")).hexdigest())

    def test_the_adjustment_expires_after_one_step(self):
        stopped = self.bridge.stopped
        self.assertEqual(stopped["after_evaluations"], 3)
        step4 = of(self.events, "submitted")[3]
        self.assertEqual(step4["decision"]["reason"], "combine_verified_gains")   # K1's own rule again
        self.assertEqual(step4["parent_id"], X_R2)
        self.assertEqual(len(of(self.events, "supervisor_review")), 1)

    def test_final_selection_still_includes_the_excluded_candidate(self):
        incumbents = of(self.events, "incumbent")
        self.assertEqual(incumbents[-1]["candidate_id"], X_R2)   # 23.42 still beats round 3's 23.39


class YWindow(unittest.TestCase):
    """10820-branching rounds 1-2 in their own order: decoder opening (12.10), loss opening (23.08)."""

    @classmethod
    def setUpClass(cls):
        # With NumPy, both arms need the shared probe fix: K1's probe rejects this recorded decoder (KnownDefect).
        k1, k1s = (with_probe_fix(K1), with_probe_fix(K1S)) if HAVE_NUMPY else (K1, K1S)
        cls.k1 = replayed(k1, Y, opening="decoder_only", label="Y-K1")
        cls.k1s = replayed(k1s, Y, opening="decoder_only", label="Y-K1S")

    def test_both_arms_measure_the_shelved_alternative_without_a_model_call(self):
        for bridge, copy, events in (self.k1, self.k1s):
            self.assertEqual(bridge.captured["kind"], "submission_without_model_call")
            self.assertEqual(bridge.model_calls, 6)
            self.assertEqual(of(events, "submitted")[-1]["decision"], {"reason": "opening_alternative_control"})
        self.assertEqual(self.k1[0].captured["source"], self.k1s[0].captured["source"])

    def test_supervisor_keeps_the_policy_step_and_adds_nothing(self):
        bridge, copy, events = self.k1s
        reviews = of(events, "supervisor_review")
        self.assertEqual([review["action"] for review in reviews], ["keep"])
        self.assertFalse(any("supervisor_note" in json.dumps(request["user"]) for request in bridge.requests))
        self.assertEqual(self.k1[0].requests, bridge.requests)

    def test_findings(self):
        dossier = json.loads((self.k1s[1] / "supervisor-dossier-2.json").read_text(encoding="utf-8"))
        found = {row["candidate_id"]: row for row in dossier["orientation"]}
        self.assertFalse(found[Y_R1]["qualifies"])   # inversions, but the round lost points
        self.assertFalse(found[Y_R2]["qualifies"])   # no inversions
        drift = {key: [row["cell"] for row in rows] for key, rows in dossier["identical_labels_with_timing_change"].items()}
        self.assertEqual(drift[Y_R1], ["bp-ng45/1001", "bp-ng45/1002", "bp-ng45/1003"])
        self.assertEqual(drift[Y_R2], ["bp-ng45/1001", "bp-ng45/1002", "bp-ng45/1003"])
        size = dossier["loss_size"][0]
        self.assertEqual((size["candidate_id"], size["control_candidate_id"]), (Y_R2, Y_R1))
        self.assertAlmostEqual(size["loss_change_min"], 0.2340, places=3)
        self.assertAlmostEqual(size["loss_change_max"], 0.2362, places=3)


@unittest.skipUnless(HAVE_NUMPY, "the decoder probe runs only when NumPy is importable")
class KnownDefect(unittest.TestCase):
    """Pre-existing in K1 (and the 34.75 harness): the probe's narrowed builtins break NumPy's lazy imports."""

    def probe(self, agent_dir, candidate):
        import importlib.util
        spec = importlib.util.spec_from_file_location("probe_under_test", str(Path(agent_dir) / "decoder_probe.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.probe_decoder((candidate / "candidate.py").read_text(encoding="utf-8"),
                                    replay.official_parent_program(X))

    def test_k1_probe_rejects_a_decoder_the_organizer_evaluated(self):
        issue = self.probe(K1, Y / "round-01")
        self.assertEqual(issue, "The decoder raised KeyError on a synthetic probe with read-only inputs: '__import__'")
        self.assertEqual(self.probe(K1S, Y / "round-01"), issue)   # K1S does not change the probe

    def test_shared_fix_accepts_it_and_still_detects_equivalence(self):
        fixed = with_probe_fix(K1)
        self.assertIsNone(self.probe(fixed, Y / "round-01"))
        self.assertIsNone(self.probe(fixed, X / "round-02"))
        start = Path(support.make_workdir()) / "start"
        start.mkdir()
        (start / "candidate.py").write_text(replay.official_parent_program(X), encoding="utf-8")
        self.assertIn("behaviorally equivalent", self.probe(fixed, start))


class Package(unittest.TestCase):
    def test_python38_syntax(self):
        for path in sorted(K1S.glob("*.py")) + [ROOT / "replay" / "replay.py"]:
            ast.parse(path.read_text(encoding="utf-8"), str(path), feature_version=(3, 8))

    def test_only_three_agent_files_differ_from_k1(self):
        changed = sorted(path.name for path in K1S.iterdir() if path.is_file() and not path.name.startswith(".")
                         and (not (K1 / path.name).exists() or (K1 / path.name).read_bytes() != path.read_bytes()))
        self.assertEqual(changed, ["agent.py", "search_policy.py", "supervisor.py"])


if __name__ == "__main__":
    unittest.main()
