---
name: zread-wiki
description: >-
  Use when the project has a .zread/wiki directory. Leverage zread-generated
  documentation as the primary knowledge layer for code understanding,
  architecture analysis, change impact assessment, and feature→file mapping.
  Works across any project — not bound to a specific codebase.
invocation: model+user
---

# Zread Wiki

> 基于 zread 生成的 `.zread/wiki` 文档，为 agent 提供代码理解的知识增强层。
> 跨项目通用，零配置，纯指令驱动。

## When to use

- 进入一个新项目，且项目根目录存在 `.zread/wiki/` 时
- 用户要求理解某个模块、功能或架构时
- 需要评估某个改动的影响范围（"改了哪些文件"、"涉及哪些模块"）
- 审查代码时，需要对照设计文档验证实现是否与设计一致

## Non-goals

- 不要尝试修改或补全 zread wiki 文档（只读使用）
- 不要在 wiki 缺失时模拟或虚构 wiki 内容
- 不要将 wiki 内容置于实际代码之上——代码是真理，wiki 是参考
- 不要全量加载所有 wiki 页面到上下文，按需读取

## Discovery & Indexing

进入项目时，自动执行以下检查：

```
1. 检查 .zread/wiki/versions/ 是否存在
2. 如果存在，找到最新版本目录：
   - 按时间戳排序（目录名格式：YYYY-MM-DD-HHmmss）
   - 取最大值为最新版本
3. 读取该目录下的 wiki.json，建立页面索引
4. 将索引摘要纳入工作记忆：
   - 总页数、section 分布、group 分组
   - 每个页面的 {slug, title, file, section, group, level}
```

索引是轻量级目录，不加载全文。后续按需读取具体页面。

## Context Matching

根据任务上下文，按以下优先级匹配相关 wiki 页面：

| 匹配策略 | 触发条件 | 动作 |
|----------|----------|------|
| 文件路径匹配 | 任务涉及的文件路径与 wiki 页面 Sources 引用匹配 | 读取引用该文件的所有页面 |
| 关键词匹配 | 用户提到的模块名、术语与页面 title/group 匹配 | 读取标题或分组包含该词的页面 |
| 架构理解 | 需要整体理解项目架构 | 读取 Get Started 全部页面 + 核心架构组页面 |
| 模块深潜 | 深入理解某个功能模块 | 读取对应 group 下的所有页面 |
| 代码审查 | 审查某段代码或 diff | 读取 Sources 引用该文件的页面 + 相关架构页面 |

匹配到相关页面后，先快速浏览页面中的 mermaid 图表和 Sources 引用，再进入实际代码阅读。

## Feature→File Mapping

这是本 skill 的核心能力。当用户想修改某个功能时，利用 wiki 页面中的 Sources 引用和内容描述，给出结构化的改动分析。

### 输出格式

每次分析必须给出以下三样东西：

```
1. 文件清单
   - 核心改动文件：必须修改的文件
   - 连带影响文件：可能受影响的文件
   - 参考参考文件：已有类似实现可供参考的文件

2. 改动顺序建议
   - 从底层往上层：service → API Route → 页面组件
   - 或按依赖关系排列

3. 参考 wiki 页面
   - 标出引用了哪些 wiki 页面，方便核对设计意图
```

### 示例

```
用户：我想改客户管理模块的折扣配置逻辑

→ 匹配页面 10《客户管理模块》
→ 从 Sources + 内容提取文件清单：

核心改动：
  - app/msg/page.jsx              — 折扣弹窗 UI 和交互逻辑
  - service/index.js              — 前端服务层，封装折扣接口调用
  - app/api/customerDiscount/route.js — API 代理路由

连带影响：
  - utils/requset.js              — 公共 HTTP 客户端（通常不改）

参考参考：
  - 已有的 QPM 限流配置实现（页面 11）可作为同类弹窗的参考

改动顺序：service → API Route → page.jsx
参考 wiki：页面 10《客户管理模块》、页面 11《用户 LLM 限流配置》
```

### 多模块联动

当改动涉及多个模块时，交叉 Sources 去重，并标注跨模块影响：

```
用户：改充值流程

→ 匹配页面 12《财务中心》+ 页面 13《充值功能》
→ 交叉 Sources 去重后：

涉及文件：
  - app/msg/page.jsx         — 充值入口（客户管理页面）
  - app/keys/page.jsx        — 订单列表（财务中心页面）
  - service/index.js         — 服务层（共享，跨模块改动需回归测试）
  - app/api/recharge/route.js
  - app/api/orderList/route.js

跨模块影响：
  - service/index.js 的改动会影响 msg 和 keys 两个页面
```

## Version Awareness

- 始终使用 `versions/` 下时间戳最大的版本
- 如果 zread 重新生成（新版本目录出现），下次检查时自动切换到新版本
- 旧版本保留在 `versions/` 中，必要时可以回溯对比
- `current/` 目录如果存在符号链接，可直接使用；否则按时间戳定位

## Safety Notes

- **代码优先**：如果 wiki 内容与实际代码不一致，以实际代码为准，并在分析中标注差异
- **差异上报**：发现 wiki 过时或错误时，告知用户但不修改 wiki
- **上下文预算**：只读取与当前任务直接相关的 wiki 页面，避免上下文膨胀
- **跨项目**：该规则适用于任何存在 `.zread/wiki` 的项目，无项目绑定