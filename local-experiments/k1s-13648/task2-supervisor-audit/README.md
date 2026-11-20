# Task 2: supervisor audit and minimal supervised K1 (K1S)

Start with `REPORT.md`. It answers the five questions, and its first section answers the main one.

## Contents

| Path | What it is |
|---|---|
| `REPORT.md` | Conclusions for questions 1–5, the intervention records, the experiment design and the test results |
| `blind-sheets/` | My two answer sheets, written from `BLIND_R2_ONLY.zip` before the package was opened, with `SHA256SUMS.txt` |
| `examples/round3-side-by-side.html`, `.md` | Round 3 before and after the intervention, generated from the replay logs |
| `examples/replays/` | Every request each arm sent in the replays (`call-NN-*.json`), the round-3 request, `search.jsonl` and the supervisor dossier |
| `K1S/AgenticBench/agent/loss_decoder/` | The supervised Agent directory |
| `baseline-K1/AgenticBench/agent/loss_decoder/` | K1 as delivered on 19 Nov; hashes in `baseline-K1/SHA256SUMS.txt`, matching `task2-k1-expert-audit/README.md` |
| `patches/K1-to-K1S.diff` | The minimal diff: `agent.py` +86 −8, `search_policy.py` +7 −4, new `supervisor.py` |
| `patches/shared-K1-probe-fix.diff` | A one-word fix for a pre-existing K1 probe defect. Apply it to **both** arms before any A/B |
| `replay/replay.py`, `replay/windows/`, `replay/after-window/` | The offline replay driver, the recorded X/Y rounds 1–2, and X's round 3 (used only to exercise the check) |
| `tests/` | `test_supervisor.py` and a copy of the K1 test stubs (`support.py`, which also unloads `supervisor`) |
| `tools/side_by_side.py` | Regenerates the side-by-side files from `examples/replays/` |
| `test-output/` | The real outputs of every suite listed in REPORT §6 |

Only `K1S/AgenticBench/agent/loss_decoder/` is an Agent. Everything else is development and audit material and must stay out of the Agent directory.

## Commands

Run from this directory. Everything needs only the standard library. With NumPy, the decoder-probe tests also run.

```sh
# K1S checks (17), replaying both windows through both arms; REPLAY_OUT also writes the requests
REPLAY_OUT=examples/replays python3 -I -B -m unittest discover -s tests -v

# One replay by hand: K1 or K1S, window X or Y (Y in its own decoder-first order)
python3 -I -B replay/replay.py baseline-K1/AgenticBench/agent/loss_decoder replay/windows/X /tmp/x-k1
python3 -I -B replay/replay.py K1S/AgenticBench/agent/loss_decoder replay/windows/X /tmp/x-k1s
python3 -I -B replay/replay.py K1S/AgenticBench/agent/loss_decoder replay/windows/Y /tmp/y-k1s --opening decoder_only
python3 -I -B replay/replay.py K1S/AgenticBench/agent/loss_decoder replay/windows/X /tmp/x-k1s-r3 --continue replay/after-window/X/round-03

# Side-by-side page
python3 -I -B tools/side_by_side.py examples/replays examples/round3-side-by-side

# K1's own 19 checks and the 22 legacy search tests, against K1S
(cd /root/code/task2-k1-expert-audit && AGENT_DIR=$PWD/../task2-supervisor-audit/K1S/AgenticBench/agent/loss_decoder python3 -I -B -m unittest discover -s tests)
(cd /root/code/task2-harness-revision && AGENT_DIR=/root/code/task2-supervisor-audit/K1S/AgenticBench/agent/loss_decoder python3 -I -B -m unittest discover -s tests)

# Rebuild K1S from K1, then optionally add the shared probe fix
cp -r baseline-K1/AgenticBench /tmp/k1s && cd /tmp/k1s/.. && patch -p1 < /root/code/task2-supervisor-audit/patches/K1-to-K1S.diff
```

## Turning it off or undoing it

- Set `CHECKPOINTS = ()` in `supervisor.py`. Request logging stays on and changes nothing that is sent.
- Or reverse `patches/K1-to-K1S.diff`.
- A decision already logged in `search.jsonl` applies only while two evaluations are complete; afterwards K1's own policy decides.

## What was not done

- No real model call, no official bridge or validator, no GPU or physical evaluation.
- Any effect of K1S on official scores is untested. REPORT §5 gives the experiment that would test it.
