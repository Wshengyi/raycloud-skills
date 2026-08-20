#!/usr/bin/env python3
"""Deterministic sales-driven replenishment calculator (stdlib only)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)


def round4(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def blocked(item: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "sysSkuId": item.get("sysSkuId"),
        "name": item.get("name", ""),
        "status": "blocked",
        "priority": "异常",
        "suggested_purchase_qty": None,
        "write_eligible": False,
        "reasons": [reason],
    }


def calculate_item(item: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    sku = str(item.get("sysSkuId", "")).strip()
    if not sku:
        return blocked(item, "缺少sysSkuId")
    if item.get("excluded", False):
        result = blocked(item, str(item.get("exclusion_reason", "商品被排除")))
        result["status"] = "excluded"
        result["priority"] = "已排除"
        return result
    if not item.get("data_complete", True):
        return blocked(item, "关键数据不完整")
    if not item.get("stock_match_unique", True):
        return blocked(item, "库存记录无法按sysSkuId唯一匹配")

    try:
        q1 = number(item.get("q1", 0), "q1")
        q3 = number(item.get("q3", 0), "q3")
        q7 = number(item.get("q7", 0), "q7")
        qprev7 = number(item.get("qprev7", 0), "qprev7")
        available = number(item.get("available_stock"), "available_stock")
        transit = number(item.get("in_transit_stock", 0), "in_transit_stock")
        lead = number(item.get("lead_time_days", defaults["lead_time_days"]), "lead_time_days")
        review = number(item.get("review_cycle_days", defaults["review_cycle_days"]), "review_cycle_days")
        safety = number(item.get("safety_days", defaults["safety_days"]), "safety_days")
    except (KeyError, ValueError) as exc:
        return blocked(item, str(exc))

    if min(q1, q3, q7, qprev7, transit, lead, review, safety) < 0:
        return blocked(item, "销量、在途或业务天数不能为负数")
    if available < 0:
        return blocked(item, "可配货库存为负数，必须先核对库存")
    if q3 == 0 and q7 > 0 and not item.get("recent_zero_explained", False):
        return blocked(item, "近3天为0但近7天有销量，需核对缺货、下架、活动或渠道缺数")

    d1, d3, d7, dprev7 = q1, q3 / 3.0, q7 / 7.0, qprev7 / 7.0
    growth = None if dprev7 == 0 else (d7 - dprev7) / dprev7
    acceleration = None if d7 == 0 else (d1 - d7) / d7

    min_q7 = number(item.get("min_q7", defaults["min_q7"]), "min_q7")
    absolute_threshold = number(item.get("absolute_daily_threshold", defaults["absolute_daily_threshold"]), "absolute_daily_threshold")
    new_threshold = number(item.get("new_product_q3_threshold", defaults["new_product_q3_threshold"]), "new_product_q3_threshold")
    meets_scale = q7 >= min_q7 or d7 >= 2

    strong: list[str] = []
    ordinary: list[str] = []
    if dprev7 > 0 and d7 >= 1.5 * dprev7:
        strong.append("7日高增长")
    if item.get("is_top10", False):
        strong.append("头部销量")
    if q1 >= absolute_threshold:
        strong.append("绝对爆量")
    if dprev7 == 0 and q3 >= new_threshold:
        strong.append("新品起量")
    if d7 > 0 and d1 >= 1.5 * d7 and q1 >= 5:
        ordinary.append("短期加速")
    if d7 > 0 and d3 >= 1.2 * d7:
        ordinary.append("持续加速")

    hot_candidate = meets_scale and (bool(strong) or len(ordinary) >= 2)
    if hot_candidate and {"头部销量", "7日高增长"}.issubset(strong) and "持续加速" in ordinary:
        grade = "S"
    elif hot_candidate and "7日高增长" in strong and any(x in ordinary for x in ("短期加速", "持续加速")):
        grade = "A"
    elif hot_candidate:
        grade = "B"
    else:
        grade = "观察"

    if d7 == 0:
        trend, forecast = "无销量", 0.0
    elif dprev7 == 0 and q3 >= new_threshold and q1 > 0:
        trend, forecast = "新品", d3
    elif d1 < 0.5 * d7 and d3 < 0.8 * d7:
        trend, forecast = "下降", min(d3, d7)
    elif d1 >= 1.2 * d7 or d3 >= 1.1 * d7:
        trend, forecast = "上升", 0.5 * d1 + 0.3 * d3 + 0.2 * d7
    else:
        trend, forecast = "平稳", d7

    target_days = lead + review + safety
    target_stock = math.ceil(forecast * target_days)
    stock_position = available + transit
    trigger_stock = forecast * (lead + safety)
    suggested = max(0, math.ceil(target_stock - stock_position))
    cover_days = None if forecast <= 0 else available / forecast
    shortage_risk = cover_days is not None and cover_days < lead

    if suggested == 0:
        priority = "暂不补货"
    elif hot_candidate and shortage_risk:
        priority = "P0"
    elif hot_candidate and stock_position < target_stock:
        priority = "P1"
    elif not hot_candidate and stock_position < trigger_stock:
        priority = "P2"
    else:
        priority = "P3"

    warnings: list[str] = []
    if item.get("event_driven", False):
        warnings.append("活动或直播驱动，需要人工确认")
    if transit > 0 and not item.get("in_transit_eta_verified", False):
        warnings.append("采购在途ETA未确认，当前为静态试算")
    if not item.get("order_scope_verified", False):
        warnings.append("订单状态口径未验证，当前为备货需求估算")
    if not item.get("platform_scope_complete", True):
        warnings.append("平台覆盖不完整，不代表全店销量")
    if not item.get("in_transit_consistent", True):
        warnings.append("两处在途数据不一致")

    write_eligible = (
        suggested > 0
        and not warnings
        and item.get("purchase_context_verified", False)
        and item.get("idempotency_ready", False)
    )
    reasons = strong + ordinary
    reasons.append(f"趋势{trend}")
    if shortage_risk:
        reasons.append("现货无法覆盖供应商交期")
    elif suggested > 0:
        reasons.append("库存位置低于目标库存")
    else:
        reasons.append("库存位置覆盖目标周期")

    return {
        "sysSkuId": sku,
        "sysItemId": item.get("sysItemId"),
        "name": item.get("name", ""),
        "status": "ok",
        "priority": priority,
        "hot_grade": grade,
        "hot_candidate": hot_candidate,
        "trend": trend,
        "metrics": {
            "q1": q1, "q3": q3, "q7": q7, "qprev7": qprev7,
            "d1": round4(d1), "d3": round4(d3), "d7": round4(d7), "dprev7": round4(dprev7),
            "growth_rate": round4(growth), "acceleration": round4(acceleration),
            "forecast_daily": round4(forecast), "target_days": round4(target_days),
            "target_stock": target_stock, "available_stock": available,
            "in_transit_stock": transit, "stock_position": round4(stock_position),
            "trigger_stock": round4(trigger_stock), "available_cover_days": round4(cover_days),
        },
        "suggested_purchase_qty": suggested,
        "write_eligible": write_eligible,
        "signals": {"strong": strong, "ordinary": ordinary},
        "reasons": reasons,
        "warnings": warnings,
    }


def calculate(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "lead_time_days": payload.get("lead_time_days", 3),
        "review_cycle_days": payload.get("review_cycle_days", 1),
        "safety_days": payload.get("safety_days", 3),
        "min_q7": payload.get("min_q7", 14),
        "absolute_daily_threshold": payload.get("absolute_daily_threshold", 100),
        "new_product_q3_threshold": payload.get("new_product_q3_threshold", 6),
    }
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("items must be an array")
    results = [calculate_item(item, defaults) for item in items]
    return {
        "schema_version": 1,
        "result_count": len(results),
        "summary": {
            "p0": sum(r.get("priority") == "P0" for r in results),
            "p1": sum(r.get("priority") == "P1" for r in results),
            "p2": sum(r.get("priority") == "P2" for r in results),
            "p3": sum(r.get("priority") == "P3" for r in results),
            "blocked": sum(r.get("status") == "blocked" for r in results),
            "suggested_total": sum(r.get("suggested_purchase_qty") or 0 for r in results),
        },
        "results": results,
    }


def self_test() -> None:
    payload = {
        "lead_time_days": 5, "review_cycle_days": 1, "safety_days": 3,
        "items": [{
            "sysSkuId": "demo", "q1": 48, "q3": 120, "q7": 238, "qprev7": 112,
            "available_stock": 90, "in_transit_stock": 80, "is_top10": True,
            "order_scope_verified": True, "in_transit_eta_verified": True,
            "purchase_context_verified": True, "idempotency_ready": True,
        }],
    }
    result = calculate(payload)["results"][0]
    assert result["metrics"]["forecast_daily"] == 42.8, result
    assert result["metrics"]["target_stock"] == 386, result
    assert result["suggested_purchase_qty"] == 216, result
    negative = calculate({"items": [{"sysSkuId": "bad", "q7": 10, "available_stock": -1}]})["results"][0]
    assert negative["status"] == "blocked", negative
    print("self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = calculate(payload)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
