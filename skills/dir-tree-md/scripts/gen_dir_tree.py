"""
.dir-tree.md 自动生成器 (v0.2)

策略:
- 扫目录深度 2 (自己 + 直接子)
- 跳过 .git/ __pycache__/ .venv/ node_modules/ .minimax/ .aionrs/ 等
- 输出 ASCII 树 + 跳到子图链接 + 文件大小
- 用 frontmatter 标记 AUTO 段, 标记之外是手写段, generator 不动

用法:
  python gen_dir_tree.py <dir1> [dir2 ...]                # dry-run, 输出到控制台
  python gen_dir_tree.py --apply <dir1> [dir2 ...]       # 真正写文件
  python gen_dir_tree.py --all                           # 跑 19 个 .dir-tree.md

约定:
- 跟项目根非 git 目录一一对应 (codes/ docs/ scratchpad/ reports_dashboard/ 等)
- 不在 git 仓内部写, 避免污染 (遇到 .git 目录只标 "(git 仓)", 不深入)
"""
from pathlib import Path
from datetime import datetime
import argparse

# 跳过的目录 (这些目录的内容永远不列)
SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "node_modules", "target", "dist",
    ".minimax", ".aionrs", ".idea", ".vscode", ".mypy_cache",
}

# frontmatter 标记
AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"

# 项目根下的"目标目录"清单 (--all 跑这些)
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
    "docs/02-operations/bi/02-design/dashboard-html",
    "docs/02-operations/bi/_archive",
    "docs/02-operations/bi/_archive/migration-20260721",
    "docs/02-operations/bi/99-decisions",
    "docs/02-operations/bi/Scripts",
    "docs/03-delivery",
    "docs/04-growth",
    "docs/05-governance",
    "docs/prompts",
    "docs/templates",
]


def is_git_root(path: Path) -> bool:
    return (path / ".git").exists()


def format_size(n: int) -> str:
    if n < 1024:
        return f"{n}B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f}KB"
    return f"{n/1024/1024:.1f}MB"


def gen_tree_block(target_dir: Path) -> str:
    """生成 ASCII 树 + 跳到子图链接 + 文件大小"""
    if not target_dir.exists() or not target_dir.is_dir():
        return f"_目录不存在或不是目录: {target_dir}_\n"

    lines = ["```text", f"{target_dir.name}/"]
    children = sorted(
        [c for c in target_dir.iterdir() if c.name not in SKIP_DIRS and not c.name.startswith(".")],
        key=lambda c: (not c.is_dir(), c.name.lower()),
    )

    for i, c in enumerate(children):
        is_last = (i == len(children) - 1)
        prefix = "└── " if is_last else "├── "
        if c.is_dir():
            if is_git_root(c):
                lines.append(f"{prefix}{c.name}/  (git 仓, 详见 AGENTS.md)")
            else:
                sub_map = c / ".dir-tree.md"
                if sub_map.exists():
                    lines.append(f"{prefix}{c.name}/  → [{c.name}/.dir-tree.md]({c.name}/.dir-tree.md)")
                else:
                    lines.append(f"{prefix}{c.name}/  (无组织图)")
        else:
            size = format_size(c.stat().st_size)
            lines.append(f"{prefix}{c.name}  ({size})")
    lines.append("```")
    return "\n".join(lines)


def gen_or_update(target: Path, block: str, timestamp: str) -> str:
    """生成/更新 .dir-tree.md, 保留手写段, 只覆盖 AUTO 段

    timestamp 参数保留是为了签名兼容, 但实际**不写**到 auto_block 里
    (否则每次跑 generator 都会改 timestamp, 失去 idempotent 性质)
    """
    # 注意: auto_block 文字里不要包含真实的 marker 字符串
    # 否则 partition() 找 marker 时会被文字里的 marker 误导
    auto_block = (
        f"> 自动段由 generator 维护 (gen_dir_tree.py v0.2). 跑 generator 会覆盖.\n\n"
        f"{block}"
    )

    if not target.exists():
        # 新文件, 简短 header + auto 段
        return (
            f"# {target.parent.name}/ 目录组织图\n\n"
            f"> 由 mavis 维护. 此文件不在 git 跟踪范围内.\n\n"
            f"{AUTO_START}\n{auto_block}\n{AUTO_END}\n"
        )

    text = target.read_text(encoding="utf-8")
    if AUTO_START in text and AUTO_END in text:
        # 已有标记, 只替换 AUTO 段
        before, _, rest = text.partition(AUTO_START)
        _, _, after = rest.partition(AUTO_END)
        # before 末尾可能已经有 `---` 分隔符, 去掉再加新的
        before = before.rstrip()
        if before.endswith("---"):
            before = before[:-3].rstrip()
        return f"{before}\n\n---\n\n{AUTO_START}\n{auto_block}\n{AUTO_END}{after}"

    # 文件存在但没标记, 追加到末尾
    text_stripped = text.rstrip()
    if text_stripped.endswith("---"):
        # 已有 `---` 分隔符, 不再加
        return text_stripped + f"\n\n{AUTO_START}\n{auto_block}\n{AUTO_END}\n"
    return text_stripped + f"\n\n---\n\n{AUTO_START}\n{auto_block}\n{AUTO_END}\n"


def process(target_dir: Path, apply: bool) -> tuple[bool, str]:
    """处理单个目录. 返回 (changed, new_text)"""
    if not target_dir.exists():
        return False, f"[SKIP] 不存在: {target_dir}"
    if not target_dir.is_dir():
        return False, f"[SKIP] 不是目录: {target_dir}"

    target_file = target_dir / ".dir-tree.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = gen_tree_block(target_dir)
    new_text = gen_or_update(target_file, block, timestamp)

    if not apply:
        return False, f"=== DRY-RUN: {target_file} ===\n{new_text}\n"

    if target_file.exists():
        old_text = target_file.read_text(encoding="utf-8")
        if old_text == new_text:
            return False, f"[UNCHANGED] {target_file}"

    target_file.write_text(new_text, encoding="utf-8")
    return True, f"[WROTE] {target_file}"


def main():
    p = argparse.ArgumentParser(description=".dir-tree.md 自动生成器")
    p.add_argument("paths", nargs="*", help="要生成 .dir-tree.md 的目录")
    p.add_argument("--apply", action="store_true", help="真正写文件 (默认 dry-run)")
    p.add_argument("--all", action="store_true", help="跑 DEFAULT_TARGETS (项目根下 19 个 .dir-tree.md)")
    args = p.parse_args()

    if args.all:
        root = Path.cwd()
        targets = [root / t for t in DEFAULT_TARGETS]
    elif args.paths:
        targets = [Path(p).resolve() for p in args.paths]
    else:
        p.error("需要 <paths> 或 --all")

    changed = 0
    for t in targets:
        c, msg = process(t, args.apply)
        if c:
            changed += 1
        print(msg)

    print()
    print(f"=== 总结: {changed}/{len(targets)} 个文件有变化 ===")


if __name__ == "__main__":
    main()
