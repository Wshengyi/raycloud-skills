---
name: erp-weekly-progress-report
description: "Use when generating weekly product & engineering progress reports for 快递助手ERP project — fetching release/dev tasks from TB MCP and publishing to Yuque."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [erp, tb, teambition, yuque, weekly-report, productivity]
    related_skills: [tb-raycloud-automation]
---

# 快递助手ERP 产研进度周报生成

## Overview

从 TB (Teambition) MCP 服务拉取快递助手ERP项目的任务数据，生成产研进度周报并发布到语雀知识库。周报包含两大部分：上周发布内容 + 当前开发中任务。

## When to Use

- 用户要求生成 ERP 产研进度周报
- 用户要求查看上周上线/发布内容
- 用户要求查看当前开发中任务进度
- 每周定期生成并发布到语雀

## 数据源

### TB MCP Server

- **端点**: `https://ai.kuaidizs.cn/api/sse/mcp`
- **协议**: MCP Streamable HTTP (Spring AI), protocolVersion `2025-03-26`
- **项目ID**: `61b0497a4bcf8d29f911602e` (快递助手ERP)

### MCP 连接步骤

```bash
# 1. Initialize (获取 session)
curl -s -H "Accept: text/event-stream, application/json" \
  -H "Content-Type: application/json" \
  -X POST "https://ai.kuaidizs.cn/api/sse/mcp" \
  -D /tmp/mcp_headers.txt \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"hermes","version":"1.0"}}}'

# 从 response header 取 Mcp-Session-Id
SID=$(grep -i 'mcp-session-id' /tmp/mcp_headers.txt | tr -d '\r' | awk '{print $2}')

# 2. 发 initialized 通知
curl -s -H "Accept: text/event-stream, application/json" \
  -H "Content-Type: application/json" \
  -H "mcp-session-id: $SID" \
  -X POST "https://ai.kuaidizs.cn/api/sse/mcp" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'

# 3. 调用 tools/call
```

### 可用工具

- `queryTasksByTql` — TQL 语法查任务（核心）
- `querySupportedProjects` — 查项目列表
- `searchOrgMembers` — 搜企业成员
- `getProjectMembers` — 项目成员列表

### 钉钉文档 MCP

- **端点**: `https://mcp-gw.dingtalk.com/server/9a926600781309ad7220be14ce7eff4e9e3ab3dab5f9443908014cd63c5ada74?key=621bddfb52255f187a99dfef76118510`
- **协议**: MCP Streamable HTTP
- **知识库**: `R2PmK290kQOywXvp`（快递助手erp业务组）
- **产品周报文件夹**: `AR4GpnMqJzMLyKbZhKpKbXXxVKe0xjE3`
- **2026年7月文件夹**: `jb9Y4gmKWr7lmxrah4Zal4jnVGXn6lpz`
- **文档标题格式**: `助手erp业务周会_MM.DD`（MM.DD为生成当天日期）
- **自动创建月份文件夹**: 每月第一次运行时，如果当月文件夹不存在则自动创建（格式「YYYY年M月」）

## 任务状态 StatusId 映射（仅限 ERP 项目）

### 上线状态（isDone=0 除已完成外）

| 状态名 | statusId |
|--------|----------|
| 已完成 | `61b0497b4bcf8d29f9116035` (isDone=1) |
| 灰度 | `672dc348cfab6c001ee984eb` |
| p1 | `6205104ad2cda3003ceeb7b2` |
| p2 | `674ecaece61ed5001d3bdfe3` |
| p3 | `6971bd78fe685800225fffe4` |
| p4 | `6971bd81fe685800225ffff2` |

### 开发状态

| 状态名 | statusId |
|--------|----------|
| 待处理 | `61b0497b4bcf8d29f9116032` |
| 开发中 | `61b0497b4bcf8d29f9116033` |
| 测试中 | `61b0497b4bcf8d29f9116034` |
| 测试完成 | `62051089a6240e003381f027` |
| 待测试 | `61b8064c9d014b03d16f1741` |
| 待评审 | `631194b2e6c0ae001d9b32f2` |
| 方案设计中 | `671758469149cd001d714b12` |
| 联调中 | `62051001a6240e003381efba` |
| 待排查 | `64546d794ca592001dd3d110` |

## 任务字段映射

| 业务含义 | 字段 |
|---------|------|
| 提测时间 | `taskInfo.dueDate` |
| 预计上线时间 | `customfields` 中 `cfId = 6317537a0e4b7a4bdb3d8a89` |

## 周报结构

### 一、上周发布内容

分两大类：

#### 🟢 灰度发布到线上
- **定义**: 原状态为灰度/p1/p2/p3/p4，上周变更为「已完成」
- **查询方式**: `isDone = true AND accomplished >= 上周一UTC AND accomplished <= 上周日UTC AND onlyTopTask = true`
- **表头**: # | 任务标题 | 上线日期

#### 🔵 新上线
- **定义**: 原状态为其他（开发/测试等），上周变更为灰度/p1/p2/p3/p4
- **查询方式**: `isDone = false AND updated >= 上周一UTC AND updated <= 上周日UTC AND onlyTopTask = true`，然后本地过滤 statusId ∈ {灰度,p1,p2,p3,p4}
- **表头**: # | 任务标题 | 上线日期 | 上线环境

### 二、开发中任务

**筛选条件**:
1. 在当月活跃迭代中（`_sprintId IN (...)`）
2. 执行人非空
3. 执行人不是产品经理：王升一(`62317ac9a123364cb9e73f23`)、倪苏杭(`5cab0ae9accc3300017bc837`)、王宇波(`5c6684a090a47a0001b7d68a`)
4. 任务状态不是：已完成、灰度、p1、p2、p3、p4
5. 仅主任务（`onlyTopTask = true`）

**表头**: # | 任务标题 | 任务状态 | 提测时间 | 上线时间

## 模块排序规则

固定顺序：订单 → 打印 → 售后 → 备货单 → 快销 → 商品库存 → 铺货 → 分销 → 报表&直播 → 云仓 → 公共 → 小程序 → 平台 → 其他

### 模块识别（从【xxx】提取）

| 关键词 | 模块 |
|--------|------|
| 订单 | 订单 |
| 打印、后置打印 | 打印 |
| 售后 | 售后 |
| 备货单 | 备货单 |
| 快销 | 快销 |
| 商品、库存 | 商品库存 |
| 铺货 | 铺货 |
| 分销 | 分销 |
| 报表、直播 | 报表&直播 |
| 云仓 | 云仓 |
| 公共、前端、设置 | 公共 |
| 小程序 | 小程序 |
| 平台、店铺、全平台 | 平台 |
| 其他 | 其他（放平台后面） |

## 格式要求（标准模板 — 以 07.13 文档为准，不得变更除非用户明确指示）

完整格式结构如下，**必须严格遵循**：

```markdown
## 一、上周发布内容（2026年第XX周 M.DD-M.DD）

---

### 🟢 灰度发布到线上（N条）
> 上周由灰度/p1/p2/p3/p4 变更为「已完成」，正式全量上线   

**订单**

| # | 任务标题 | 上线日期 |
|---|------------|------------|
| 1 | ... | MM-DD |

**售后**
...

---

### 🔵 新上线（N条）
> 上周由开发/测试状态变更为「灰度/p1/p2/p3/p4」，进入预发布环境   

**订单**

| # | 任务标题 | 上线日期 | 上线环境 |
|---|------------|------------|------------|
| 1 | ... | MM-DD | 灰度/p3/p4 |

---

## 二、开发中任务（截至 YYYY-MM-DD）

**合计：** N条（X月当月迭代，技术已承接，未发布）
> 筛选逻辑：在当月活跃迭代中 \+ 执行人非空且不是产品（王升一/倪苏杭/王宇波） \+ 任务状态为开发中/测试中等（不含已完成/灰度/p1-p4）   

### 订单（N条）

| # | 任务标题 | 任务状态 | 提测时间 | 上线时间 |
|---|------------|------------|------------|------------|
| 1 | ... | 测试中 | MM-DD | MM-DD |

### 打印（N条）
...
```

关键格式规则：
- 一级标题用 `##`，周次格式 `2026年第XX周 M.DD-M.DD`
- 灰度/新上线子标题用 `###`，带 `（N条）` 计数 + `>` 引用说明行
- 各章节之间用 `---` 分隔
- 上周发布中，模块标题用 `**模块名**`（粗体，不带条数）
- 开发中任务标题用 `## 二、开发中任务（截至 YYYY-MM-DD）`，带合计和筛选逻辑
- 开发中的模块标题用 `### 模块名（N条）`（H3带条数）
- 每个模块内序号从 **1** 开始（不全局连续递增）
- 上线日期只保留 `MM-DD`，不要具体时间
- 开发中任务按状态排序：测试完成→测试中→联调中→待测试→开发中→待处理→待评审→方案设计中→待排查
- 无顶部 `# 快递助手ERP产研进度周报` H1 标题（直接从 `## 一、` 开始）

## 钉钉文档发布步骤

**MCP 端点**: `https://mcp-gw.dingtalk.com/server/9a926600781309ad7220be14ce7eff4e9e3ab3dab5f9443908014cd63c5ada74?key=621bddfb52255f187a99dfef76118510`

**协议**: MCP Streamable HTTP（无需 session header，直接 POST）

**知识库**: `R2PmK290kQOywXvp`（快递助手erp业务组）
**产品周报文件夹**: `AR4GpnMqJzMLyKbZhKpKbXXxVKe0xjE3`

### 发布流程

1. 调用 `list_nodes(folderId=AR4GpnMqJzMLyKbZhKpKbXXxVKe0xjE3)` 查看子文件夹
2. 查找名称为当月的文件夹（格式「YYYY年M月」，如「2026年8月」）
3. 如不存在，调用 `create_folder(name="YYYY年M月", folderId="AR4GpnMqJzMLyKbZhKpKbXXxVKe0xjE3")` 创建
4. 在月份文件夹下调用 `create_document(name="助手erp业务周会_MM.DD", folderId=月份文件夹ID, markdown=内容)`
5. 如果 markdown 超过 9500 字符，必须分块上传：先 `update_document(mode="overwrite", markdown=chunk1)`，再 `update_document(mode="append", markdown=chunk2)`
   - **切分点必须落在空行处**（即切分点前后都不是 `|` 开头的表格行），否则 append 时钉钉会转义被截断表格的 `|` 和 `+`，导致格式损坏
   - 切分算法：从9500字符处向前找，直到找到一行前后都不是表格行的空行为止
   - 注意：`update_document` 的 mode 是 `overwrite`（不是 `replace`）和 `append`

**文档标题格式**: `助手erp业务周会_MM.DD`（MM.DD 为当天日期）

### 已知月份文件夹 ID

- 2026年7月: `jb9Y4gmKWr7lmxrah4Zal4jnVGXn6lpz`
- 2026年8月: `dQPGYqjpJYg0lZOdIBb26dOyWakx1Z5N`

### 可用工具

| 工具 | 用途 |
|------|------|
| `list_nodes` | 列出文件夹/知识库子节点 |
| `create_folder` | 创建文件夹 |
| `create_document` | 创建钉钉在线文档（markdown，≤10000字符） |
| `update_document` | 更新/追加文档内容 |
| `rename_document` | 重命名文档 |
| `search_documents` | 按关键词搜索文档 |
| `get_document_content` | 获取文档 markdown 内容 |
| `get_document_info` | 获取文档元信息 |

## 语雀备用发布流程（钉钉文档写入失败时启用）

当钉钉文档 MCP 的目录读取或文档写入出现认证失败、服务异常、超时等问题，且产研周报内容已经整理完成时，改用语雀作为备用发布目标，不要因钉钉写入失败而丢弃已整理的数据。

### 备用目标

- **知识库**：`senyi/gyt78a`（快递助手ERP 项目文档）
- **目标分组**：`快递助手ERP_发布日志`，TOC UUID：`3L-_pYprmmvNcFer`
- **文档标题格式**：`快递助手ERP 产研进度日志 — 2026年第N周（M.D-M.D）`
- **内容格式**：沿用本技能规定的标准周报格式，不因发布目标切换而改变正文结构、模块顺序或统计口径。

### 执行步骤

1. 先确认钉钉文档写入失败的具体错误；读取成功但 `update_document`/`create_document` 失败时，也可直接启用备用流程。
2. 在语雀知识库中按标题或 slug 检查是否已有同周文档，避免重复创建。
3. 若不存在，调用语雀创建文档：`POST /repos/senyi/gyt78a/docs`，使用 `format=markdown`、标准标题和已生成的周报正文。
4. 若已存在，调用语雀更新文档：`PUT /repos/senyi/gyt78a/docs/{doc_id}`，覆盖同周文档正文，避免产生副本。
5. 创建后必须将文档挂载到「快递助手ERP_发布日志」分组：调用 `PUT /repos/senyi/gyt78a/toc`，使用 `action=appendNode`、`action_mode=child`、`target_uuid=3L-_pYprmmvNcFer`、`doc_ids=[doc_id]`。
6. 写入完成后通过语雀 `GET /repos/senyi/gyt78a/docs/{doc_id}` 回读，校验标题、正文长度以及“一、上周发布内容”“二、开发中任务”等关键章节。
7. 最终回复中明确说明：钉钉文档写入失败，已改写入语雀，并提供语雀文档链接；不得声称钉钉文档已更新。

### 认证与安全

- 优先使用已配置的语雀 MCP；MCP 不可用时使用 REST API。
- REST API 使用 `YUQUE_API_TOKEN` 或用户当前提供的有效个人 Token；Token 只用于当前调用，不写入技能文件、日志、回复或长期记忆。
- 语雀创建/更新和 TOC 挂载都必须分别核验返回结果；任何一步失败都要如实报告。
- 若语雀也无法写入，不创建不完整文档，不使用旧数据或估算内容冒充成功。


1. 创建文档到知识库 `senyi/gyt78a`
2. 把文档挂到「发布日志」分组下（更新 TOC）

```python
# 创建文档
POST /repos/senyi/gyt78a/docs
{title, body, format: "markdown"}

# 挂到发布日志分组
PUT /repos/senyi/gyt78a/toc
{action: "appendNode", action_mode: "child", target_uuid: "3L-_pYprmmvNcFer", doc_ids: [doc_id]}
```

**注意**: 语雀 body_lake 字段只读，通过 API 修改不会生效。表格列宽/自适应只能在语雀编辑器手动设置。

## TQL 注意事项

- TQL **不支持** `_taskflowstatusId` 筛选和 `NOTIN` 操作符
- 需要按 statusId 过滤时，先拉全量再本地过滤
- 日期用 UTC ISO8601（CST -8h），如上周一 CST 00:00 = 前一天 UTC 16:00
- `pageSize` 最大 100，超过需要用 `nextPageToken` 翻页
- 建议始终带 `_projectId` 限定项目范围

## 钉钉文档 MCP（备选发布目标）

- **端点**: `https://mcp-gw.dingtalk.com/server/9a926600781309ad7220be14ce7eff4e9e3ab3dab5f9443908014cd63c5ada74?key=621bddfb52255f187a99dfef76118510`
- **协议**: MCP Streamable HTTP，无需 session header
- **关键工具**: `create_document`（name + markdown 内容）、`list_nodes`（遍历知识库/文件夹）、`search_documents`
- **内容限制**: markdown 内容上限 10000 字符，超出需分块上传（overwrite + append）。切分点必须落在空行处（不在表格内部），否则被截断的表格行会被钉钉 API 转义管道符。
- **注意**: markdown 中换行必须是真实换行符 `\n`，不能是字面量 `\\n`
- **mode 参数**: `overwrite`（覆盖）或 `append`（追加），不是 `replace`

## Common Pitfalls

1. **TQL NOTIN 不可用** — 不能用 TQL 直接排除产品经理的 executorId，必须全量拉取后本地过滤。
2. **灰度/p1-p4 是 isDone=false** — 不能只查 `isDone=true` 就认为是全部上线任务。上线 = isDone=true（已完成）+ isDone=false 但 statusId 是灰度/p1/p2/p3/p4。
3. **上周时间范围要用 UTC** — CST 周一 00:00 对应 UTC 前一天 16:00。
4. **TB MCP session 会过期** — 每次调用前重新 initialize 获取新 session。钉钉文档 MCP 不需要 session。
5. **shell 双引号转义** — TQL 里的双引号在 shell 里容易出错，建议写入文件后用 `-d @file.json` 传递。
6. **钉钉文档 markdown 10000 字符限制** — create_document 最多10000字符，超出需分块。
7. **钉钉文档月份文件夹** — 文件夹名称格式是「YYYY年M月」（不补零：7月，不是07月），需先查再创。
8. **开发中任务必须剔除上线状态** — 不仅排除 isDone=true，还要排除灰度/p1/p2/p3/p4 的 statusId。
9. **模块序号每模块从1开始** — 用户明确要求每个模块的表格序号独立编号，不全局连续。
10. **TB MCP 的 SSE 响应格式** — 返回数据在 `data:` 前缀的 SSE event 行里，需要 `re.search(r'^data:(.+)$', content, re.MULTILINE)` 提取。任务列表在 `result.tasks`（不是 `result.data`）。
11. **上线内容分类逻辑** — "灰度发布到线上"是状态从灰度/p1-p4 变为已完成（查 isDone=true + accomplished 上周）；"新上线"是从其他状态变为灰度/p1-p4（查 isDone=false + updated 上周 + statusId 匹配）。两者不重叠。
12. **分块切分禁止落在表格内部** — append 被截断表格行时，钉钉文档 API 会自动转义 `|` 为 `\|`、`+` 为 `\+`，导致表格格式完全损坏。切分时向前扫描到安全空行（前后行都不以 `|` 开头）。
13. **任务标题中的 `+` 不要转义** — TB 返回的标题可能含 `+`（如「多次催促+2个商家反馈」），写入 markdown 时**不要**用 `\+`，直接保留原文 `+`。钉钉文档读取时会显示 `\+` 但那是 API 返回的转义表示，实际渲染正确。生成内容时确保源文本无 `\+`。
14. **update_document mode 参数** — 正确值为 `overwrite`（覆盖全文）和 `append`（追加）。**不是** `replace`（会报错 invalidRequest）。
15. **格式不得擅自变更** — 用户明确要求以 07.13 文档为标准格式模板，在没有收到修改命令前不得改变输出格式。结构差异（如模块标题级别、分隔线、计数、说明行等）都属于格式变更。
## 支持脚本

- `scripts/safe_split.py` — 钉钉文档分块上传安全切分工具，确保切分点不落在表格内部。可直接 `python3 scripts/safe_split.py /tmp/weekly_report.md` 使用，或 `from safe_split import safe_split` 导入。

## Verification Checklist

- [ ] MCP session 建立成功
- [ ] 灰度发布到线上任务查全（isDone=true + accomplished 在上周范围）
- [ ] 新上线任务查全（isDone=false + updated 在上周 + statusId 匹配）
- [ ] 开发中任务已剔除已完成/灰度/p1/p2/p3/p4 状态
- [ ] 开发中任务已剔除空执行人和产品经理
- [ ] 模块排序正确（订单→打印→售后→...→平台→其他）
- [ ] 每模块序号从1开始
- [ ] 无顶部 H1 标题，一级标题含年度周次
- [ ] 灰度/新上线标题含条数和引用说明行，章节间有 `---`
- [ ] 开发中模块用 `### 模块名（N条）`，上周发布模块用 `**模块名**`
- [ ] 分块上传时切分点不在表格行内（使用 safe_split 逻辑）
- [ ] 钉钉文档创建/更新成功并返回有效 URL
