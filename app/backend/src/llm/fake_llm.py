"""Fake LLM implementation using rule-based logic."""
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal
from ..llm.adapter import LLMAdapter


class FakeLLM(LLMAdapter):
    """Rule-based fake LLM for generating structured outputs."""

    async def generate_diagnosis(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate diagnosis report using rules."""
        insights = []
        risks = []
        next_actions = []

        cvr = metrics.get("cvr", 0.0)
        epc = metrics.get("epc", Decimal("0.00"))
        refund_rate = metrics.get("refund_rate", 0.0)
        commission_rate = metrics.get("commission_rate", 0.0)
        orders = metrics.get("orders", 0)

        # Generate insights based on metrics
        if cvr < 2.0:
            insights.append({
                "type": "opportunity",
                "title": "转化率偏低",
                "description": f"当前转化率 {cvr}% 低于行业平均水平（2-5%），存在提升空间",
                "evidence": [
                    {
                        "metric": "CVR",
                        "value": f"{cvr}%",
                        "comparison": "行业平均 2-5%",
                        "time_window": window,
                    }
                ],
                "impact": "high",
            })
            next_actions.append("优化内容素材，提升点击到订单的转化率")

        if epc < Decimal("50.00"):
            insights.append({
                "type": "opportunity",
                "title": "平均订单价值偏低",
                "description": f"EPC {epc} 元，建议提升客单价或优化商品组合",
                "evidence": [
                    {
                        "metric": "EPC",
                        "value": f"{epc} 元",
                        "comparison": "目标 >50 元",
                        "time_window": window,
                    }
                ],
                "impact": "medium",
            })

        if refund_rate > 10.0:
            risks.append({
                "type": "risk",
                "title": "退款率异常",
                "description": f"退款率 {refund_rate}% 超过正常范围（<10%），需要关注商品质量或服务",
                "evidence": [
                    {
                        "metric": "退款率",
                        "value": f"{refund_rate}%",
                        "comparison": "正常 <10%",
                        "time_window": window,
                    }
                ],
                "impact": "high",
            })
            next_actions.append("排查高退款商品，优化商品描述和客户服务")

        if commission_rate > 20.0:
            risks.append({
                "type": "risk",
                "title": "佣金成本率偏高",
                "description": f"佣金成本率 {commission_rate}% 可能影响利润",
                "evidence": [
                    {
                        "metric": "佣金率",
                        "value": f"{commission_rate}%",
                        "comparison": "建议 <20%",
                        "time_window": window,
                    }
                ],
                "impact": "medium",
            })

        if orders > 0:
            insights.append({
                "type": "trend",
                "title": "订单量稳定",
                "description": f"过去 {window} 内产生 {orders} 笔订单",
                "evidence": [
                    {
                        "metric": "订单数",
                        "value": str(orders),
                        "time_window": window,
                    }
                ],
                "impact": "low",
            })

        summary = f"在过去 {window} 内，"
        if entity_type == "taoke":
            summary += f"淘客 {entity_id} 的转化率为 {cvr}%，EPC 为 {epc} 元。"
        else:
            summary += f"商家 {entity_id} 的 GMV 为 {metrics.get('gmv', 0)} 元，退款率为 {refund_rate}%。"

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "window": window,
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "insights": insights,
            "risks": risks,
            "next_actions": next_actions,
        }

    async def generate_opportunities(
        self, entity_type: str, entity_id: int, metrics: Dict[str, Any], window: str
    ) -> Dict[str, Any]:
        """Generate opportunities using rules."""
        opportunities = []

        cvr = metrics.get("cvr", 0.0)
        epc = metrics.get("epc", Decimal("0.00"))
        refund_rate = metrics.get("refund_rate", 0.0)
        commission_rate = metrics.get("commission_rate", 0.0)
        clicks = metrics.get("clicks", 0)

        # Opportunity 1: Improve CVR
        if cvr < 3.0:
            opportunities.append({
                "id": "opp_1",
                "title": "提升转化率",
                "description": f"当前 CVR {cvr}% 有提升空间，通过优化内容质量和商品匹配度可提升至 3-5%",
                "impact": "high",
                "effort": "medium",
                "estimated_gain": f"提升 CVR 至 3% 可增加 {clicks * 0.01 * float(epc):.0f} 元 GMV",
                "evidence": [
                    {
                        "metric": "CVR",
                        "value": f"{cvr}%",
                        "comparison": "目标 3-5%",
                        "time_window": window,
                    }
                ],
                "action_items": [
                    "分析高转化内容特征，复制成功模式",
                    "优化商品推荐算法",
                    "A/B 测试不同内容形式",
                ],
            })

        # Opportunity 2: Increase EPC
        if epc < Decimal("60.00"):
            opportunities.append({
                "id": "opp_2",
                "title": "提升客单价",
                "description": f"当前 EPC {epc} 元，通过推荐高价值商品或组合销售可提升",
                "impact": "medium",
                "effort": "low",
                "estimated_gain": f"EPC 提升至 60 元可增加 {clicks * (60 - float(epc)):.0f} 元 GMV",
                "evidence": [
                    {
                        "metric": "EPC",
                        "value": f"{epc} 元",
                        "comparison": "目标 60+ 元",
                        "time_window": window,
                    }
                ],
                "action_items": [
                    "分析高客单价商品特征",
                    "优化商品排序策略",
                    "设计组合套餐",
                ],
            })

        # Opportunity 3: Reduce refunds
        if refund_rate > 5.0:
            opportunities.append({
                "id": "opp_3",
                "title": "降低退款率",
                "description": f"当前退款率 {refund_rate}% 偏高，通过改善商品描述和服务可降低至 <5%",
                "impact": "high",
                "effort": "medium",
                "estimated_gain": f"退款率降至 5% 可减少损失约 {metrics.get('gmv', 0) * (refund_rate - 5) / 100:.0f} 元",
                "evidence": [
                    {
                        "metric": "退款率",
                        "value": f"{refund_rate}%",
                        "comparison": "目标 <5%",
                        "time_window": window,
                    }
                ],
                "action_items": [
                    "优化商品详情页描述",
                    "加强售前咨询",
                    "建立退款原因分析机制",
                ],
            })

        # Opportunity 4: Optimize commission
        if entity_type == "merchant" and commission_rate > 15.0:
            opportunities.append({
                "id": "opp_4",
                "title": "优化佣金结构",
                "description": f"当前佣金率 {commission_rate}% 可优化，通过分层佣金或效果激励可提升 ROI",
                "impact": "medium",
                "effort": "high",
                "estimated_gain": "降低 2-3% 佣金率可节省成本",
                "evidence": [
                    {
                        "metric": "佣金率",
                        "value": f"{commission_rate}%",
                        "comparison": "优化目标 12-15%",
                        "time_window": window,
                    }
                ],
                "action_items": [
                    "设计分层佣金体系",
                    "引入效果激励机制",
                    "分析高 ROI 渠道",
                ],
            })

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "window": window,
            "opportunities": opportunities,
        }

