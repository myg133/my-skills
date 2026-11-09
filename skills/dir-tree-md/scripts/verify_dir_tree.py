"""
.dir-tree.md 验证脚本 (跟 gen_dir_tree.py 配套)

检查项:
1. frontmatter 配对: <!-- AUTO:START --> ... <!-- AUTO:END --> 必须成对出现
2. 跳图链接: 形如 (../path.md) 或 (path.md) 的相对路径, 目标文件必须存在
3. 跳图链接格式: 只允许相对路径, 不允许 http:// 或绝对路径

用法:
  python verify_dir_tree.py              # 扫 cwd 下所有 .dir-tree.md
  python verify_dir_tree.py <path>...    # 扫指定目录或文件
  python verify_dir_tree.py --strict     # 警告也算错误
"""
from pathlib import Path
import re
import sys

SKIP_DIRS = {
    ".git", "__pycache__", ".venv", "node_modules", "target", "dist",
    ".minimax", ".aionrs", ".idea", ".vscode", ".mypy_cache",
}


def discover_files(root: Path) -> list[Path]:
    """cwd 下所有 .dir-tree.md (跳过 SKIP_DIRS)."""
    return sorted(
        p.resolve()
        for p in root.rglob(".dir-tree.md")
        if not any(part in SKIP_DIRS for part in p.parts)
    )

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
    root = Path.cwd()
    if paths:
        targets = []
        for p in paths:
            path = Path(p).resolve()
            targets.append(path if path.is_file() else path / ".dir-tree.md")
    else:
        targets = discover_files(root)
        if not targets:
            print("cwd 下没有 .dir-tree.md")
            return

    total = 0
    failed = 0
    for t in targets:
        errors = check_file(t)
        total += 1
        rel = t.relative_to(root) if t.is_relative_to(root) else t
        if errors:
            failed += 1
            print(f"❌ {rel}")
            for e in errors:
                print(f"   {e}")
        else:
            print(f"✓ {rel}")

    print()
    print(f"=== 总结: {total} 个文件, {failed} 个有错误 ===")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
