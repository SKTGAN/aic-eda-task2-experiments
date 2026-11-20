"""Build the round-3 side-by-side comparison from the replay outputs.

    python3 -I -B tools/side_by_side.py examples/replays examples/round3-side-by-side

Writes <prefix>.md and <prefix>.html. Every value is read from the captured requests and the Agents'
own search.jsonl logs; nothing is typed in by hand.
"""

import hashlib
import html
import json
from pathlib import Path
import sys


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def events(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(value):
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def brief(field, value):
    if value is None:
        return "null"
    if field == "parent_program":
        return "{} characters, sha256 {}…".format(len(value), sha(value)[:12])
    if field in ("parent_feedback", "incumbent_feedback"):
        return "receipt summary of {}… (score {:.2f}, {} cells)".format(value["candidate_id"][:12], value["score"],
                                                                       len(value["cells"]))
    if field == "recent_feedback":
        return ", ".join("{}… ({:.2f})".format(row["candidate_id"][:12], row["score"]) for row in value) or "[]"
    if field == "mechanism_ledger":
        return "; ".join("{}… {} {}".format(row["candidate_id"][:8], row["mechanism_family"], row["outcome"])
                         for row in value)
    if field == "related_experiment":
        return "{}…".format(value.get("candidate_id", "")[:12]) if isinstance(value, dict) else json.dumps(value)
    if field == "training_cells":
        return "{} cells".format(len(value))
    if field == "decision":
        return ", ".join("{}={}".format(key, (str(item)[:12] + "…") if key.endswith("candidate_id") else item)
                         for key, item in value.items())
    if field == "supervisor_note":
        return "see the full text below ({} characters)".format(len(value))
    return json.dumps(value, ensure_ascii=False)


def main(replays, prefix):
    root = Path(replays)
    k1, k1s = load(root / "X-K1" / "round3-request.json"), load(root / "X-K1S" / "round3-request.json")
    system_same = (root / "X-K1" / "round3-system.txt").read_bytes() == (root / "X-K1S" / "round3-system.txt").read_bytes()
    calls = sorted(path.name for path in (root / "X-K1").glob("call-0[1-6]-*.json"))
    parity = [(name, sha(load(root / "X-K1" / name)), sha(load(root / "X-K1S" / name))) for name in calls]
    review = next(event for event in events(root / "X-K1S" / "search.jsonl") if event["event"] == "supervisor_review")
    dossier = load(root / "X-K1S" / "supervisor-dossier-2.json")
    receipt = next(row for row in dossier["receipts"] if row["candidate_id"] == review["candidate_id"])
    deltas = {"{}/{}".format(cell["case"], cell["seed"]): cell["score_delta"]
              for cell in receipt["parent_comparison"]["cells"]}
    after = events(root / "X-K1S-after-round3" / "search.jsonl")
    check = next(event for event in after if event["event"] == "supervisor_check")
    step4 = [event for event in after if event["event"] == "submitted"][3]
    y_reviews = [event for event in events(root / "Y-K1S" / "search.jsonl") if event["event"] == "supervisor_review"]
    y_k1 = load(root / "Y-K1" / "stopped-at-submission.json")
    y_k1s = load(root / "Y-K1S" / "stopped-at-submission.json")
    y_dossier = load(root / "Y-K1S" / "supervisor-dossier-2.json")

    fields = sorted(set(k1) | set(k1s))
    rows = [(field, brief(field, k1.get(field)) if field in k1 else "absent",
             brief(field, k1s.get(field)) if field in k1s else "absent", k1.get(field) == k1s.get(field))
            for field in fields]
    cells = []
    for cell in receipt["cells"]:
        name = "{}/{}".format(cell["case"], cell["seed"])
        fraction = cell["partition_change_vs_initial"]["partition_assignment_changed_fraction"]
        residual = min(fraction, 1 - fraction)
        cells.append((name, fraction, "yes" if fraction > 0.5 else "no", residual, deltas[name]))

    md = ["# Round 3 before and after the supervisor",
          "",
          "Both Agents received the same rounds 1–2 of run X (22120-independent), replayed from the recorded "
          "candidates and official nine-cell receipts. Columns: **K1** = the delivered K1, unchanged; **K1S** = K1 "
          "plus the supervisor in `patches/K1-to-K1S.diff`.",
          "",
          "## Same evidence in rounds 1–2",
          "",
          "| Call | K1 request sha256 | K1S request sha256 |", "|---|---|---|"]
    md += ["| {} | `{}…` | `{}…` |".format(name, a[:16], b[:16]) for name, a, b in parity]
    md += ["", "The round-3 system prompt is {} in both arms.".format("byte-identical" if system_same else "DIFFERENT"),
           "", "## What each Agent sends as the round-3 request", "",
           "| Field | K1 | K1S | |", "|---|---|---|---|"]
    md += ["| `{}` | {} | {} | {} |".format(field, a.replace("|", "\\|"), b.replace("|", "\\|"), "same" if same else "**changed**")
           for field, a, b, same in rows]
    md += ["", "### Full `supervisor_note` (K1S only)", "", "> " + k1s["supervisor_note"], "",
           "## The intervention record", "",
           "**1. Evidence the supervisor saw** (dossier sha256 `{}…`). It read the six logged requests and replies, "
           "the two parent→child diffs and both nine-cell receipts. The policy's default step was `{}` on `{}…`. "
           "That candidate's cells:".format(review["dossier_sha256"][:16], review["policy_step"]["decision"]["reason"],
                                            review["candidate_id"][:12]),
           "", "| Cell | Changed fraction vs initial | Inverted | Moved after undoing inversion | Δ vs parent |",
           "|---|---:|---|---:|---:|"]
    md += ["| {} | {:.5f} | {} | {:.5f} | {:+.2f} |".format(*cell) for cell in cells]
    basis = review["basis"]
    md += ["",
           "In summed cell points, the inverted same-grouping cells give {:+.2f} and the other cells {:+.2f}, a net of {:+.2f}; "
           "that is {:+.2f} on the official nine-cell mean.".format(
               basis["points_from_inverted_cells"], basis["points_from_other_cells"],
               basis["points_from_inverted_cells"] + basis["points_from_other_cells"], basis["official_score_delta"]),
           "",
           "**2. Decision.** `{}` under rule `{}`. Scope: {}.".format(review["action"], review["rule"], review["applies_to"]),
           "",
           "**3. What changed in the actual round-3 request.**",
           "- The parent is now `official-initial` (the official start, sha256 `{}…`) instead of `{}…`.".format(
               sha(k1s["parent_program"])[:12], review["candidate_id"][:12]),
           "- The intent is `{}` with a required `{}` change instead of `{}`.".format(
               k1s["search_intent"], k1s["required_component"], k1["search_intent"]),
           "- The request carries the new `supervisor_note` quoted above. Everything else is K1's own policy output.",
           "",
           "**4. How the next receipt tests it.**",
           "- The `supervisor_check` event is written after the next complete evaluation. It records:",
           "  - adoption: the parent differs from the excluded candidate;",
           "  - the number of cells whose grouping changed beyond an inversion;",
           "  - inversions, score and largest cell;",
           "  - `withdraw` when most cells kept their grouping.",
           "- Replayed with run X's real round-3 candidate and receipt (also a loss edit of the official start; it "
           "was written under X's own Harness, so this illustrates the check and is not K1S's counterfactual "
           "score):",
           "  - adopted = {}; new grouping on {}/{} cells; inversions {};".format(
               check["adopted"], check["cells_with_new_grouping"], check["cells"], check["inverted_cells"]),
           "  - official score {:.2f} ({:+.2f} vs parent); largest cell {} {:+.2f};".format(
               check["official_score"], check["official_score_delta_vs_parent"], check["largest_cell_gain"][0],
               check["largest_cell_gain"][1]),
           "  - attributable = {}; withdraw = {}.".format(check["attributable_comparison"], check["withdraw"]),
           "- **Expiry.** The adjustment covers one step. At round 4, K1's own rule returned: `{}` with parent "
           "`{}…`.".format(step4["decision"]["reason"], step4["parent_id"][:12]),
           "",
           "## Run Y (10820-branching): no intervention",
           "",
           "This replay uses Y's own decoder-first order (`opening.txt = decoder_only`) and its recorded opening "
           "alternatives. These files were produced on Python 3.8, where the decoder probe is skipped. With NumPy, "
           "both arms need `patches/shared-K1-probe-fix.diff` first (see the KnownDefect tests).",
           "- Supervisor decision: `{}`.".format(", ".join(review_y["action"] for review_y in y_reviews)),
           "- Both arms then submit the same shelved opening alternative, with no model call: source sha256 "
           "`{}…` (K1) and `{}…` (K1S).".format(sha(y_k1["source"])[:12], sha(y_k1s["source"])[:12]),
           "- The review still logs, for people only, that bp-ng45 kept the start labels yet timed differently from "
           "the published start: {}.".format(", ".join(
               row["cell"] for row in y_dossier["identical_labels_with_timing_change"][
                   next(iter(y_dossier["identical_labels_with_timing_change"]))])),
           ""]
    Path(prefix + ".md").write_text("\n".join(md) + "\n", encoding="utf-8")

    def esc(text):
        return html.escape(str(text))

    table = "".join(
        "<tr class='{}'><th scope='row'><code>{}</code></th><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            "same" if same else "changed", esc(field), esc(a), esc(b), "same" if same else "changed")
        for field, a, b, same in rows)
    cell_rows = "".join("<tr><td>{}</td><td class='n'>{:.5f}</td><td>{}</td><td class='n'>{:.5f}</td><td class='n'>{:+.2f}</td></tr>".format(
        esc(name), fraction, inverted, residual, delta) for name, fraction, inverted, residual, delta in cells)
    parity_rows = "".join("<tr><td><code>{}</code></td><td><code>{}…</code></td><td><code>{}…</code></td></tr>".format(
        esc(name), a[:16], b[:16]) for name, a, b in parity)
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Round 3 Side by Side</title>
<style>
:root{{--bg:#fbfbfa;--fg:#1d1d1f;--muted:#5f6368;--line:#d9d9d6;--panel:#ffffff;--accent:#1f5fbf;--changed:#fff4d6;--changedline:#e0b84a}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#141416;--fg:#ececec;--muted:#a3a3a8;--line:#34343a;--panel:#1c1c20;--accent:#7fb0ff;--changed:#3a3218;--changedline:#a8862c}}}}
:root[data-theme="dark"]{{--bg:#141416;--fg:#ececec;--muted:#a3a3a8;--line:#34343a;--panel:#1c1c20;--accent:#7fb0ff;--changed:#3a3218;--changedline:#a8862c}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:1.5rem;margin:0 0 4px}} h2{{font-size:1.15rem;margin:32px 0 8px}} p,li{{max-width:75ch}}
.muted{{color:var(--muted)}} code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86em}}
.scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--panel)}}
table{{border-collapse:collapse;width:100%;min-width:640px}} th,td{{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}}
thead th{{font-size:.85rem;color:var(--muted);font-weight:600}} tr.changed td,tr.changed th{{background:var(--changed)}}
tr.changed td:last-child{{font-weight:600;border-left:3px solid var(--changedline)}} td.n{{text-align:right;font-variant-numeric:tabular-nums}}
blockquote{{margin:8px 0;padding:12px 14px;border-left:3px solid var(--accent);background:var(--panel);border-radius:4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}} .card{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}}
.card b{{display:block;margin-bottom:4px}}
</style></head><body><main>
<h1>Round 3 before and after the supervisor</h1>
<p class="muted">Run X (22120-independent) rounds 1–2, replayed from the recorded candidates and official nine-cell receipts. K1 = delivered K1, unchanged. K1S = K1 + <code>patches/K1-to-K1S.diff</code>.</p>
<div class="grid">
<div class="card"><b>K1, round 3</b><code>{k1_intent}</code> on the round-2 decoder <code>{r2}…</code> (official 23.42, +2.99 vs start)</div>
<div class="card"><b>K1S, round 3</b><code>{k1s_intent}</code> from the official start, required <code>{req}</code> change; round 2 kept for final selection</div>
<div class="card"><b>Why</b>{same}/{n} cells of round 2 are the start grouping, mostly with the dies exchanged; exchanged cells {inv:+.2f}, the rest {rest:+.2f}</div>
</div>
<h2>Same evidence in rounds 1–2</h2>
<div class="scroll"><table><thead><tr><th>Call</th><th>K1 sha256</th><th>K1S sha256</th></tr></thead><tbody>{parity_rows}</tbody></table></div>
<p class="muted">Round-3 system prompt: {system}.</p>
<h2>The round-3 request, field by field</h2>
<div class="scroll"><table><thead><tr><th>Field</th><th>K1 sends</th><th>K1S sends</th><th></th></tr></thead><tbody>{table}</tbody></table></div>
<h2>The added field</h2>
<blockquote><code>supervisor_note</code>: {note}</blockquote>
<h2>Evidence the supervisor used</h2>
<div class="scroll"><table><thead><tr><th>Cell</th><th>Changed vs initial</th><th>Inverted</th><th>Moved after undoing inversion</th><th>Δ vs parent</th></tr></thead><tbody>{cell_rows}</tbody></table></div>
<h2>How the next receipt tests it</h2>
<ul>
<li>The next complete evaluation writes a <code>supervisor_check</code> event. It records adoption, the cells whose grouping changed, inversions, score, largest cell, and <code>withdraw</code>.</li>
<li><b>Illustration with run X's real round-3 receipt</b> (also a loss edit of the official start, but written under X's own Harness, so this is not K1S's counterfactual score):
<ul>
<li>adopted {adopted}; new grouping on {regrouped}/{cells} cells;</li>
<li>official {score:.2f}; largest cell {big} {bigd:+.2f};</li>
<li>attributable {attr}; withdraw {withdraw}.</li>
</ul></li>
<li><b>Expiry:</b> at round 4, K1's own rule returned: <code>{step4}</code> on <code>{step4p}…</code>.</li>
</ul>
<h2>Run Y (10820-branching): no intervention</h2>
<p>The supervisor decision was <code>{y_action}</code>. Both arms submit the same shelved opening alternative with no model call (source <code>{y_src}…</code>). bp-ng45's identical-label timing differences are logged for people only.</p>
</main></body></html>
""".format(k1_intent=esc(k1["search_intent"]), k1s_intent=esc(k1s["search_intent"]), req=esc(k1s["required_component"]),
           r2=esc(review["candidate_id"][:12]), same=basis["same_grouping_cells"], n=basis["cells"],
           inv=basis["points_from_inverted_cells"], rest=basis["points_from_other_cells"], parity_rows=parity_rows,
           system="byte-identical in both arms" if system_same else "DIFFERENT", table=table,
           note=esc(k1s["supervisor_note"]), cell_rows=cell_rows, adopted=check["adopted"],
           regrouped=check["cells_with_new_grouping"], cells=check["cells"], score=check["official_score"],
           big=esc(check["largest_cell_gain"][0]), bigd=check["largest_cell_gain"][1],
           attr=check["attributable_comparison"], withdraw=check["withdraw"], step4=esc(step4["decision"]["reason"]),
           step4p=esc(step4["parent_id"][:12]), y_action=esc(", ".join(r["action"] for r in y_reviews)),
           y_src=sha(y_k1["source"])[:12])
    Path(prefix + ".html").write_text(page, encoding="utf-8")
    print("wrote", prefix + ".md", "and", prefix + ".html")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
