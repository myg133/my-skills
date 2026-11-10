# 用例 JSON Schema 与字段语义

用例集是**单个 JSON 文件**，由 `scripts/validate-cases.mjs` 强制校验。

## 顶层结构

```json
{
  "meta": {
    "source": "需求来源标识",
    "generated_at": "2026-11-09T10:20:00+08:00",
    "case_count": 3
  },
  "requirements": [
    { "id": "R-1", "title": "需求条目标题", "source_ref": "原文摘录或位置", "testable": true }
  ],
  "cases": [
    {
      "id": "TC-001",
      "title": "用例标题",
      "requirement_refs": ["R-1"],
      "dimension": "functional",
      "priority": "P0",
      "preconditions": [],
      "steps": [{ "action": "操作", "expected": "预期结果" }],
      "data": {},
      "tags": []
    }
  ]
}
```

## `meta`

| 字段 | 类型 | 语义 |
|------|------|------|
| `source` | string | 需求来源标识（文档名、链接、需求单号），让人能回溯到原始需求 |
| `generated_at` | string | 生成时间，ISO-8601 |
| `case_count` | number | 用例总数，与 `cases` 数组长度一致 |

`meta` 用于报告抬头，不参与覆盖计算。

## `requirements[]`（需求条目）

| 字段 | 类型 | 必填 | 语义 |
|------|------|------|------|
| `id` | string | 是 | 需求条目 ID，约定 `R-<序号>`，全局唯一 |
| `title` | string | 建议 | 条目标题，追溯矩阵里显示 |
| `source_ref` | string | 建议 | 原文摘录或位置（章节号、页码、引用句） |
| `testable` | boolean | 建议 | 是否可测试点；`false` 表示背景叙述等不生成用例 |

`id` 必须存在且唯一——`cases[].requirement_refs` 通过它建立追溯关系。`title` / `source_ref` 缺失不影响校验，但追溯矩阵的可读性会下降。

## `cases[]`（用例）

| 字段 | 类型 | 必填 | 约束 | 语义 |
|------|------|------|------|------|
| `id` | string | 是 | 匹配 `^TC-\d{3}$`，全局唯一 | 用例编号，`TC-001` 起递增 |
| `title` | string | 是 | 非空 | 一句话说清这条用例验证什么 |
| `requirement_refs` | string[] | 是 | 非空数组，每项必须存在于 `requirements[].id` | 这条用例覆盖哪些需求条目（可多选） |
| `dimension` | string | 是 | 8 个枚举值之一 | 覆盖维度，见 `coverage-dimensions.md` |
| `priority` | string | 是 | `P0` / `P1` / `P2` / `P3` | 缺陷漏掉的代价分级 |
| `preconditions` | string[] | 否 | 数组 | 前置条件（环境、账号、数据状态） |
| `steps` | object[] | 是 | 至少 1 条，每条含非空 `action` 与 `expected` | 执行步骤 |
| `data` | object | 否 | 对象 | 用例数据（入参、期望值、样本集） |
| `tags` | string[] | 否 | 数组 | 自由标签，便于按标签筛选 |

### `steps[]`

```json
{ "action": "在登录页输入用户名 alice 与密码 12345678", "expected": "页面跳转到工作台并显示 alice" }
```

- `action`：可执行的动作描述。写清输入什么、点哪里、调用什么接口。
- `expected`：**可判定**的结果。避免"显示正常""功能可用"这类无法判断通过与否的表述；写清看到什么、返回什么值、什么状态。

## 编号约定

- 需求条目：`R-1`、`R-2`、`R-3`…… 按需求原文顺序编号，条目被删除后不复用旧号（避免历史引用错位）。
- 用例：`TC-001`、`TC-002`…… 连续编号，与需求条目编号相互独立。
- 用例只属于一个覆盖维度；一条需求条目被多个维度覆盖时，拆成多条用例，各自 `requirement_refs` 指回同一条目。

## 覆盖与追溯

- 一条需求条目被覆盖 = 至少一条用例的 `requirement_refs` 含它的 `id`。
- 未被任何用例引用的需求条目出现在报告的"未覆盖"清单里，`validate-cases.mjs` 与 `render-report.mjs` 都会输出。
- `testable: false` 的条目同样计入未覆盖清单——它是"显式判定为不覆盖"，报告里靠 `可测试` 列区分，避免把"判定不可测"和"漏设计"混为一谈。

## 校验命令

```
node scripts/validate-cases.mjs cases.json
```

退出码 0 = 通过，1 = 失败（逐条列出问题）。通过时输出需求条目总数、可测试条目数、用例总数、按维度分布、未覆盖需求条目 ID 列表。
