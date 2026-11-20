"""Check the four local training experiments from their native physics receipts."""
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "main-thread"
CASES = {"bp_fe-ng45", "bp-ng45", "ariane133-ng45"}
VERSIONS = ("capacity_quantum", "variance_guard", "three_radius_guard", "coarse_majority")


def load(path):
    return json.loads(path.read_bytes())


def verify(version):
    sheet = load(ROOT / "measurements" / (version + "-train.json"))
    source = (ROOT / "development-code" / (version + ".py")).read_bytes()
    assert hashlib.sha256(source).hexdigest() == sheet["candidate_sha256"], version
    cells = sheet["cells"]
    assert len(cells) == 9
    assert {(c["case"], int(c["seed"])) for c in cells} == {
        (case, seed) for case in CASES for seed in (1001, 1002, 1003)
    }
    scores = []
    for c in cells:
        name = "{}-{}.json".format(c["case"], c["seed"])
        result = load(ROOT / "native-receipts" / version / name)["metrics"]
        assert result["valid"] and result["evaluation_complete"]
        matrix = result["matrix"]
        assert matrix["complete"] and len(matrix["cells"]) == 1
        cell = matrix["cells"][0]
        assert cell["valid"] and cell["status"] == "succeeded"
        assert (cell["case"], int(cell["seed"])) == (c["case"], int(c["seed"]))
        values = cell["metrics"]
        for actual, expected in (
            (cell["score"], c["score"]),
            (values["final_global_wns_setup_ns"], c["wns_ns"]),
            (values["final_global_tns_setup_ns"], c["tns_ns"]),
        ):
            assert math.isclose(actual, expected, abs_tol=1e-9, rel_tol=1e-12), name
        scores.append(cell["score"])
    avg = statistics.mean(scores)
    assert math.isclose(avg, sheet["full_score"], abs_tol=1e-9)
    print("{}: 9 valid cells, {:.6f}".format(version, avg))
    return sheet


if __name__ == "__main__":
    for version in VERSIONS:
        sheet = verify(version)
    validation = load(ROOT / "public-validation-snapshot.json")
    assert validation["candidate_sha256"] == sheet["candidate_sha256"]
    assert validation["scored_cells"] == sum(c["score"] is not None for c in validation["cells"])
    print("Frozen validation snapshot: {}/6 scored".format(validation["scored_cells"]))
