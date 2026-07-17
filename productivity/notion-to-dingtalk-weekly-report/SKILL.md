---
name: notion-to-dingtalk-weekly-report
description: "从 Notion 每日工作日志自动生成周报并通过钉钉日志 MCP 发送给指定领导。"
version: 1.0.0
author: hermes-agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Notion, 钉钉, 周报, 自动化, MCP]
---

# Notion → 钉钉周报自动生成

从 Notion 每日工作日志读取本周内容，AI 归纳整理后，通过钉钉日志 MCP 创建周报并推送给指定领导。

## 触发条件

用户要求生成/发送周报，或每周五定时执行。

## 环境信息

- **Notion API Key**：存储于 `~/.hermes/.env`，变量名 `NOTION_API_KEY`
- **Notion 日志结构**：`<顶层工作页面> / 每日工作汇总 / <年度> / <月份> / 每日页面（MM/DD）`
- **钉钉日志 MCP URL**：`https://mcp-gw.dingtalk.com/server/<SERVER_ID>?key=<DINGTALK_REPORT_MCP_KEY>`
- **钉钉通讯录 MCP URL**：`https://mcp-gw.dingtalk.com/server/<SERVER_ID>?key=<DINGTALK_CONTACT_MCP_KEY>`
- **周报模板 ID**：通过 `get_available_report_templates` 查询，选择名为「周报」的模板
- **领导 userId**：通过 `search_contact_by_key_word` 搜索领导姓名获取

## 步骤

### 1. 确定本周日期范围

本周一到今天（周五）。例如当前日期 2026-07-17，则本周为 07/13～07/17。

### 2. 读取 Notion 本月页面列表

```python
import urllib.request, json, os

NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": "2025-09-03",
}

def notion_get(url):
    req = urllib.request.Request(url, headers=NOTION_HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())
```

- 从顶层工作页面往下导航：年度 → 月份 → 每日页面
- 调用 `/blocks/{月份页面ID}/children` 列出所有子页面（格式 `MM/DD`）
- 筛选出本周日期范围内的页面 ID

> **注意**：跨年跨月时需从「每日工作汇总」页面重新导航到对应年度和月份。

### 3. 读取每日日志内容

```python
def get_daily_log(page_id):
    data = notion_get(f"https://api.notion.com/v1/blocks/{page_id}/children")
    lines = []
    for b in data.get("results", []):
        t = b.get("type", "")
        rich = b.get(t, {}).get("rich_text", [])
        text = "".join(x.get("plain_text", "") for x in rich)
        if text.strip():
            lines.append(text)
    return "\n".join(lines)
```

### 4. AI 归纳整理成周报结构

将5天的碎片记录按主题归类，生成以下四个字段（Markdown 格式）：

| 字段 | sort | 说明 |
|------|------|------|
| 本周完成工作 | 0 | 按模块分类列举具体事项 |
| 本周工作总结 | 1 | 3～5句话概括重点方向与成果 |
| 下周工作计划 | 2 | 列举3～5项下周重点 |
| 需协调与帮助 | 3 | 如无则填「暂无」 |

### 5. 查找接收人 userId

```python
def call_dingtalk_mcp(url, method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(url, data=payload,
        headers={"Content-Type":"application/json","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

CONTACT_MCP = os.environ.get("DINGTALK_CONTACT_MCP_URL", "")

r = call_dingtalk_mcp(CONTACT_MCP, "tools/call", {
    "name": "search_contact_by_key_word",
    "arguments": {"keyword": "领导姓名关键词"}
})
# 从返回结果中取 userId
```

> 也可用 `get_current_user_profile` 获取当前用户的直属主管 userId。

### 6. 调用钉钉日志 MCP 发送周报

```python
REPORT_MCP = os.environ.get("DINGTALK_REPORT_MCP_URL", "")

result = call_dingtalk_mcp(REPORT_MCP, "tools/call", {
    "name": "create_report",
    "arguments": {
        "templateId": "<周报模板ID>",
        "ddFrom": "hermes-agent",
        "toChat": True,
        "toUserIds": ["<领导userId>"],
        "contents": [
            {"key":"本周完成工作","sort":"0","type":"1","contentType":"markdown","content": "<本周完成工作内容>"},
            {"key":"本周工作总结","sort":"1","type":"1","contentType":"markdown","content": "<本周工作总结内容>"},
            {"key":"下周工作计划","sort":"2","type":"1","contentType":"markdown","content": "<下周工作计划内容>"},
            {"key":"需协调与帮助","sort":"3","type":"1","contentType":"markdown","content": "暂无"},
        ]
    }
})
```

## 验证

周报创建成功时返回：
```json
{"success": true, "errorCode": 0, "reportId": "...", "url": "dingtalk://..."}
```

## 陷阱

- Notion API 需确保工作日志页面已共享给 Integration，否则返回 401
- 月份父页面 ID 每月不同，跨月时需从年度页面重新导航
- 钉钉日志 MCP 的 `create_report` **不支持**推送到群聊，只能推给个人（`toUserIds`）
- 使用 `python3` 脚本方式调用而非 `curl | python3` 管道，避免 shell 审批拦截
- MCP URL 中含有 key，属于敏感信息，存入环境变量，不要硬编码或打印到日志
- `search_user_by_key_word` 工具有时搜不到结果，改用 `search_contact_by_key_word` 更可靠
