# API编排

## 主数据源

| 阶段 | API | 分组/作用 |
|---|---|---|
| 整体 | `kdzs.erp.api.report.gross.profit` | `queryGroupType=10` 概览总览 |
| 平台 | `kdzs.erp.api.report.gross.profit` | `queryGroupType=1` |
| 店铺 | `kdzs.erp.api.report.gross.profit` | `queryGroupType=2` |
| 货品 | `kdzs.erp.api.report.gross.profit` | `queryGroupType=3`，详细版按需 |
| SKU | `kdzs.erp.api.report.gross.profit` | `queryGroupType=4`，详细版按需 |
| 售后 | `kdzs.erp.api.refund.stats` | `PLATFORM`、`SHOP`、`REASON` |
| 物流 | `kdzs.erp.api.report.logistics` | 发货时间范围内的预警与异常 |
| 明细 | `kdzs.erp.api.trade.list` / `refund.list` | 仅异常下钻 |

## 推荐顺序

```text
版本确认
→ Token和只读连接验证
→ 毛利润总览
→ 平台
→ 店铺
→ 售后平台/店铺/原因
→ 物流
→ 详细版按需读取货品/SKU
→ 异常对象按需读取明细
```

## 时间口径

- 销售利润默认 `queryTimeType=2`（付款时间）。
- 售后默认 `timeType=1`（申请时间）。
- 物流按 `sendTimeStart`、`sendTimeEnd`（发货时间）。
- 报告必须分别注明三种时间口径。

## 关键字段

- 销售额：`payment`
- 净销售额：`netSales`
- 订单数：`ptTidCount`
- 销量：`number`
- 销售毛利：`paymentProfit`
- 销售毛利率：`paymentProfitMargin`
- 接口口径净利润：`netSalesProfit`
- 净利润率：`netSalesProfitMargin`
- 销售报表退款金额：`refundAmount`
- 售后申请数：`refundCount`
- 售后申请金额：售后统计的 `refundAmount`

## 限制

- 单页通常最多200条；禁止擅自循环翻页或拆时间绕过限制。
- 聚合优先，明细按需。
- `total > pageSize` 或总数与返回行不一致时，标记不完整并停止相关正式结论。
- 不支持淘宝、天猫、1688、淘工厂和拼多多。
