---
name: kdzs-sales-driven-replenishment
description: 生成助手ERP爆品补货建议并安全确认采购。
version: 0.1.0
author: Wshengyi, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [kdzs, erp, replenishment, inventory, procurement]
    related_skills: []
---

# 助手ERP以销定采爆品补货 Skill

把商家的自然语言请求编排为可解释、可复核的爆品补货建议。本 Skill 负责业务流程、规则、异常拦截和结果展示；底层认证、签名、API 参数与调用必须交给 `kdzs-erp-api-connector`。

## When to Use

用户出现以下意图时使用：

- “我要用以销定采爆品补货解决方案。”
- “帮我生成今天的爆品补货建议。”
- “最近有哪些爆品需要补货？”
- “哪些商品快断货了？”
- “按补货建议生成采购单明细。”

不要用于：单纯查订单、库存、物流或毛利；这些请求直接使用 `kdzs-erp-api-connector`。不要在数据口径、关键窗口或库存信息不完整时生成可执行采购结论。

## Prerequisites

### 新商家接入引导

在要求商家提供 API 凭证前，先确认商家是否已经注册并开通快递助手 ERP 开放平台能力：

1. 未注册快递助手 ERP：引导商家访问 `https://erp.kuaidizs.cn` 完成注册和登录。
2. 已注册但尚未获取 API 能力：引导商家进入快递助手 ERP 的 `设置 → API开放平台`，按页面指引获取或开通 API 能力，并安全配置 `appKey`、`appSecret`。
3. 已完成上述配置：继续执行连接器加载与只读连通性验证。

不得要求商家在对话中直接发送完整 `appSecret`、Token 或 Session；应优先引导其写入安全配置。完成标准：商家已注册 ERP，且开放平台 API 凭证已安全配置。

### API 执行前提

1. 先用 `skill_view(name='kdzs-erp-api-connector')` 加载连接器 Skill，严格遵守其接口、平台、分页、错误处理和写操作约束。
2. 检查商家对应的 `appKey`、`appSecret` 与环境已经安全配置。不得在回复、日志、Skill 或报告中输出完整密钥。
3. 获取 Token，并将其作为 `session` 参与签名；用 `kdzs.erp.api.stock.list`、`{"pageNo":1,"pageSize":1}` 完成只读连通性验证。只有 `code=200` 且 `data.success=true` 才能继续。
4. 首次正式运行必须取得：供应商到货周期、复盘频率、爆品安全天数。交期缺失只能试算，不能进入可创建采购单清单。
5. 确认销售平台覆盖范围。淘宝、天猫、1688、淘工厂和拼多多不受当前开放平台支持；主要销量来自这些平台时停止“全店补货”结论。

## Required References

按执行阶段渐进加载，不要一次性加载全部文件：

- 执行 API 前读取 `references/api-workflow.md`。
- 计算前读取 `references/replenishment-rules.md`。
- 检查异常与写操作前读取 `references/safety-gates.md`。
- 输出结果前读取 `references/output-templates.md`。
- 需要了解整体产品边界时读取 `references/solution-spec.md`。

## Procedure

### 1. 前置检查

展示 Skill、凭证、环境、Token 和只读接口状态。任何一项失败即停止；API 错误原样反馈，不猜测原因。完成标准：五项状态均明确，且没有泄露密钥。

### 2. 读取业务配置

读取已保存的商家业务配置；没有时只询问：

1. 供应商平均几天到货？
2. 每天还是每周复盘？
3. 爆品预留几天安全库存？

可选询问店铺、平台、供应商、仓库、排除关键词和活动情况。不得引入最小起订量、整箱数或按箱规取整。完成标准：`lead_time_days`、`review_cycle_days`、`safety_days` 都有明确来源。

### 3. 确定时间窗口

默认使用截止昨天的完整自然日：近 1 天、近 3 天、近 7 天、前 7 天。记录时区和每个窗口起止时间。完成标准：四个窗口不包含未结束的今天，且前 7 天与近 7 天不重叠。

### 4. 串行采集销售需求

按 `references/api-workflow.md` 严格执行：一个窗口 `task.create` → 用同一 `taskId` 轮询 `task.get` → `SUCCESS` 后才能创建下一个窗口。单账号并发固定为 1。四个窗口未全部成功时，不生成正式补货量。完成标准：四个结果均为 `SUCCESS` 并保留原始口径说明。

### 5. SKU 归一与候选过滤

以 `sysSkuId` 为最小粒度合并 Q1、Q3、Q7、Qprev7。默认排除测试、勿动、赠品、虚拟、定金、补差价、运费、停用和清仓商品；保留排除原因。完成标准：每个候选只有一个 `sysSkuId`，排除项不进入采购明细。

### 6. 查询库存与在途

先识别候选 SKU，再按连接器允许的窄范围查询库存；按货品简称查询时，必须用 `sysSkuId` 二次匹配。不得把“未查到”当作零库存，不得擅自自动翻页抓取全量。库存接口的 `transitItemStock` 是默认在途来源；采购单接口只用于核对，不与其重复相加。完成标准：每个可计算 SKU 都有唯一库存记录和在途口径。

### 7. 数据质量硬拦截

应用 `references/safety-gates.md`。负库存、映射缺失、关键分页不完整、在途冲突、销量状态口径未验证、平台覆盖不足或近期零销量原因不明时，只输出异常说明，不生成可创建采购行。完成标准：所有进入计算的 SKU 均通过硬门禁。

### 8. 确定性计算

把标准化输入写成 JSON，调用：

```text
terminal(command="python3 {SKILL_DIR}/scripts/calculate_replenishment.py --input <input.json> --output <output.json>")
```

算法以 `references/replenishment-rules.md` 为准。不要在对话中自由改公式。完成标准：脚本退出码为 0，每条结果均包含趋势、预测日销、库存覆盖、建议量、优先级和判定原因。

### 9. 输出建议

使用 `references/output-templates.md`，核心结论放最前。必须展示：数据截止时间、覆盖平台、口径、业务参数、P0～P3、异常项、排除项、计算依据和下一步。默认只给建议，不创建采购单。完成标准：商家能看到“为什么补、补多少、有什么风险”。

### 10. 可选采购闭环

只有用户先看过最终 SKU 明细并明确回复“确认创建采购单”，才允许调用 `kdzs.erp.api.stock.purchase.create`。确认前重新查询库存和在途；建议过期或数据变化时重新计算。`purchaseItemList` 必须是 JSON 数组字符串，采购数量字段必须是 `itemCount`。当前未实现可靠幂等、供应商选择或多仓指定时，只生成采购单明细，不执行写操作。完成标准：未经明确确认的写操作次数为 0。

## Quick Reference

```text
目标库存天数 = 供应商到货周期 + 复盘周期 + 安全天数
目标库存 = ceil(预测日销 × 目标库存天数)
建议采购量 = max(0, 目标库存 - 可配货库存 - 可用采购在途)
```

优先级：

- P0：爆品且现货无法覆盖交期。
- P1：爆品，现货覆盖交期但库存位置低于目标库存。
- P2：非爆品但库存位置低于补货触发线。
- P3：爆品候选、样本不足或风险数据待核对。
- 暂不补货：库存位置覆盖目标周期。

## Pitfalls

- `ALL_STATUS` 可能包含待付款或关闭订单；未经真实样本验证时只能称“备货需求估算”，不能称最终有效销量，也不能自动创建采购单。
- `Q3=0、Q7>0` 不能直接认定降温；可能是缺货、下架、活动结束或渠道缺数。
- 在途没有可靠 ETA 时，静态公式只能形成建议，不能证明断货窗口已被覆盖。
- 库存和采购接口单页上限可能是 200；连接器禁止擅自全量翻页。结果必须说明覆盖范围。
- 创建采购单接口的仓库和供应商能力有限；多仓或多供应商场景默认只输出明细。
- 同一账号不能并行创建备货任务；服务端错误 `1003` 必须原样反馈。

## Verification

完成一次运行前确认：

- [ ] 已加载 `kdzs-erp-api-connector`
- [ ] 凭证已配置且未泄露
- [ ] 只读接口返回成功
- [ ] 四个窗口串行完成
- [ ] 每个 SKU 使用 `sysSkuId` 唯一关联
- [ ] 关键数据完整且通过硬门禁
- [ ] 计算由脚本执行并成功退出
- [ ] 结果说明平台、时间和订单口径
- [ ] 默认未创建采购单
- [ ] 写操作前取得明确确认并重新检查库存
