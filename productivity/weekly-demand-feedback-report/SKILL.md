---
name: weekly-demand-feedback-report
description: "每周需求反馈情况整理：从钉钉AI表格提取退款需求，写入钉钉文档，更新汇总表。"
triggers:
  - 每周需求反馈
  - 需求催促反馈表
  - 七月第几周
  - 退款需求整理
  - 汇总表更新
---

# 每周需求反馈情况整理

## 数据来源

| 表格 | baseId | tableId | 说明 |
|---|---|---|---|
| 售后催促需求汇总 | `YMyQA2dXW793dgQZTkKoXBpeJzlwrZgb` | `QiDEMvH` | 需求催促反馈表 |
| 销售需求反馈汇总 | `a9E05BDRVQ6L3R7yHppgglx4J63zgkYA` | `QiDEMvH` | 需求催促反馈表 |

- **AI 表格 MCP URL**: `https://mcp-gw.dingtalk.com/server/<AI_SHEET_TOKEN>?key=<AI_SHEET_KEY>`
- **钉钉文档 MCP URL**: `https://mcp-gw.dingtalk.com/server/<DOC_TOKEN>?key=<DOC_KEY>`
- **知识库**: `R2PmK290kQOywXvp`（快递助手erp业务组）
- **每周需求反馈情况文件夹**: 路径：用户分析 → 需求分析 → 每周需求反馈情况 → 月份文件夹
  - 七月文件夹 folderId: `jb9Y4gmKWr7lmxrah4Z7Eg5aVGXn6lpz`
- **汇总表 nodeId**: `ZgpG2NdyVXrOqRxzHAbD7knY8MwvDqPk`

## 字段说明（两张表相同字段名，options 略有差异）

| fieldId | 字段名 | 类型 |
|---|---|---|
| `AJfe8sL` | 需求名称 | text |
| `FTJcv6C` | 需求链接（TB链接） | url |
| `cSIqHZz` | 反馈时间 | date |
| `yBiZkVE` | 需求类型 | multipleSelect |
| `GHsMWDx` | 催促商家手机号 | text |
| `TTyRnwe` | 催促背景 | text |
| `xmJTQac` | 评估结论（含原因） | text |
| `sSyp8L0` | 需求回复结果 | singleSelect |
| `E7mOs0L` | 模块 | singleSelect |
| `1VYxIRE` | 催促人员 | user |

售后表需求类型 options（name→optionId）：
- 催促 → `xKHsk1t5Zr`
- 多次催促 → `Mq8Jv2t15w`
- 新增反馈商家 → `PlFboeEJsv`
- 不再续费 → `988hyxhLBw`
- 马上退款 → `A8SupYrGQr`
- 产生资损 → `wlCKtiY0Cy`

## 每周整理步骤

### 第一步：获取当周退款需求（写入周文档）

筛选条件：**反馈时间 = 上周** + **需求类型包含"马上退款"**

⚠️ **API 关键坑**：`query_records` 的 `filters`、`sort` 实测均不生效，只返回默认前100条。**必须用 `keyword` 搜索绕过**：

```python
# 用 keyword="马上退款" 搜索，本地按日期过滤
records = query_by_keyword(base_id, table_id, "马上退款")
week_records = [r for r in records if start_date <= parse_date(r) <= end_date]
```

- 售后表 → 写入"售后反馈"章节
- 销售表 → 写入"销售反馈"章节（上周无数据则写"暂无"）

### 第二步：创建周文档

```python
# 创建文档
create_document(workspaceId="R2PmK290kQOywXvp", folderId="<月份folderId>", name="X月第Y周", content=md)
```

**文档格式要点**：
- 标题行：`X月第Y周：起止日期`（无 H1）
- 章节标题：`# **售后反馈**` / `# **销售反馈**` / `# **工单新增**`
- 需求编号标题：`## 一、需求名称【讨论结果：xxx】`（不要用 `## **一、**` 格式，多余的 `**` 很难看）
- 内含 `:::` callout 块包裹退款明细

### 第三步：统计数量（用于汇总表）

获取全量上周数据需要对**每个类型关键词**分别 keyword 搜索，再取 recordId 并集：

```python
ALL_KEYWORDS = ["催促", "多次催促", "新增反馈商家", "不再续费", "马上退款", "产生资损"]
all_week = {}
for kw in ALL_KEYWORDS:
    for r in query_by_keyword(base_id, table_id, kw):
        if is_last_week(r):
            all_week[r["recordId"]] = r["cells"]
total = len(all_week)
```

⚠️ **注意**：即使这样也可能不全（如果存在不含任何上述关键词的记录）。建议与用户确认总数后再计算比例。

统计各类型：
```python
def count_type(tag):
    return sum(1 for c in all_week.values()
               if tag in [t["name"] for t in c.get("yBiZkVE", [])])
```

### 第三步（补充）：向用户确认无法通过 API 获取的数据

以下数据 API 无法准确获取，**必须请用户在 AI 表格页面手动筛选后提供**：

| 数据项 | 原因 |
|--------|------|
| 售后表上周**总记录数** | API 无法全量分页，只返回100条 |
| 售后表上周**多次催促**数量 | 全年记录远超100条，keyword搜索覆盖不全 |
| 售后表上周**催促**数量 | 同上 |
| **工单数据** | 来自工单系统，用户自己填写 |

以下数据 API 可准确获取（全年记录少，keyword 100条够覆盖）：
- 马上退款（售后+销售）、不再续费（售后+销售）、产生资损（售后）、签单卡点（销售）

### 第四步：更新汇总表

汇总表 nodeId: `ZgpG2NdyVXrOqRxzHAbD7knY8MwvDqPk`

⚠️ **禁止对汇总表使用 overwrite 全文**：会破坏表头单元格背景色（API写入的background-color渲染为文字高亮色，不可逆）。

**正确做法**：读取文档 → 找到上周行后面插入新行 → 分段写回

```python
# 获取当前文档
md = get_document_content(nodeId)

# 在各表末行后拼接新行
old = "| 上周行内容 |"
new = old + "\n| 本周行内容 |"
md = md.replace(old, new, 1)

# 分两段写回（文档超 10000 字符限制）
split_idx = md.index("\n# **销售反馈**")
part1, part2 = md[:split_idx], md[split_idx:]
update_document(nodeId, part1, mode="overwrite")   # 前半段（含售后表头）
update_document(nodeId, part2, mode="append")       # 后半段
```

各表新行格式：
1. **重点需求反馈汇总**：`| 月份第X周 | 签单 | 退款 | 续费 | 合计 |`
   - 签单 = 销售表"签单卡点"数
   - 退款 = 售后"马上退款" + 销售"马上退款"
   - 续费 = 售后"不再续费" + 销售"不再续费"
2. **售后反馈**：`| [周文档](url) | 总数 | 资损(%) | 退款(%) | 续费(%) | 多催(%) | 催促(%) |`
3. **销售反馈**：`| [周文档](url) |  | 签单(%) | 退款(%) | 0 | 续费(%) | 多催(%) |`（总沟通人数留空）

## 常见坑

1. **汇总表 overwrite 破坏表头** — 一旦 overwrite，表头单元格背景色丢失需用户手动恢复
2. **`**其他需求：**暂无` 被转义** — 写入后 `**` 变成 `\*\*`，需检查并 replace 修复
3. **需求编号标题** — 用 `## 一、需求名称`，不要用 `## **一、**需求名称`
4. **工单表头背景色** — API 新建文档时无法还原橙色背景，需用户手动调
5. **同一需求多次催促** — 按 TB 链接去重，时间线合并多条
6. **keyword 不匹配日期** — 不能用日期字符串搜索，只匹配文本/选项字段
