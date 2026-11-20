"""Validate and summarize the matched local two-factor evidence."""

import ast
from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FACTORS = ("A", "B", "AB")
LOSS = "compute_tp_gnn_loss"
DECODER = "decode_tp_gnn_embeddings"


def function_body(text, name):
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            if ast.get_docstring(node, clean=False) is not None:
                node.body.pop(0)
            return ast.dump(node, include_attributes=False)
    raise ValueError("Missing function " + name)


def main():
    records = {}
    sources = {}
    for factor in FACTORS:
        body = (HERE / (factor + ".py")).read_text(encoding="utf-8")
        record = json.loads((HERE / (factor + ".json")).read_text(encoding="utf-8"))
        assert record["formal_evaluation"] is False
        assert sha256(body.encode()).hexdigest() == record["candidate_sha256"], factor
        records[factor], sources[factor] = record, body
    for key in ("case", "seed", "baseline", "image", "initial_result", "memory_limit_gib", "initial"):
        assert records["A"][key] == records["B"][key] == records["AB"][key], key
    assert function_body(sources["A"], LOSS) == function_body(sources["AB"], LOSS)
    assert function_body(sources["B"], DECODER) == function_body(sources["AB"], DECODER)
    assert function_body(sources["B"], LOSS) != function_body(sources["AB"], LOSS)
    assert function_body(sources["A"], DECODER) != function_body(sources["AB"], DECODER)
    measurements = {"P": records["A"]["initial"]}
    measurements.update((factor, record["candidate"]) for factor, record in records.items())
    fields = ("common_reference_score", "final_global_wns_setup_ns", "final_global_tns_setup_ns",
              "cut_net_count", "timing_weighted_cut")
    print(json.dumps({
        "scope": "local_diagnostic_one_cell",
        "case": records["A"]["case"],
        "seed": records["A"]["seed"],
        "measurements": {factor: {k: m[k] for k in fields} for factor, m in measurements.items()},
        "interaction_AB_minus_A_minus_B_plus_P": {
            k: measurements["AB"][k] - measurements["A"][k] - measurements["B"][k] + measurements["P"][k]
            for k in fields
        },
        "source_hashes_verified": True,
        "exact_loss_and_decoder_components_verified": True,
    }, indent=2))


if __name__ == "__main__":
    main()
