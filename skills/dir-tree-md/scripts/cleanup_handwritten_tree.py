"""
清理 19 个 .dir-tree.md 手写段里的 ASCII 树段 (一次性).

策略:
- 找 "## 结构" 段 (H2 heading) + 紧跟的第一个 ```text``` 块, 整段删掉
- 保留其他手写段 (跳到上层 / 何时读 / 维护原则 等)
- 跑完再跑 gen_dir_tree.py --apply, 自动段会接管

用法:
  python cleanup_handwritten_tree.py --dry-run          # 输出预览, 不改文件
  python cleanup_handwritten_tree.py --apply            # 真正改文件

目标目录: 项目根下 19 个 .dir-tree.md
"""
from pathlib import Path
import re
import sys

# 跟 gen_dir_tree.py 的 DEFAULT_TARGETS 保持一致
DEFAULT_TARGETS = [
    ".",
    "codes",
    "docs",
    "scratchpad",
    "reports_dashboard",
    "docs/00-overview",
    "docs/01-team",
    "docs/02-operations",
    "docs/02-operations/bi",
    "docs/02-operations/bi/00-meta",
    "docs/02-operations/bi/01-ods-public",
    "docs/02-operations/bi/02-design",
    "docs/02-operations/bi/99-decisions",
    "docs/02-operations/bi/Scripts",
    "docs/03-delivery",
    "docs/04-growth",
    "docs/05-governance",
    "docs/prompts",
    "docs/templates",
]


def cleanup_text(text: str) -> tuple[str, bool]:
    """
    删掉 "## 结构" 段 + 紧跟的 ```text``` 块.
    返回 (new_text, changed).
    """
    lines = text.split("\n")
    out = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]
        # 检查是否是 "## 结构" / "## 顶层结构" 段 (ASCII 树标题, 后面跟 ```text``` 块)
        if re.match(r"^##\s*(?:.*)?结构\s*$", line.strip()):
            changed = True
            i += 1  # 跳过 "## 结构" 行
            # 跳过后面空行
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            # 跳过紧跟的 ```text ... ``` 块
            if i < len(lines) and lines[i].strip().startswith("```text"):
                i += 1  # 跳过开始标记
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    i += 1
                if i < len(lines):
                    i += 1  # 跳过结束标记
            # 不写 "## 结构" 也不写 ```text``` 块
            continue
        out.append(line)
        i += 1

    new_text = "\n".join(out)
    # 清理连续空行 (3+ 个空行合并成 2 个)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    return new_text, changed


def main():
    dry_run = "--apply" not in sys.argv
    root = Path.cwd()
    targets = [root / t for t in DEFAULT_TARGETS]

    changed_count = 0
    for t in targets:
        target_file = t / ".dir-tree.md"
        if not target_file.exists():
            print(f"[SKIP] 不存在: {target_file.relative_to(root)}")
            continue

        text = target_file.read_text(encoding="utf-8")
        new_text, changed = cleanup_text(text)

        if not changed:
            print(f"[NOOP] 没找到 '## 结构' 段: {target_file.relative_to(root)}")
            continue

        if dry_run:
            print(f"=== DRY-RUN: {target_file.relative_to(root)} ===")
            # 输出前 30 行对比
            old_preview = "\n".join(text.split("\n")[:30])
            new_preview = "\n".join(new_text.split("\n")[:30])
            print("--- OLD (前 30 行) ---")
            print(old_preview)
            print("--- NEW (前 30 行) ---")
            print(new_preview)
            print()
        else:
            target_file.write_text(new_text, encoding="utf-8")
            changed_count += 1
            print(f"[WROTE] {target_file.relative_to(root)}")

    print()
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== {mode}: {changed_count}/{len(targets)} 个文件被修改 ===")
    if dry_run:
        print("确认 OK 跑 --apply 真正改文件")


if __name__ == "__main__":
    main()
