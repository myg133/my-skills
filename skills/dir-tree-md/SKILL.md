---
name: dir-tree-md
description: |
  跨项目的 `.dir-tree.md` 维护工具链 skill. 包含 gen_dir_tree.py /
  cleanup_handwritten_tree.py / verify_dir_tree.py 3 个工具.
  触发: 任何项目要建立 / 维护 / 验证 `.dir-tree.md` 递归索引的时候.
  `.dir-tree.md` = 手动段 (组织意图) + AUTO 段 (脚本生成的目录树) 的混合结构,
  让 agent 快速定位文档、避免重复读大文档.

  Use when:
  - 项目要引入 `.dir-tree.md` 索引机制
  - 改了目录结构, 刷新 `.dir-tree.md`
  - 老的 `.dir-tree.md` 手写段里有过时 ASCII 树要清理
  - 验证 `.dir-tree.md` 一致性 (frontmatter / 跳图链接)
  - 跨多个项目时统一维护"项目地图"

  Don't use for:
  - 纯只读浏览 (直接 `ls` / `tree` 命令更轻)
  - 临时一次性目录树 (用 `tree` 或 `find`)
  - 没有 `.dir-tree.md` 约定的项目 (强行引入需先跟用户确认)

  配套使用: 项目根的 `AGENTS.md` (规则层) + 每个目录的 `.dir-tree.md` (索引层)
  + 工具脚本 (执行层). 三者独立, 互不污染.
---

# dir-tree-md — `.dir-tree.md` 递归索引维护工具链

`.dir-tree.md` 是一种"项目级结构索引"模式: 每个目录放一个 `.dir-tree.md`,
里面是手动段 (写组织意图 / 红线 / 跳图) + 自动段 (由脚本生成当前目录结构).
agent 接手新项目时, 从根 `.dir-tree.md` 开始, 按链接向下钻, 几秒就能"看
到"项目长什么样, 不必再 `ls` 几十次.

本 skill 解决 3 类问题:
- **生成**: 写新文件 / 刷新过期文件 → `gen_dir_tree.py`
- **清理**: 老的 `.dir-tree.md` 手写段里有冗余 ASCII 树 → `cleanup_handwritten_tree.py`
- **验证**: 检查 frontmatter 配对 / 跳图链接是否断 → `verify_dir_tree.py`

## Inputs to collect

跑任务前确认 (大多能从上下文拿到):

- **目标**: 第一次引入? 刷新过期? 清理冗余? 验证一致性?
- **项目根**: 在哪个目录跑工具 (cwd 决定扫的范围)
- **目标目录列表**: 哪些目录需要 `.dir-tree.md` (初次引入时跟用户确认范围)
- **是否已经存在 `.dir-tree.md`**: 决定用 `gen_or_update` (保留手写段) 还是新写

## 1. `.dir-tree.md` 设计模式

### 1.1 文件结构 (混合: 手动 + AUTO)

```markdown
# <目录名>/ 目录组织图

> 此文件不在 git 跟踪范围内, 由 mavis 维护 (生成于 <日期>).

## <手动段: 组织意图>           <- 自由写
- 跳到上层: [...](<相对路径>)
- 跳到子图: [...](<子图相对路径>)
- 何时读: <什么场景下读这个目录>
- 维护原则: <改这个目录的红线>
- ⚠️ 注意: <已知坑 / 特殊约束>

---

<!-- AUTO:START -->             <- 标记, 工具不碰标记之外
> 自动段由 generator 维护. 跑 generator 会覆盖.

```text
<目录名>/
├── <子目录>/  → [<子目录>/.dir-tree.md](<子目录>/.dir-tree.md)
├── <子目录>/  (git 仓, 详见 AGENTS.md)
├── <子目录>/  (无组织图)
└── <文件>  (<大小>)
```
<!-- AUTO:END -->
```

### 1.2 手动段 vs 自动段分工

| 段 | 谁维护 | 内容 | 工具碰不碰 |
| --- | --- | --- | --- |
| 顶部标题 + 维护元信息 | mavis / 人 | 标题、生成日期、维护人 | 不碰 |
| 手动段 (H2 章节) | mavis / 人 | 跳到上层/子图、何时读、维护原则、⚠️ 注意 | 不碰 |
| `---` 分隔符 | mavis / 人 | 手动段和 AUTO 段的分界 | 不碰 |
| `<!-- AUTO:START -->` 标记 | 工具生成 | 自动段开始 | 由工具重写 |
| 自动段内容 | 工具生成 | 当前目录的 ASCII 树 + 跳子图链接 | **由工具覆盖** |
| `<!-- AUTO:END -->` 标记 | 工具生成 | 自动段结束 | 由工具重写 |

> 关键设计: **手动段是"组织意图"**, **自动段是"物理事实"**。意图和事实分离, 改事实时不会破坏意图, 改意图时不会跟事实冲突.

### 1.3 跳图链接规范

- 用相对路径, 形如 `[text](subdir/.dir-tree.md)` 或 `[(../../)](...)`
- 不允许 `http://` / `https://` / 绝对路径
- 锚点 `#` 开头允许
- 目标文件必须存在 (verify 工具会检查)

## 2. 工具链 (3 个 Python 脚本)

3 个脚本在 `scripts/` 下, 都是**幂等** + **支持 `--apply` / `--dry-run`**:

### 2.1 `gen_dir_tree.py` — 生成 / 刷新自动段

```bash
# dry-run (输出到 stdout, 不写文件)
python scripts/gen_dir_tree.py <dir1> [dir2 ...]

# 真正写文件
python scripts/gen_dir_tree.py --apply <dir1> [dir2 ...]

# 跑预设目标清单 (--all, 适合大项目, 一次性全更新)
python scripts/gen_dir_tree.py --all
python scripts/gen_dir_tree.py --apply --all
```

**行为**:
- 扫目录深度 2 (自己 + 直接子)
- 跳过 `.git/` `__pycache__/` `.venv/` `node_modules/` `target/` `dist/` `.minimax/` `.aionrs/` 等
- 遇到 git 仓: 标 `(git 仓, 详见 AGENTS.md)`, 不深入
- 遇到有 `.dir-tree.md` 的子目录: 生成跳图链接
- 遇到没有的子目录: 标 `(无组织图)`
- 文件: 标 `(<size>)` 格式 (`B` / `KB` / `MB`)
- **保留手动段**, 只覆盖 `<!-- AUTO:START -->` 到 `<!-- AUTO:END -->` 之间的内容

**自定义目标清单**: 改 `DEFAULT_TARGETS` 列表 (脚本第 34 行附近), 加新路径.

### 2.2 `cleanup_handwritten_tree.py` — 清理手写段里的 ASCII 树

```bash
# dry-run
python scripts/cleanup_handwritten_tree.py

# 真正改
python scripts/cleanup_handwritten_tree.py --apply
```

**行为**:
- 扫预设目标清单的 19+ 个 `.dir-tree.md`
- 找 "## 结构" / "## 顶层结构" 等 H2 标题 + 紧跟的 ```text``` 块
- 整段删掉 (因为自动段会接管)
- 保留其他手写段 (跳到上层 / 何时读 / 维护原则等)

**适用场景**: 老项目第一次引入 `.dir-tree.md` 机制, 已经有手写的 ASCII 树, 想清掉换自动段.

### 2.3 `verify_dir_tree.py` — 验证一致性

```bash
# 扫预设目标
python scripts/verify_dir_tree.py

# 扫指定目录
python scripts/verify_dir_tree.py <dir1> [dir2 ...]

# 严格模式 (警告也算错误)
python scripts/verify_dir_tree.py --strict
```

**检查项**:
1. frontmatter 配对: `<!-- AUTO:START -->` / `<!-- AUTO:END -->` 必须成对, 顺序正确
2. 跳图链接: 相对路径必须存在
3. 跳图链接格式: 不允许外链 / 绝对路径

**退出码**: 有错时 exit 1, 适合 CI / pre-commit hook.

## 3. 典型工作流

### 3.1 新项目第一次引入 `.dir-tree.md`

1. 跟用户确认要建 `.dir-tree.md` 的目录列表 (顶层 + 重要子目录)
2. 在每个目录先**手写**一个 `.dir-tree.md` 头部 + 手动段 (组织意图)
3. 跑 `gen_dir_tree.py --apply <dirs...>` 第一次生成自动段
4. 跑 `verify_dir_tree.py` 确认 link 不断
5. 提交进 git (建议加进项目根的 `AGENTS.md` 写明"每个目录有 `.dir-tree.md` 索引")

### 3.2 改了目录结构, 刷新索引

1. 跑 `gen_dir_tree.py --apply --all` (如果项目已配 `DEFAULT_TARGETS`)
2. 跑 `verify_dir_tree.py` 检查
3. 检查 manual 段是否要更新 (新子目录 / 新红线)

### 3.3 老项目改造 (有手写 ASCII 树)

1. 跑 `cleanup_handwritten_tree.py --apply` 清掉冗余手写树
2. 跑 `gen_dir_tree.py --apply --all` 接管
3. 跑 `verify_dir_tree.py`
4. 手动把自动段链接整理进手写段的"跳到子图"

### 3.4 agent 接手已有项目

1. **从根 `.dir-tree.md` 开始读**: 看顶层目录结构 + 手动段的"角色 / 维护原则"
2. **按需向下钻**: 看到 `→ [subdir/.dir-tree.md](...)` 链接, 想知道细节时再点开
3. **不要重复 `ls`**: `.dir-tree.md` 就是"已分类的 ls", 跟物理事实同步 (verify 过)
4. 写新文件前**先看 `.dir-tree.md` 决定归位**: 手动段"维护原则" + 跳图链接给出"该放哪"

## 4. 跟 `AGENTS.md` 的关系

| 文件 | 角色 | 谁维护 | 频率 |
| --- | --- | --- | --- |
| `AGENTS.md` (项目根) | 规则 / 关键决策 / 已知坑 (harness 自动加载) | 项目 owner | 重大变更时 |
| `.dir-tree.md` (每目录) | 纯结构索引 (手动翻) | mavis 工具 + 偶尔人手 | 目录结构变时 |
| `_tools/gen_dir_tree.py` 等 | 执行工具 | 项目 owner | 改逻辑时 |

**关键**:
- `AGENTS.md` 跟 `.dir-tree.md` 独立, 互不污染
- `AGENTS.md` 写"规则", `.dir-tree.md` 写"结构 + 跳图", 工具写"执行"
- 三者独立维护, 但 agent 接手时建议都读

## 5. 关键设计原则 (做这个 skill 学到的)

1. **手动段 + 自动段分离**: 意图跟事实解耦, 各管各的
2. **frontmatter 标记**: `<!-- AUTO:START -->` / `<!-- AUTO:END -->` 让工具知道边界
3. **跳图链接用相对路径**: 跨平台, 可重定位, verify 能检查
4. **git 仓不深入**: 标 `(git 仓)` 让 agent 自己点开仓内 `AGENTS.md`
5. **幂等 + --apply/--dry-run**: 多次跑结果一样, 跑前可预览
6. **DEFAULT_TARGETS 在脚本里**: 不靠 agent 记忆目标清单, 改一次覆盖全部
7. **不强制每个目录都有**: 没有 `.dir-tree.md` 的子目录标 `(无组织图)`, 渐进引入

## 6. 自定义与扩展

### 6.1 改默认目标清单

每个脚本都有 `DEFAULT_TARGETS` 列表 (在文件顶部), 改成自己项目的目录结构.
**3 个脚本的列表要保持一致** (或至少 `gen_dir_tree.py` 是子集).

### 6.2 改跳过列表

`gen_dir_tree.py` 顶部 `SKIP_DIRS` 集合, 加项目特定的脏目录 (如 `.tox/` `.next/`).

### 6.3 改自动段格式

`gen_dir_tree.py` 的 `gen_tree_block()` 函数是核心, 改输出格式 (如加 icon / 改排序).

### 6.4 集成到 CI / pre-commit

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: verify-dir-tree
      name: Verify .dir-tree.md consistency
      entry: python scripts/verify_dir_tree.py
      language: system
      pass_filenames: false
```

## 7. 触发本 skill 的典型场景

- 新项目要引入结构索引
- 目录结构变了 (新建/删/移), 想批量刷新
- 老的 `.dir-tree.md` 有过时 ASCII 树, 想清理
- 接手项目时发现 `.dir-tree.md` 跟物理目录对不上
- 跨项目时想统一"项目地图"机制
- 项目根有 N 个手写目录树想统一管理

## 8. 不要做的事

- ❌ 不要把 `.dir-tree.md` 跟 `AGENTS.md` 混在一起 (规则 vs 结构, 各管各的)
- ❌ 不要用绝对路径或 http:// 链接 (verify 会报错, 跨平台不友好)
- ❌ 不要在自动段里手写 (会被工具覆盖, 改写到手动段)
- ❌ 不要忘了跑 verify (断链不修, 索引就废了)
- ❌ 不要无限递归 (扫深度 2 就够, 再深就是单目录 ls)
- ❌ 不要把 git 仓内部目录列进 `.dir-tree.md` (让仓自己管, 标 `(git 仓)` 即可)
