#!/usr/bin/env node
// render-report.mjs — 用例集 Markdown 报告渲染器
//
// 用法: node scripts/render-report.mjs <cases.json>
// 输出: stdout，三部分 —— 用例总览表 / 追溯矩阵 / 未覆盖需求条目清单
// 退出码: 0 = 渲染完成, 1 = 读取或解析失败
//
// 纯 Node.js 实现，只依赖 node: 内置模块；只读文件，不发起网络请求。

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';

function isObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFilledString(value) {
  return typeof value === 'string' && value.trim() !== '';
}

// 表格单元格转义：竖线会截断 Markdown 表格，换行会破坏单行结构
function escapeCell(value) {
  if (!isFilledString(value)) return '';
  return value.replace(/\|/g, '\\|').replace(/\r?\n/g, ' ').trim();
}

function buildCoverage(requirements, cases) {
  const covered = new Map();

  cases.forEach((item) => {
    if (!isObject(item) || !Array.isArray(item.requirement_refs)) return;
    item.requirement_refs.forEach((ref) => {
      if (!isFilledString(ref)) return;
      if (!covered.has(ref)) covered.set(ref, []);
      if (isFilledString(item.id) && !covered.get(ref).includes(item.id)) {
        covered.get(ref).push(item.id);
      }
    });
  });

  const rows = requirements
    .filter((item) => isObject(item) && isFilledString(item.id))
    .map((item) => {
      const caseIds = covered.get(item.id) || [];
      return {
        id: item.id,
        title: isFilledString(item.title) ? item.title : '',
        testable: item.testable !== false,
        caseIds,
        status: caseIds.length > 0 ? '已覆盖' : '未覆盖',
      };
    });

  return rows;
}

function render(doc, file) {
  const requirements = Array.isArray(doc.requirements) ? doc.requirements : [];
  const cases = Array.isArray(doc.cases) ? doc.cases : [];
  const rows = buildCoverage(requirements, cases);
  const uncovered = rows.filter((row) => row.status === '未覆盖');

  const meta = isObject(doc.meta) ? doc.meta : {};
  const source = isFilledString(meta.source) ? meta.source : '未标注';
  const generatedAt = isFilledString(meta.generated_at) ? meta.generated_at : '未标注';
  const testableCount = rows.filter((row) => row.testable).length;

  const lines = [];

  lines.push('# 测试用例报告');
  lines.push('');
  lines.push(`- 用例集文件: \`${file}\``);
  lines.push(`- 需求来源: ${escapeCell(source)}`);
  lines.push(`- 生成时间: ${escapeCell(generatedAt)}`);
  lines.push(`- 需求条目总数: ${rows.length}（可测试 ${testableCount}）`);
  lines.push(`- 用例总数: ${cases.length}`);
  lines.push('');

  lines.push('## 用例总览');
  lines.push('');
  if (cases.length === 0) {
    lines.push('（用例集为空）');
  } else {
    lines.push('| 用例 ID | 标题 | 关联需求 | 维度 | 优先级 |');
    lines.push('| --- | --- | --- | --- | --- |');
    cases.forEach((item, index) => {
      const at = isObject(item) ? item : {};
      const refs = Array.isArray(at.requirement_refs)
        ? at.requirement_refs.filter(isFilledString).join(', ')
        : '';
      lines.push(
        `| ${escapeCell(at.id) || `cases[${index}]`} | ${escapeCell(at.title)} | ${escapeCell(refs)} | ${escapeCell(at.dimension)} | ${escapeCell(at.priority)} |`,
      );
    });
  }
  lines.push('');

  lines.push('## 追溯矩阵');
  lines.push('');
  if (rows.length === 0) {
    lines.push('（没有需求条目）');
  } else {
    lines.push('| 需求条目 | 标题 | 可测试 | 覆盖用例 | 覆盖状态 |');
    lines.push('| --- | --- | --- | --- | --- |');
    rows.forEach((row) => {
      const caseIds = row.caseIds.length > 0 ? row.caseIds.join(', ') : '—';
      lines.push(
        `| ${escapeCell(row.id)} | ${escapeCell(row.title)} | ${row.testable ? '是' : '否'} | ${escapeCell(caseIds)} | ${row.status} |`,
      );
    });
  }
  lines.push('');

  lines.push('## 未覆盖需求条目');
  lines.push('');
  if (uncovered.length === 0) {
    lines.push('无（全部需求条目均已被用例覆盖）');
  } else {
    uncovered.forEach((row) => {
      const note = row.testable ? '可测试但无用例覆盖' : '标记为不可测试';
      const title = row.title ? ` — ${escapeCell(row.title)}` : '';
      lines.push(`- ${escapeCell(row.id)}${title}（${note}）`);
    });
  }
  lines.push('');

  return lines.join('\n');
}

function main() {
  const file = process.argv[2];

  if (!file) {
    process.stderr.write('用法: node scripts/render-report.mjs <cases.json>\n');
    process.exit(2);
  }

  const target = resolve(file);

  let raw;
  try {
    raw = readFileSync(target, 'utf8');
  } catch (err) {
    process.stderr.write(`无法读取用例集文件: ${file}（${err.message}）\n`);
    process.exit(1);
  }

  let doc;
  try {
    doc = JSON.parse(raw);
  } catch (err) {
    process.stderr.write(`JSON 语法错误: ${file} 解析失败 — ${err.message}\n`);
    process.exit(1);
  }

  if (!isObject(doc)) {
    process.stderr.write('结构错误: 用例集根节点必须是 JSON 对象\n');
    process.exit(1);
  }

  process.stdout.write(`${render(doc, file)}\n`);
  process.exit(0);
}

main();
