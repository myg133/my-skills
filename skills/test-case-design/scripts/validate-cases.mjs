#!/usr/bin/env node
// validate-cases.mjs — 测试用例集结构校验器
//
// 用法: node scripts/validate-cases.mjs <cases.json>
// 退出码: 0 = 校验通过, 1 = 校验失败, 2 = 调用方式错误
//
// 纯 Node.js 实现，只依赖 node: 内置模块。
// 只读取并解析 JSON 文件：不发起任何网络请求，也不执行需求文本或用例文本中的任何内容。

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';

// 覆盖维度枚举，与 references/coverage-dimensions.md 的清单保持一致
const DIMENSIONS = [
  'functional',
  'boundary',
  'exception',
  'permission',
  'data',
  'concurrency',
  'performance',
  'compatibility',
];

const PRIORITIES = ['P0', 'P1', 'P2', 'P3'];

const CASE_ID_PATTERN = /^TC-\d{3}$/;

const problems = [];
const warnings = [];

function fail(message) {
  problems.push(message);
}

function warn(message) {
  warnings.push(message);
}

function isObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFilledString(value) {
  return typeof value === 'string' && value.trim() !== '';
}

// 问题清单同时写入 stdout 与 stderr：调用方无论捕获哪个流都能定位到缺陷类型
function emit(line) {
  process.stdout.write(`${line}\n`);
  process.stderr.write(`${line}\n`);
}

function validateRequirements(requirements) {
  const ids = new Set();

  requirements.forEach((item, index) => {
    const at = `requirements[${index}]`;

    if (!isObject(item)) {
      fail(`${at} 必须是对象`);
      return;
    }

    if (!isFilledString(item.id)) {
      fail(`${at} 缺少必填字段 id（需求条目 ID 必须是非空字符串）`);
      return;
    }

    if (ids.has(item.id)) {
      fail(`${at}.id 重复的需求条目 ID: "${item.id}"`);
    }
    ids.add(item.id);

    if (item.title === undefined) {
      warn(`${at}.title 缺失，建议补上需求条目标题以便追溯矩阵可读`);
    } else if (!isFilledString(item.title)) {
      fail(`${at}.title 必须是非空字符串`);
    }

    if (item.testable !== undefined && typeof item.testable !== 'boolean') {
      fail(`${at}.testable 必须是布尔值（true/false）`);
    }

    if (item.source_ref !== undefined && typeof item.source_ref !== 'string') {
      fail(`${at}.source_ref 必须是字符串`);
    }
  });

  return ids;
}

function validateCases(cases, requirementIds) {
  const seenIds = new Map();

  cases.forEach((item, index) => {
    const at = `cases[${index}]`;

    if (!isObject(item)) {
      fail(`${at} 必须是对象`);
      return;
    }

    // --- id: 必填 + 全局唯一 + 格式 ---
    if (!isFilledString(item.id)) {
      fail(`${at} 缺少必填字段 id（用例 ID 必须是非空字符串）`);
    } else {
      if (!CASE_ID_PATTERN.test(item.id)) {
        fail(`${at}.id 非法: "${item.id}"，用例 ID 必须匹配 ^TC-\\d{3}$`);
      }
      if (seenIds.has(item.id)) {
        fail(`${at}.id 重复的用例 ID: "${item.id}"（与 cases[${seenIds.get(item.id)}] 冲突）`);
      } else {
        seenIds.set(item.id, index);
      }
    }

    // --- title: 必填非空 ---
    if (item.title === undefined) {
      fail(`${at} 缺少必填字段 title`);
    } else if (!isFilledString(item.title)) {
      fail(`${at}.title 必须是非空字符串`);
    }

    // --- requirement_refs: 必填非空数组，且不能悬空 ---
    if (item.requirement_refs === undefined) {
      fail(`${at} 缺少必填字段 requirement_refs`);
    } else if (!Array.isArray(item.requirement_refs)) {
      fail(`${at}.requirement_refs 必须是数组`);
    } else if (item.requirement_refs.length === 0) {
      fail(`${at}.requirement_refs 为空，每个用例至少关联 1 个需求条目`);
    } else {
      item.requirement_refs.forEach((ref, refIndex) => {
        const refAt = `${at}.requirement_refs[${refIndex}]`;
        if (!isFilledString(ref)) {
          fail(`${refAt} 必须是非空字符串`);
          return;
        }
        if (!requirementIds.has(ref)) {
          fail(`${refAt} 悬空引用: "${ref}" 在 requirements 中不存在对应的需求条目`);
        }
      });
    }

    // --- dimension: 必填 + 枚举 ---
    if (item.dimension === undefined) {
      fail(`${at} 缺少必填字段 dimension`);
    } else if (!DIMENSIONS.includes(item.dimension)) {
      fail(`${at}.dimension 取值非法: "${item.dimension}"，允许值: ${DIMENSIONS.join(' / ')}`);
    }

    // --- priority: 必填 + 枚举 ---
    if (item.priority === undefined) {
      fail(`${at} 缺少必填字段 priority`);
    } else if (!PRIORITIES.includes(item.priority)) {
      fail(`${at}.priority 取值非法: "${item.priority}"，允许值: ${PRIORITIES.join(' / ')}`);
    }

    // --- steps: 必填，至少 1 条，每条含非空 action 与 expected ---
    if (item.steps === undefined) {
      fail(`${at} 缺少必填字段 steps`);
    } else if (!Array.isArray(item.steps)) {
      fail(`${at}.steps 必须是数组`);
    } else if (item.steps.length === 0) {
      fail(`${at}.steps 为空，至少需要 1 个步骤`);
    } else {
      item.steps.forEach((step, stepIndex) => {
        const stepAt = `${at}.steps[${stepIndex}]`;
        if (!isObject(step)) {
          fail(`${stepAt} 必须是对象（含 action 与 expected）`);
          return;
        }
        if (!isFilledString(step.action)) {
          fail(`${stepAt} 缺少必填字段 action（操作不能为空）`);
        }
        if (!isFilledString(step.expected)) {
          fail(`${stepAt} 缺少必填字段 expected（预期结果不能为空）`);
        }
      });
    }

    // --- 可选字段的类型约束 ---
    if (item.preconditions !== undefined && !Array.isArray(item.preconditions)) {
      fail(`${at}.preconditions 必须是数组`);
    }
    if (item.data !== undefined && !isObject(item.data)) {
      fail(`${at}.data 必须是对象`);
    }
    if (item.tags !== undefined && !Array.isArray(item.tags)) {
      fail(`${at}.tags 必须是数组`);
    }
  });
}

function collectCoverage(requirements, cases) {
  const covered = new Set();

  cases.forEach((item) => {
    if (!isObject(item) || !Array.isArray(item.requirement_refs)) return;
    item.requirement_refs.forEach((ref) => {
      if (isFilledString(ref)) covered.add(ref);
    });
  });

  const uncovered = requirements
    .filter((item) => isObject(item) && isFilledString(item.id) && !covered.has(item.id))
    .map((item) => item.id);

  return { covered, uncovered };
}

function printStats(doc, file, requirements, cases, uncovered) {
  const testableCount = requirements.filter(
    (item) => isObject(item) && item.testable !== false,
  ).length;

  const distribution = new Map(DIMENSIONS.map((name) => [name, 0]));
  let unknownDimension = 0;

  cases.forEach((item) => {
    if (!isObject(item)) return;
    if (typeof item.dimension === 'string' && distribution.has(item.dimension)) {
      distribution.set(item.dimension, distribution.get(item.dimension) + 1);
    } else {
      unknownDimension += 1;
    }
  });

  const source = isObject(doc.meta) && isFilledString(doc.meta.source) ? doc.meta.source : '未标注';
  const generatedAt =
    isObject(doc.meta) && isFilledString(doc.meta.generated_at) ? doc.meta.generated_at : '未标注';

  process.stdout.write(`校验通过: ${file}\n`);
  process.stdout.write(`需求来源: ${source}\n`);
  process.stdout.write(`生成时间: ${generatedAt}\n`);
  process.stdout.write(`需求条目总数: ${requirements.length}\n`);
  process.stdout.write(`可测试条目数: ${testableCount}\n`);
  process.stdout.write(`用例总数: ${cases.length}\n`);
  process.stdout.write('按维度分布:\n');
  for (const [name, count] of distribution) {
    process.stdout.write(`  ${name}: ${count}\n`);
  }
  if (unknownDimension > 0) {
    process.stdout.write(`  (非法维度): ${unknownDimension}\n`);
  }
  process.stdout.write(
    uncovered.length > 0
      ? `未覆盖需求条目: ${uncovered.join(', ')}\n`
      : '未覆盖需求条目: 无（全部需求条目均已被用例覆盖）\n',
  );
}

function main() {
  const file = process.argv[2];

  if (!file) {
    emit('用法: node scripts/validate-cases.mjs <cases.json>');
    process.exit(2);
  }

  const target = resolve(file);

  let raw;
  try {
    raw = readFileSync(target, 'utf8');
  } catch (err) {
    emit(`无法读取用例集文件: ${file}（${err.message}）`);
    process.exit(1);
  }

  let doc;
  try {
    doc = JSON.parse(raw);
  } catch (err) {
    emit(`JSON 语法错误: ${file} 解析失败 — ${err.message}`);
    process.exit(1);
  }

  if (!isObject(doc)) {
    emit('结构错误: 用例集根节点必须是 JSON 对象');
    process.exit(1);
  }

  const requirements = doc.requirements;
  const cases = doc.cases;

  if (requirements === undefined) {
    fail('缺少必填字段 requirements（需求条目数组）');
  } else if (!Array.isArray(requirements)) {
    fail('requirements 必须是数组');
  }

  if (cases === undefined) {
    fail('缺少必填字段 cases（用例数组）');
  } else if (!Array.isArray(cases)) {
    fail('cases 必须是数组');
  }

  const requirementList = Array.isArray(requirements) ? requirements : [];
  const caseList = Array.isArray(cases) ? cases : [];

  const requirementIds = validateRequirements(requirementList);
  validateCases(caseList, requirementIds);

  if (problems.length > 0) {
    emit(`✗ 校验失败: 共 ${problems.length} 个问题（文件: ${file}）`);
    for (const problem of problems) {
      emit(`  - ${problem}`);
    }
    process.exit(1);
  }

  // meta.case_count 与实际用例数不一致只提示不报错：它是抬头元信息，不是结构约束
  if (
    isObject(doc.meta) &&
    typeof doc.meta.case_count === 'number' &&
    doc.meta.case_count !== caseList.length
  ) {
    warn(`meta.case_count (${doc.meta.case_count}) 与实际用例数 (${caseList.length}) 不一致`);
  }

  for (const warning of warnings) {
    process.stdout.write(`[WARN] ${warning}\n`);
  }

  const { uncovered } = collectCoverage(requirementList, caseList);
  printStats(doc, file, requirementList, caseList, uncovered);
  process.exit(0);
}

main();
