# API 编排与执行协议

执行前先加载 `kdzs-erp-api-connector`，具体参数和返回字段以连接器的 `assets/api-list.md` 为准。本文件只定义业务编排，不替代接口契约。

## 1. 认证门禁

1. 安全读取商家自己的 `appKey`、`appSecret` 和环境。
2. 按连接器当前要求获取 Token，并作为 `session` 参与签名。
3. 调用 `kdzs.erp.api.stock.list`：`{"pageNo":1,"pageSize":1}`。
4. 仅当 `code=200` 且 `data.success=true` 时继续。

不得在输出中展示 Token、完整 `appSecret` 或签名原文。服务端错误原样反馈，不猜测。

## 2. 时间窗口

使用业务时区中截止昨天的完整自然日：

- Q1：近 1 天
- Q3：近 3 天
- Q7：近 7 天
- Qprev7：再往前 7 天

记录每个窗口的 `startTime`、`endTime` 和时区。Q7 与 Qprev7 不能重叠。

## 3. 销售任务必须串行

接口：

- `kdzs.erp.api.trade.stockup.task.create`
- `kdzs.erp.api.trade.stockup.task.get`

每个账号最大并发数固定为 1：

```text
Q1 create → get同一taskId直到SUCCESS
→ Q3 create → get同一taskId直到SUCCESS
→ Q7 create → get同一taskId直到SUCCESS
→ Qprev7 create → get同一taskId直到SUCCESS
```

状态处理：

- `PROCESSING`：继续查询同一 `taskId`，禁止重复创建。
- `SUCCESS`：保存结果，进入下一窗口。
- `FAILED` / `NOT_FOUND`：原样反馈并停止正式计算。
- 超过执行时限：停止本次分析，说明任务仍在处理；不要无限轮询。
- 服务端返回 `1003:当前账号已有备货单生成任务，请稍后重试`：原样反馈，不并行重建。

四个窗口必须全部成功。禁止用缺失窗口生成正式增长率或采购量。

## 4. 订单状态口径

默认参数可采用 `queryVision=0`、`refundStatus=1`、`timeType=1`。`ALL_STATUS` 未经过真实订单抽样核对前，只能称“备货需求估算”，结果不得直接驱动采购写操作。

如果商家已经完成口径校准，记录：统计状态、退款规则、校准日期、抽样差异和负责人。不要在多个当前状态任务之间简单相加冒充一致性快照，因为任务结果不提供订单级去重键。

## 5. SKU 归一

从四个结果中抽取 `sysItemId`、`sysSkuId`、货品/规格名称和 `count`。以 `sysSkuId` 合并；同一窗口重复行先求和。缺少 `sysSkuId` 的行进入异常清单。

## 6. 库存查询

接口：`kdzs.erp.api.stock.list`。

连接器禁止未经用户授权自动翻页抓取全部库存，因此采用候选优先策略：

1. 先从销售结果识别有限候选。
2. 按 `sysItemAlias` 窄范围查询。
3. 返回结果必须用 `sysSkuId` 二次精确匹配。
4. 无匹配或多条冲突记录时停止该 SKU 计算。
5. 不得把“没查到”视为库存 0。

库存字段：

- 可配货：`salableItemDistributableStock`
- 采购在途：`transitItemStock`
- 实际总库存：`stockTotal`
- 已占用：`salableItemPreemptedNum`

可配货已经反映占用，不得再次扣减已占用库存。

## 7. 在途核对

`transitItemStock` 作为默认在途来源。可在用户明确范围内调用 `kdzs.erp.api.purchase.list` 核对 `purchaseNum - instockNum`，但两份在途不能相加。

若两者不一致，标记“在途数据冲突”，拦截采购写操作。没有 ETA 时，不能声称在途可以在断货前到达。

## 8. 可选采购写入

接口：`kdzs.erp.api.stock.purchase.create`。仅在用户看过最终明细并明确确认后调用。

- `purchaseItemList` 必须传 JSON 数组字符串。
- 数量字段是 `itemCount`。
- 每行必须包含 `sysItemId`、`sysSkuId`、`itemCount`。
- 建议批次必须有唯一 `recommendationId`、生成时间和有效期。
- 确认前重新查询库存和在途；变化后重新计算。
- 未实现幂等、多仓或供应商选择时，仅输出采购单明细，不调用接口。

创建成功后必须回传采购单编号或服务端可验证标识；无法验证时不得声称创建成功。
