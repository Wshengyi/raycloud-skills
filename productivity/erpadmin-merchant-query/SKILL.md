---
name: erpadmin-merchant-query
description: "Use when querying merchant/user info from erpadmin.kuaidizs.cn (ERP运营管理系统). Covers authentication, API endpoint, batch phone lookup."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [erpadmin, kuaidizs, merchant, query, api]
    related_skills: [tb-raycloud-automation, kdzs-erp-api-connector]
---

# ERP Admin 商家信息查询

查询快递助手ERP运营管理系统 (erpadmin.kuaidizs.cn) 中的商家基础信息。

## Overview

erpadmin.kuaidizs.cn 是快递助手的内部商家运营管理后台，可以按手机号查询商家的基础信息，包括等级、地区、店铺数、打单量、到期时间、负责销售等。

系统需要内网访问 + 钉钉扫码登录认证，认证后通过 Cookie + JWT Bearer Token 调用 API。

## When to Use

- 需要根据手机号查询商家基础信息（等级、地区、平台店铺、打单量等）
- 批量查询多个商家的运营数据
- 验证需求池中商家的活跃度和使用情况

## 用户需要提供的信息

**每次新会话只需提供一次：**

> 在已登录的 erpadmin.kuaidizs.cn 页面，按 F12 打开 DevTools → Network 标签 → 随便点击一个 API 请求 → 右键 → **Copy → Copy as cURL** → 发给 Hermes。

原因：认证有两层（SSO cookie + JWT），两者都会过期且无法从外部预判有效期，必须由用户从浏览器活跃 session 中提取。browser_cookie3 因 Chrome 锁库问题不可靠，DevTools Copy as cURL 是唯一可靠方式。

---

## 认证方式

### 获取凭证

1. 用户在浏览器中登录 erpadmin.kuaidizs.cn（需要钉钉扫码）
2. 从浏览器 DevTools → Network 面板中，复制任意成功请求的 `Copy as cURL`
3. 需要的凭证：
   - `Authorization` header（Bearer JWT Token）
   - `Cookie` 中的 `ray-authentication` 和 `Admin-Token`

### 凭证结构

```
Authorization: Bearer <JWT_TOKEN>
Cookie: ray-authentication=<RAY_AUTH_VALUE>; Admin-Token=<JWT_TOKEN>
```

- `ray-authentication` 格式: `<uuid>_<ip>_<timestamp>_<username>`
- `Admin-Token` = JWT Token（与 Authorization header 中的一致）

### 通过 browser_cookie3 读取（可选）

```python
import browser_cookie3
cj = browser_cookie3.chrome(domain_name='erpadmin.kuaidizs.cn')
cookies = {c.name: c.value for c in cj}
jwt = cookies.get('Admin-Token', '')
ray_auth = cookies.get('ray-authentication', '')
```

**⚠️ PITFALL:** Chrome 运行时 Cookie DB 被锁，browser_cookie3 读到的可能是旧值。最可靠的方式是从 DevTools 的 Copy as cURL 中获取。

## API 接口

### 商家列表查询

```
POST https://erpadmin.kuaidizs.cn/erp/operationSystem/user/list
```

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json;charset=UTF-8
Accept: application/json, text/plain, */*
Cookie: ray-authentication=<RAY_AUTH>; Admin-Token=<JWT_TOKEN>
Referer: https://erpadmin.kuaidizs.cn/
x-requested-with: true
```

**Request Body:**
```json
{
  "total": 7940,
  "pageSize": 10,
  "pageNum": 1,
  "quickSearchType": "",
  "erpAccount": "手机号",
  "level": "",
  "renewedFlag": ""
}
```

- `erpAccount`: 搜索关键词（手机号）
- `pageSize`: 每页数量（最大可能为100）
- `pageNum`: 页码
- `total`: 可任意传，不影响结果

**Response:**
```json
{
  "total": 1,
  "code": 200,
  "msg": "查询成功",
  "list": [
    {
      "id": 2871,
      "erpAccount": "199****9009",
      "userId": "1263965",
      "version": "1",
      "level": "2",
      "platformShopInfo": "抖音:18;拼多多:13;快手:11",
      "category": "7",
      "categoryStr": "食品保健",
      "province": "吉林省",
      "city": "长春市",
      "county": "宽城区",
      "area": "吉林省长春市宽城区",
      "firstOrderTime": "2024-01-13T11:44:35",
      "lastOrderTime": "2025-11-20T17:33:14",
      "expiresTime": "2027-01-21T23:59:59",
      "hotSpot": "扣减库存，打印快递单，手工单",
      "hotSpotList": ["扣减库存", "打印快递单", "手工单"],
      "salesPerson": "金岑瑨",
      "implementorName": "赵万里",
      "lastLoginDate": 20260727,
      "lastLoginDateStr": "2026-07-27 00:00:00",
      "printCntL7": 5345,
      "printCntL15": 13817,
      "salesSourceStr": "自营电销一部二组",
      "itemCnt": 2262,
      "skuCnt": 38721,
      "settlementFlag": 1
    }
  ]
}
```

### 返回字段说明

| 字段 | 含义 |
|------|------|
| erpAccount | ERP账号（手机号，部分脱敏） |
| userId | 用户ID |
| version | 版本 |
| level | 等级（1/2/3...） |
| platformShopInfo | 平台店铺信息（格式: 平台:数量;...） |
| categoryStr | 商品品类 |
| area | 所在地区 |
| firstOrderTime | 首次下单时间 |
| lastOrderTime | 最近下单时间 |
| expiresTime | 到期时间 |
| hotSpot / hotSpotList | 高频使用功能 |
| salesPerson | 销售负责人 |
| implementorName | 实施负责人 |
| salesSourceStr | 销售来源渠道 |
| lastLoginDate | 最近登录日期 |
| printCntL7 | 近7天打印单量 |
| printCntL15 | 近15天打印单量 |
| itemCnt | 商品数 |
| skuCnt | SKU数 |
| settlementFlag | 结算标记 |
| latestVisitRecord | 最近拜访记录 |

## 批量查询示例

```python
import http.client, json, time

JWT = "<YOUR_JWT_TOKEN>"
COOKIES = f"ray-authentication=<YOUR_RAY_AUTH>; Admin-Token={JWT}"

headers = {
    "Authorization": f"Bearer {JWT}",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://erpadmin.kuaidizs.cn/",
    "Cookie": COOKIES,
    "x-requested-with": "true",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

def query_merchant(phone):
    body = json.dumps({
        "total": 7940,
        "pageSize": 10,
        "pageNum": 1,
        "quickSearchType": "",
        "erpAccount": phone,
        "level": "",
        "renewedFlag": ""
    })
    conn = http.client.HTTPSConnection("erpadmin.kuaidizs.cn", timeout=15)
    conn.request("POST", "/erp/operationSystem/user/list", body=body, headers=headers)
    resp = conn.getresponse()
    data = json.loads(resp.read().decode('utf-8'))
    conn.close()
    return data

# 批量查询
phones = ["19904479009", "18676118837", "15510181112"]
for phone in phones:
    result = query_merchant(phone)
    if result.get('code') == 200 and result.get('list'):
        m = result['list'][0]
        print(f"{phone}: {m.get('area','')} | {m.get('categoryStr','')} | 近7天打印:{m.get('printCntL7',0)} | 到期:{m.get('expiresTime','')}")
    else:
        print(f"{phone}: 未找到")
    time.sleep(0.5)  # 避免请求过快
```

## Common Pitfalls

1. **401 认证失败** — JWT 过期或 ray-authentication cookie 不正确。需要用户重新从浏览器获取最新凭证。
2. **302 重定向到 SSO** — 缺少 `ray-authentication` cookie。必须同时传 Cookie 和 Authorization header。
3. **路径错误** — API 路径是 `/erp/operationSystem/user/list`，不是 `/api/bd/user/list` 或 `/bd/user/page`。
4. **browser_cookie3 读到旧值** — Chrome 运行时锁 DB，必须关闭 Chrome 或用 DevTools 直接拷贝。
5. **请求方法** — 必须用 POST，不是 GET。
6. **搜索字段** — 用 `erpAccount` 字段传手机号搜索，不是 `phone`。

## 其他已知接口

| 路径 | 方法 | 用途 |
|------|------|------|
| `/system/user/impleatorRoleUser/list` | GET | 获取实施人员列表 |
| `/erp/operationSystem/user/list` | POST | 商家列表查询（核心） |

## Verification Checklist

- [ ] 有有效的 JWT Token 和 ray-authentication cookie
- [ ] POST 请求到 `/erp/operationSystem/user/list`
- [ ] Body 中 `erpAccount` 字段为手机号
- [ ] 同时传 Authorization header 和 Cookie
- [ ] 返回 `code: 200` 且 `list` 非空
