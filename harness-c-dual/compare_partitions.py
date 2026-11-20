"""Read retained physical partitions on one C host; compare each round with earlier local runs."""
import csv
import gzip
import hashlib
import json
from pathlib import Path


def scan(root):
    by_cell = {}
    for scope in ("control-r4/initial", "run-c/c*-*"):
        pattern = "*/" + scope + "/evaluations/matrix/cells/*/*/result/retained_artifacts/algorithm/20_partition/partition_assignment.csv.gz"
        for file in (root / "workers").glob(pattern):
            parts = file.relative_to(root / "workers").parts
            case, seed = parts[parts.index("cells") + 1:parts.index("cells") + 3]
            tag = "r4" if parts[1] == "control-r4" else "r" + parts[2].split("-")[0][1:]
            by_cell.setdefault((case,seed), {})[tag] = file
    comparisons = {}
    for (case, seed), files in sorted(by_cell.items()):
        if "r4" not in files:
            continue
        with gzip.open(files["r4"], "rt") as inp:
            order = sorted(r["inst_name"] for r in csv.DictReader(inp))
        assert len(order) == len(set(order))
        history = {}
        pairs = {}
        for tag, file in sorted(files.items(), key=lambda item: int(item[0][1:])):
            with gzip.open(file, "rt") as data:
                labels = {row["inst_name"]: row["die"] for row in csv.DictReader(data)}
            if set(labels) != set(order) or not set(labels.values()) <= {"top", "bottom"}:
                raise ValueError(f"Unexpected partition format in {file}")
            tiers = bytes(int(labels[k]=="top") for k in order)
            for old, ref in history.items():
                moved = sum(a != b for a,b in zip(tiers,ref))
                pairs[old+"->"+tag] = {"instances":len(tiers), "changed_tiers":moved,
                    "changed_up_to_die_exchange":min(moved,len(tiers)-moved)}
            history[tag] = tiers
        comparisons[case+"/"+seed] = {"tier_digests":{k:hashlib.sha256(v).hexdigest() for k,v in history.items()},
                                        "pairs":pairs}
    return comparisons


if __name__ == "__main__":
    print(json.dumps(scan(Path("/root/aic-group-c-v1"))))
