"""Summarize saved native receipts without mixing different candidate programs."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
EXPORTS = HERE.parents[1] / "exports"
OUT = EXPORTS / "2026-11-18-local-score-challenge"
BP = EXPORTS / "2026-11-18-bp-local"


def main():
    programs = list(HERE.glob("*.py")) + [HERE.parent / "bp-boundary-20261118/negative_second_moment.py"]
    names = {hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest(): p.stem for p in programs}
    cells_by_name = {}
    targets = set()
    latest = 0
    for path in [BP / "new-loss-full-train.json", *sorted(OUT.glob("*.json"))]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("scope") != "local native training cells, common scoring":
            continue
        targets.add(data["benchmark"])
        latest = max(latest, path.stat().st_mtime)
        name = names.get(data["candidate_sha256"], data["candidate_sha256"])
        cells = cells_by_name.setdefault(name, {})
        for row in data["cells"]:
            key = (row["case"], row["seed"])
            if key in cells and cells[key]["score"] != row["score"]:
                raise ValueError(f"Conflicting measurements for {name} {key}")
            cells[key] = row
    if len(targets) != 1:
        raise ValueError("Expected one common comparison score")
    target = targets.pop()
    current_parent = "three_radius_guard"
    parent_cells = cells_by_name.get(current_parent, {})
    parent_score = mean(r["score"] for r in parent_cells.values()) if len(parent_cells) == 9 else None
    updated = datetime.fromtimestamp(latest, tz=timezone(timedelta(hours=8)))
    lines = ["# 本机训练成绩", "", f"回执更新至北京时间 {updated:%Y-%m-%d %H:%M}。", "",
             f"九格目标为服务器上 Claude 版 Harness 第四轮的 {target:.6f} 分。另一个对照是 27528 上 DeepSeek 第三轮在三个算例、同一种子 1002 上的 30.983636 分。两组对照分别见[九格原始记录](../2026-11-18-overnight/claude-formal-vs-official-reference.json)和[三格原始记录](../2026-11-18-overnight/claude-three-server-r3/tests/fixtures/three_servers.json)。", "",
             "下表只使用笔记本上已通过前后端检查的物理结果。`claude_r4` 为同机重跑的冠军源码。部分评估的最高可能均分按每个剩余格最高 100 分计算。", "",
             "| 程序 | 已测格数 | 完整九格均分 | 与本机 39.6809 的分差 | 与服务器 34.755 的分差 | 九格最高可能均分 | 三个算例均取种子 1002 的均分 |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    def ranking(item):
        name, cells = item
        if len(cells) == 9:
            return (0, -mean(r["score"] for r in cells.values()), name)
        return (1, -len(cells), name)

    for name, cells in sorted(cells_by_name.items(), key=ranking):
        scores = [r["score"] for r in cells.values()]
        matched = [r["score"] for r in cells.values() if r["seed"] == 1002]
        full = f"{mean(scores):.4f}" if len(scores) == 9 else "—"
        local_gap = f"{mean(scores) - parent_score:+.4f}" if len(scores) == 9 and parent_score is not None else "—"
        gap = f"{mean(scores) - target:+.4f}" if len(scores) == 9 else "—"
        panel = f"{mean(matched):.2f}" if len(matched) == 3 else "—"
        ceiling = (sum(scores) + 100 * (9 - len(scores))) / 9
        lines.append(f"| `{name}` | {len(scores)}/9 | {full} | {local_gap} | {gap} | {ceiling:.2f} | {panel} |")
    paired_screens = []
    for path in sorted(OUT.glob("*-screen.json")):
        screen = json.loads(path.read_text(encoding="utf-8"))
        if screen.get("scope") == "local paired training probes" and names.get(screen["parent_sha256"]) == current_parent:
            paired_screens.append(screen)
    if paired_screens:
        lines += ["", "## 与本机 39.6809 版的同种子对照", "",
                  "| 候选程序 | 训练格 | 起点得分 | 候选得分 | 分差 |",
                  "| --- | --- | ---: | ---: | ---: |"]
        for screen in paired_screens:
            name = names[screen["candidate_sha256"]]
            for r in screen["probes"]:
                lines.append(f"| `{name}` | {r['cell']} | {r['parent_score']:.2f} | {r['candidate_score']:.2f} | {r['change']:+.2f} |")
    historical = json.loads((EXPORTS / "2026-11-18-overnight/claude-formal-vs-official-reference.json").read_text(encoding="utf-8"))
    reference = next(row for row in historical["rounds"] if row["candidate"] == historical["candidate"])
    reference_cells = {(r["case"], int(r["seed"])): r["score"] for r in reference["cells"] if r["valid"]}
    if len(reference_cells) != 9 or abs(mean(reference_cells.values()) - target) > 1e-8:
        raise ValueError("Historical reference cells do not reproduce the comparison score")
    complete = {name: cells for name, cells in cells_by_name.items() if set(cells) == set(reference_cells)}
    if complete:
        best = max(complete, key=lambda n: mean(r["score"] for r in complete[n].values()))
        lines += ["", "## 本机最佳完整版本与服务器对照", "",
                  f"本机 `{best}` 使用 RTX 4060 Laptop，服务器 Claude 第四轮使用 RTX 4090。两边按相同参考时序计分。",
                  "", "| 算例 | 本机三种子均分 | 服务器三种子均分 | 均分差 |",
                  "| --- | ---: | ---: | ---: |"]
        for case in sorted({case for case, _ in reference_cells}):
            keys = [key for key in reference_cells if key[0] == case]
            local = mean(complete[best][key]["score"] for key in keys)
            server = mean(reference_cells[key] for key in keys)
            lines.append(f"| {case} | {local:.4f} | {server:.4f} | {local - server:+.4f} |")
    ordered = sorted(cells_by_name)
    lines += ["", "## 逐格绝对分", "",
              "| 算例 | 种子 | 服务器 Claude 第四轮 | " + " | ".join(f"`{n}`" for n in ordered) + " |",
              "| --- | --- | ---: | " + " | ".join("---:" for _ in ordered) + " |"]
    for case in ("bp_fe-ng45", "bp-ng45", "ariane133-ng45"):
        for seed in (1001, 1002, 1003):
            row = []
            for name in ordered:
                result = cells_by_name[name].get((case, seed))
                row.append(f'{result["score"]:.2f}' if result else "—")
            lines.append(f"| {case} | {seed} | {reference_cells[case, seed]:.2f} | " + " | ".join(row) + " |")
    final = OUT / "本机训练成绩.md"
    pending = final.with_suffix(".tmp")
    pending.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pending.replace(final)


if __name__ == "__main__":
    main()
