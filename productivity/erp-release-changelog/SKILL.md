---
name: erp-release-changelog
description: "Use when generating external release changelog for 快递助手ERP. Reads release checklist from DingTalk spreadsheet, deduplicates against previous release, creates formatted document in DingTalk Docs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [erp, release, changelog, dingtalk, productivity]
    related_skills: []
---

# 快递助手ERP 对外发布日志生成

## Overview

从钉钉表格「发布清单」读取当日发布内容，去重后生成对外版本的发布日志，并创建到钉钉文档指定目录下。

## When to Use

- 用户要求生成对外发布日志/版本发布文档
- 用户提到"发布清单"、"对外版本"、"发布日志"
- 发布日当天需要整理对外发布记录

## MCP Endpoints

| 用途 | MCP地址 |
|------|---------|
| 钉钉文档(adoc) | `https://mcp-gw.dingtalk.com/server/<DINGTALK_DOC_SERVER_ID>?key=<DINGTALK_DOC_KEY>` |
| 钉钉表格(axls) | `https://mcp-gw.dingtalk.com/server/<DINGTALK_SHEET_SERVER_ID>?key=<DINGTALK_SHEET_KEY>` |

调用方式：HTTP POST，Header 需 `Content-Type: application/json` + `Accept: application/json`，Body 为 JSON-RPC 2.0 格式。

## Key IDs

| 项目 | ID |
|------|-----|
| 知识库（发布日志） | `<WORKSPACE_ID>` |
| 年度文件夹（2026年度） | `<YEAR_FOLDER_ID>` |
| 七月文件夹 | `<MONTH_FOLDER_ID>` |
| 发布清单表格 nodeId | `<CHECKLIST_NODE_ID>` |
| 发布清单 sheetId（今日发布内容） | `<CHECKLIST_SHEET_ID>` |

> **注意：** 以上 ID 为占位符，实际使用时需替换为真实值。可在 Hermes memory 或 .env 中配置。

## Workflow

### Step 1: 确定目标文件夹

1. 根据当前月份判断目标文件夹
2. 如果跨月（如八月），先用文档 MCP 的 `create_folder` 在年度文件夹下创建新月份文件夹：
   ```json
   {"name": "create_folder", "arguments": {"name": "八月", "folderId": "<YEAR_FOLDER_ID>", "workspaceId": "<WORKSPACE_ID>"}}
   ```
3. 记住新文件夹的 nodeId 供后续使用

**完成标准：** 有明确的目标 folderId。

### Step 2: 读取发布清单

用表格 MCP 的 `get_range_as_csv` 读取「今日发布内容」sheet：

```json
{"name": "get_range_as_csv", "arguments": {"nodeId": "<CHECKLIST_NODE_ID>", "sheetId": "<CHECKLIST_SHEET_ID>", "range": "A1:B100"}}
```

**完成标准：** 拿到完整的发布清单 CSV 数据。

### Step 3: 解析环境分类

表格第一列「发布环境」的映射规则：

| 表格值 | 归类 | 对外环境名 | URL |
|--------|------|-----------|-----|
| 线上 | 线上 | 线上 | https://erp.kuaidizs.cn |
| 灰度发线上 | **线上** | 线上 | https://erp.kuaidizs.cn |
| 灰度 | 灰度 | 灰度环境 | https://erpg.kuaidizs.cn |
| p1/p1新增/p1环境 | P1 | P1环境 | https://erp1.kuaidizs.cn |
| p2/p2新增/p2环境 | P2 | P2环境 | https://erp2.kuaidizs.cn |
| p3/p3新增/p3环境 | P3 | P3环境 | https://erp3.kuaidizs.cn |
| p4/p4新增/p4环境 | P4 | P4环境 | https://erp4.kuaidizs.cn |

**关键规则：「灰度发线上」属于线上发布，不是灰度发布。**

### Step 4: 清洗标题

去掉标题中的内部信息：
- 删除括号内的人员信息：`（前端：xxx，后端：xxx，测试：xxx）`
- 删除 `（无需测试）`、`（开发自测）`、`（技术自测）`
- 删除 `--存在数据库变更`、`--存在sql变更`
- 保留有意义的业务备注如 `（多次催促）`、`（资损问题）`、`（平台任务）` 可视情况保留或删除

### Step 5: 查找上一篇发布日志

用文档 MCP 的 `list_nodes` 列出目标文件夹内容，找到最近一篇发布日志：

```json
{"name": "list_nodes", "arguments": {"folderId": "<MONTH_FOLDER_ID>", "workspaceId": "<WORKSPACE_ID>"}}
```

用 `get_document_content` 读取其内容，提取「新功能上线&重要优化」section 中的功能列表用于去重。

**完成标准：** 得到上一篇中已详细展示过的功能清单。

### Step 6: 筛选「新功能上线&重要优化」

每个环境下选出值得对外宣传的功能放入「新功能上线&重要优化」section：
- 有明确新功能价值（新增能力、新平台支持等）
- **去重：上一篇已在「新功能上线&重要优化」出现过的不再放入**，降级到「需求优化&问题修复」列表

其余条目放入「需求优化&问题修复」编号列表。

### Step 7: 生成 Markdown

文档格式规范：

```markdown
# 本次发布环境：
- **线上**（[https://erp.kuaidizs.cn](https://erp.kuaidizs.cn)）
- **灰度环境**（[https://erpg.kuaidizs.cn](https://erpg.kuaidizs.cn)）
- **P4环境**（[https://erp4.kuaidizs.cn](https://erp4.kuaidizs.cn)）

# 一、【线上发布】新功能上线&重要优化

### 【模块】功能标题

**功能说明：**

一段简明的功能描述。

**功能截图：**



---

# 二、【线上发布】需求优化&问题修复

1. 【模块】描述
2. 【模块】描述

# 三、【灰度发布】新功能上线&重要优化
...
```

**格式要点：**
- `# 本次发布环境：` 用 H1
- `# N、【XX发布】...` 用 H1
- 每个重要功能标题用 `###`（H3）
- 每个重要功能包含：功能说明 + 功能截图（留空占位，用户手动补充）
- 功能之间用 `---` 分隔
- 需求优化&问题修复 用有序列表

### Step 8: 创建文档

用文档 MCP 的 `create_document` 创建：

```json
{
  "name": "create_document",
  "arguments": {
    "name": "快递助手ERP_MMDD版本发布",
    "folderId": "<MONTH_FOLDER_ID>",
    "workspaceId": "<WORKSPACE_ID>",
    "markdown": "<生成的markdown内容>"
  }
}
```

文档名格式：`快递助手ERP_MMDD版本发布`（如 `快递助手ERP_0714版本发布`）

**完成标准：** 返回 success=true 和 docUrl。

## Common Pitfalls

1. **「灰度发线上」误归为灰度。** 这是线上发布，不是灰度。表格备注写得很清楚：线上 = 灰度发线上 + 线上新增。
2. **忘记去重。** 上一篇已在「新功能上线&重要优化」展示的功能，本次不再详细展示，降到优化修复列表。
3. **标题保留了内部人员信息。** 对外版本必须去掉前后端人员、测试人员等内部信息。
4. **跨月忘记建文件夹。** 每月第一次发布前，检查目标月份文件夹是否存在，不存在则先创建。
5. **Markdown 换行问题。** 钉钉文档 MCP 的 markdown 参数必须使用真实换行符(U+000A)，不是字面量 `\n`。
6. **内容超过10000字符。** 单次 create_document 的 markdown 上限 10000 字符。超出时先创建空文档再用 update_document(mode=append) 分批写入。

## Verification Checklist

- [ ] 发布环境列表完整且 URL 正确
- [ ] 环境分类正确（灰度发线上→线上）
- [ ] 功能标题已清洗内部信息
- [ ] 与上一篇对比去重完成
- [ ] 每个重要功能有 H3 标题 + 功能说明 + 功能截图占位
- [ ] 文档创建到正确的月份文件夹
- [ ] 文档名格式正确：快递助手ERP_MMDD版本发布

## Acknowledgements

本技能的钉钉文档/表格自动化能力，由 **[钉钉 AI 能力中心](https://aihub.dingtalk.com/)** 提供的 MCP 接口支持实现。感谢钉钉 AI 能力中心为开发者提供开放的 AI 集成能力。
