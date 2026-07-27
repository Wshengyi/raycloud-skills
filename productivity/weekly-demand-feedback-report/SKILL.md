---
name: weekly-demand-feedback-report
description: "Use when generating weekly demand feedback reports for 快递助手ERP — pulling refund/churn data from 钉钉AI表格 MCP, creating weekly docs, and updating the summary table."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [erp, dingtalk, ai-sheet, demand-feedback, weekly-report, productivity]
    related_skills: [dingtalk-alidocs-browser, erp-weekly-progress-report]
---

# 每周需求反馈情况报告

## Overview

从钉钉 AI 表格（售后催促表 + 销售催促表）拉取上周含"马上退款"的需求记录，生成每周需求反馈文档并发布到钉钉文档知识库，同时更新汇总表的三个模块（重点汇总/售后反馈/销售反馈）。

## When to Use

- 每周一需要整理上一周的需求反馈情况
- 用户要求生成"每周需求反馈"或"退款需求汇总"
- 需要更新汇总表中的售后/销售反馈数据

## 数据源

### 钉钉 AI 表格 MCP（streamable-http）

- **售后催促表**：baseId=`<售后BASE_ID>`，tableId=`QiDEMvH`
- **销售催促表**：baseId=`<销售BASE_ID>`，tableId=`QiDEMvH`

### 关键字段（两表结构一致）

| fieldId | 字段名 | 类型 | 说明 |
|---------|--------|------|------|
| AJfe8sL | 需求名称 | text | |
| FTJcv6C | 需求链接（TB链接）| url | |
| 1VYxIRE | 催促人员 | user | |
| fToPCon | 问题类型 | singleSelect | 需求/线上问题&优化 |
| xmJTQac | 评估结论（含原因）| text | |
| yBiZkVE | 需求类型 | multipleSelect | 催促/多次催促/新增反馈商家/不再续费/马上退款/产生资损 |
| GHsMWDx | 催促商家手机号 | text | |
| TTyRnwe | 催促背景 | text | |
| cSIqHZz | 反馈时间 | date | |
| E7mOs0L | 模块 | singleSelect | |
| sSyp8L0 | 需求回复结果 | singleSelect | |

### 需求类型 option ID（售后表）

| 名称 | optionId |
|------|----------|
| 催促 | xKHsk1t5Zr |
| 多次催促 | Mq8Jv2t15w |
| 新增反馈商家 | PlFboeEJsv |
| 不再续费 | 988hyxhLBw |
| 马上退款 | A8SupYrGQr |
| 产生资损 | wlCKtiY0Cy |

## 执行流程

### 第一步：获取退款需求数据

用 `query_records` + `keyword:"马上退款"` 搜索两张表，然后在本地按日期过滤上周（周一至周日）的记录。

```bash
# 售后表
curl -s -X POST "$AI_SHEET_MCP" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"query_records","arguments":{
    "baseId":"<售后BASE_ID>","tableId":"QiDEMvH","limit":100,"keyword":"马上退款"
  }}}'

# 销售表
curl -s -X POST "$AI_SHEET_MCP" \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"query_records","arguments":{
    "baseId":"<销售BASE_ID>","tableId":"QiDEMvH","limit":100,"keyword":"马上退款"
  }}}'
```

本地过滤逻辑：
1. 解析 `cSIqHZz`（ISO 8601 日期）
2. 筛选 date ∈ [上周一, 上周日]
3. 确认 `yBiZkVE` 数组中含 `name:"马上退款"`

### 第二步：去重整理

按 TB 链接（`FTJcv6C.link`）去重。同一需求多次催促时：
- 时间线合并为多条
- 保留最新的催促背景
- 取最新的评估结论/回复结果

### 第三步：创建每周文档

在知识库的"每周需求反馈情况 > 七月"文件夹下创建文档。

**文档格式模板：**

```markdown
7月第N周：2026年MM月DD日 - 2026年MM月DD日

# **售后反馈**

:::
**退款需求明细**

## 一、需求名称【讨论结果：回复结果】

**对应tb：**

[TB链接](TB链接)

**反馈商家：**

手机号

**时间线：**
- YYYY.MM.DD 催促背景描述

**承诺情况**：未承诺

**商家场景：**

场景描述

**反馈截图：**

**其他需求：**暂无
:::

# **销售反馈**

:::
**退款需求明细**

## **暂无**
:::

# **工单新增**

| 来源（上周） | 需产品介入工单 | 线上问题 | 线上优化 | 技术优化 |
|---|---|---|---|---|
| 工单系统（N月第N周） |  |  |  |  |
```

**注意事项：**
- 标题格式为 `## 一、需求名` —— 不要加多余的 `**` 包裹
- 售后无退款需求时写 `## **暂无**`
- 销售无退款需求时同样写 `## **暂无**`
- 工单数据留空，由用户手动补充

### 第四步：更新汇总表

汇总表 nodeId=`<汇总表NODE_ID>`，包含三个表格模块。

**⚠️ 关键限制：禁止使用 overwrite 模式覆写汇总表全文！** overwrite 会破坏表头的单元格背景色格式。只能使用 **append** 模式追加新行。

#### 模块1：重点需求反馈汇总

| 时间 | 签单需求 | 退款需求 | 续费需求 | 需求合计 |
|------|----------|----------|----------|----------|

- 签单需求 = 销售表上周含"签单卡点"的记录数
- 退款需求 = 售后表"马上退款" + 销售表"马上退款"
- 续费需求 = 售后表"不再续费" + 销售表"不再续费"
- 合计 = 三者之和

#### 模块2：售后反馈

| 来源 | 总需求 | 资损需求 | 退款需求 | 续费需求 | 多次催促需求 | 催促需求 |

- 来源：`[七月第N周](文档链接)`
- 总需求：售后表上周所有记录数（需用户提供）
- 各类型：数量（占比%）

#### 模块3：销售反馈

| 来源 | 总沟通人数 | 签单需求 | 退款需求 | 资损需求 | 续费需求 | 多次催促需求 |

- 总沟通人数：留空
- 各类型统计逻辑同上

## API 限制与应对

### 钉钉 AI 表格 query_records 限制

1. **每次最多返回100条** —— 无法获取全量数据
2. **sort 参数不生效** —— 无法按日期排序
3. **filters 参数不生效** —— 无法服务端过滤
4. **keyword 搜索只匹配文本/选项字段** —— 日期字段无法搜索

### 应对策略

- **低频类型**（马上退款/不再续费/产生资损）：keyword 搜索 + 本地日期过滤，100条足够覆盖
- **高频类型**（催促/多次催促/新增反馈商家）：100条不够覆盖全年数据，**必须向用户确认准确数字**
- **总记录数**：API 无法获取，**必须向用户确认**

### 何时需要向用户确认

生成汇总表时，以下数字需要用户在 AI 表格页面手动筛选后提供：
- 售后表上周总记录数
- 售后表上周"多次催促"数量
- 售后表上周"催促"数量

## 钉钉文档 MCP 注意事项

- 创建文档用 `create_document`，参数：`workspaceId` + `folderId` + `name` + `content`
- 更新文档用 `update_document`，参数：`nodeId` + `markdown` + `mode`（overwrite/append）
- markdown 内容最大 10000 字符，超过需分块 append
- **汇总表禁止 overwrite**（破坏表头背景色），只用 append

## Common Pitfalls

1. **overwrite 汇总表导致表头样式丢失** —— 钉钉文档 API 写入的 `background-color` 会被渲染为"文本突出显示色"而非"单元格背景色"。一旦 overwrite，表头格式不可逆地损坏。只用 append。

2. **query_records 返回100条以为是全量** —— API 不返回 hasMore=true（即使有更多数据），容易误以为数据完整。对高频类型必须向用户确认。

3. **标题格式写成 `## **一、**内容`** —— 照搬原文档的 span 标签后，`**` 变成孤立粗体符号。正确写法是 `## 一、内容`。

4. **keyword 搜日期** —— `keyword:"2026-07-22"` 不匹配日期字段，只匹配文本字段中含该字符串的记录。

5. **同一需求多次催促未合并** —— 按 TB 链接去重，时间线合并展示多次催促的背景。

6. **销售表的需求类型名称不同** —— 销售表用"签单卡点""商家催促""商家反馈"等，与售后表不完全一致。

## Verification Checklist

- [ ] 售后表 keyword:"马上退款" 结果已按日期过滤
- [ ] 销售表 keyword:"马上退款" 结果已按日期过滤
- [ ] 同一 TB 链接的多条记录已合并
- [ ] 文档标题格式正确（`## 一、内容`，无多余`**`）
- [ ] 文档已创建在正确的文件夹下
- [ ] 汇总表未使用 overwrite 模式
- [ ] 高频类型数据（催促/多次催促/总数）已向用户确认
- [ ] 重点汇总的退款/续费数为两表合计
