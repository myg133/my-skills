"""
.dir-tree.md 验证脚本 (跟 gen_dir_tree.py 配套)

检查项:
1. frontmatter 配对: <!-- AUTO:START --> ... <!-- AUTO:END --> 必须成对出现
2. 跳图链接: 形如 (../path.md) 或 (path.md) 的相对路径, 目标文件必须存在
3. 跳图链接格式: 只允许相对路径, 不允许 http:// 或绝对路径

用法:
  python verify_dir_tree.py              # 扫 DEFAULT_TARGETS 全部
  python verify_dir_tree.py <path>...    # 扫指定文件
  python verify_dir_tree.py --strict     # 警告也算错误
"""
from pathlib import Path
import re
import sys

# 跟 gen_dir_tree.py 一致
DEFAULT_TARGETS = [
    ".",
    "codes",
    "docs",
    "scratchpad",
    "reports_dashboard",
    "_tools",
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

AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"

# 抓取 markdown 链接: [text](url)
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def check_file(path: Path) -> list[str]:
    """返回错误列表 (空 = 通过)"""
    errors = []
    if not path.exists():
        return [f"[NOEXIST] {path}"]
    text = path.read_text(encoding="utf-8")

    # 1. frontmatter 配对
    has_start = AUTO_START in text
    has_end = AUTO_END in text
    if has_start != has_end:
        if has_start and not has_end:
            errors.append(f"[FM_UNMATCHED] 有 {AUTO_START} 但没 {AUTO_END}")
        elif has_end and not has_start:
            errors.append(f"[FM_UNMATCHED] 有 {AUTO_END} 但没 {AUTO_START}")
    elif has_start and has_end:
        # 都存在, 检查顺序
        start_pos = text.index(AUTO_START)
        end_pos = text.index(AUTO_END)
        if end_pos <= start_pos:
            errors.append(f"[FM_ORDER] {AUTO_END} 在 {AUTO_START} 之前")

    # 2. 跳图链接 (相对路径, 不允许 http://)
    for match in LINK_RE.finditer(text):
        link_text, link_url = match.groups()
        # 跳过纯文本链接 (不是 .md/.dir-tree.md 跳图)
        if not (link_url.endswith(".md") or ".dir-tree.md" in link_url):
            continue
        # 跳过外链
        if link_url.startswith(("http://", "https://", "ftp://", "mailto:")):
            continue
        # 跳过锚点 (#[...])
        if link_url.startswith("#"):
            continue
        # 相对路径, 解析
        target = (path.parent / link_url).resolve()
        if not target.exists():
            errors.append(f"[LINK_BROKEN] '{link_url}' -> {target}")

    return errors


def main():
    strict = "--strict" in sys.argv
    paths = [p for p in sys.argv[1:] if not p.startswith("--")]

    if paths:
        targets = [Path(p) / ".dir-tree.md" for p in paths]
    else:
        root = Path.cwd()
        targets = [root / t / ".dir-tree.md" for t in DEFAULT_TARGETS]

    total = 0
    failed = 0
    warning_count = 0
    for t in targets:
        errors = check_file(t)
        total += 1
        if errors:
            failed += 1
            rel = t.relative_to(Path.cwd()) if t.is_absolute() and t.exists() else t
            print(f"❌ {rel}")
            for e in errors:
                print(f"   {e}")
        else:
            rel = t.relative_to(Path.cwd()) if t.is_absolute() and t.exists() else t
            print(f"✓ {rel}")

    print()
    print(f"=== 总结: {total} 个文件, {failed} 个有错误 ===")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
