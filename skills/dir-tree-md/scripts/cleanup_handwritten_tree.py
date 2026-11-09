"""
清理 .dir-tree.md 手写段里的 ASCII 树段.

策略:
- 找 "## 结构" 段 (H2 heading) + 紧跟的第一个 ```text``` 块, 整段删掉
- 保留其他手写段 (跳到上层 / 何时读 / 维护原则 等)
- 跑完再跑 gen_dir_tree.py --apply, 自动段会接管

用法:
  python cleanup_handwritten_tree.py                 # dry-run, 扫 cwd 下所有 .dir-tree.md
  python cleanup_handwritten_tree.py <dir> [...]     # dry-run, 只扫指定目录
  python cleanup_handwritten_tree.py --apply         # 真正改文件
"""
from pathlib import Path
import argparse
import re

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "node_modules", "target", "dist",
    ".minimax", ".aionrs", ".idea", ".vscode", ".mypy_cache",
}


def discover_targets(root: Path) -> list[Path]:
    """cwd 下所有已有 .dir-tree.md 的目录 (跳过 SKIP_DIRS)."""
    return sorted(
        p.parent.resolve()
        for p in root.rglob(".dir-tree.md")
        if not any(part in SKIP_DIRS for part in p.parts)
    )


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
    p = argparse.ArgumentParser(description="清理 .dir-tree.md 手写段里的 ASCII 树")
    p.add_argument("paths", nargs="*", help="要清理的目录或 .dir-tree.md 文件 (默认 cwd 下全部)")
    p.add_argument("--apply", action="store_true", help="真正改文件 (默认 dry-run)")
    p.add_argument("--dry-run", action="store_true", help="只输出预览 (默认)")
    args = p.parse_args()

    dry_run = not args.apply
    root = Path.cwd()
    if args.paths:
        targets = [Path(t).resolve() for t in args.paths]
    else:
        targets = discover_targets(root)
        if not targets:
            print("cwd 下没有 .dir-tree.md")
            return

    changed_count = 0
    for t in targets:
        target_file = t if t.is_file() else t / ".dir-tree.md"
        rel = target_file.relative_to(root) if target_file.is_relative_to(root) else target_file
        if not target_file.exists():
            print(f"[SKIP] 不存在: {rel}")
            continue

        text = target_file.read_text(encoding="utf-8")
        new_text, changed = cleanup_text(text)

        if not changed:
            print(f"[NOOP] 没找到 '## 结构' 段: {rel}")
            continue

        if dry_run:
            print(f"=== DRY-RUN: {rel} ===")
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
            print(f"[WROTE] {rel}")

    print()
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== {mode}: {changed_count}/{len(targets)} 个文件被修改 ===")
    if dry_run:
        print("确认 OK 跑 --apply 真正改文件")


if __name__ == "__main__":
    main()
