"""Evaluate the fixed ten-round winner on the organizers' complete public validation matrix."""
import hashlib
import json
from pathlib import Path
import three_gpu as group

root = Path(__file__).resolve().parent
work = root / "k1s-ten"
official = Path("/root/aic-26016/official")
source, bench, data = group.framework(official)
from contest2.halo_policy import validate_matrix_halos
from contest2.sampling import validate_public_matrix
from contest2.scoring import complete_score, validate_scoring_references
from contest2.runtime_images import install, records
from contest2.storage import TrainingStorageTransport
from grt_bench.queue import Queue
from local_bench.matrix import LocalEvaluationMatrix
from local_bench.matrix_docker import DockerMatrixTransport
from local_bench.model import load_task
from local_tasks.tp_gnn_local_task_definitions import DECODER_TASK, materialize_loss_decoder, validate_program

matrix = LocalEvaluationMatrix(data / "loss_decoder/validation/qualified_matrix.json",
                              load_task(bench / "local_tasks" / DECODER_TASK))
validate_matrix_halos(matrix)
validate_public_matrix(matrix, "loss_decoder", "validation")
validate_scoring_references(matrix, "loss_decoder")
assert len(matrix.cells) == 6

def run():
    summary = json.loads((work / "diagnostic-result.json").read_bytes())
    receipts = [json.loads(f.read_bytes()) for f in (work/"receipts").glob("*.json")]
    assert summary["rounds"] == len(receipts) == 10
    candidate_id = summary["selected_candidate_id"]
    chosen = next(r for r in receipts if r["candidate_id"] == candidate_id and r["status"] == "succeeded")
    program = validate_program(chosen["source"], DECODER_TASK)
    assert hashlib.sha256(program.encode()).hexdigest() == candidate_id
    assert len(chosen["feedback"]["cells"]) == 9
    out = root / "public-validation"
    out.mkdir()
    capsule = out / "candidate"
    capsule.mkdir()
    group.atomic(capsule/"candidate.json", materialize_loss_decoder(program))
    group.atomic(out/"selected.json", {"formal":False, "split":"public-validation",
                 "candidate_id":candidate_id,"request_id":chosen["request_id"], "matrix_digest":matrix.identity})
    image = next(iter(records()))
    install(image,out)
    queue = out / "queue.sqlite"
    Queue(queue).register_host("public-C", {"cpu":12,"memory_gb":72,"storage_gb":48,
                                        "gpus":["0","1"],"build_slots":0})
    transport = DockerMatrixTransport(queue=queue,host="public-C",image=image,admission_timeout=1200)
    result = matrix.evaluate(capsule,source,out/"matrix",workers=3,timeout_seconds=None,
                             transport=TrainingStorageTransport(transport,out))
    complete = complete_score(result.metrics,matrix)
    group.atomic(out/"result.json",{"formal":False,"candidate_id":candidate_id,
                 "split":"public-validation","complete":complete,"metrics":result.metrics})
    if not complete: raise RuntimeError("Public validation has incomplete physical receipts")

if __name__ == "__main__":
    import sys
    if "--check" not in sys.argv: run()
    else: print("Verified six official public validation cells", flush=True)
