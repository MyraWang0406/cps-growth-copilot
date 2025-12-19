'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

const templates = {
  taoke_diagnosis_report: `# 淘客诊断报告

## 执行摘要
本报告基于过去14天的数据分析，对淘客运营情况进行全面诊断。

## 核心指标
- 曝光: XXX
- 点击: XXX
- 订单: XXX
- CVR: X.X%
- EPC: ¥XX

## 关键洞察
1. 转化率分析
2. 内容效果评估
3. 商品匹配度

## 风险提示
- 退款率异常
- 佣金成本控制

## 行动建议
1. 优化内容策略
2. 调整商品组合
3. 提升转化率
`,

  taoke_weekly_plan: `# 淘客周计划

## 本周目标
- GMV目标: ¥XX,XXX
- 订单目标: XXX单
- CVR提升至: X.X%

## 执行计划
### 周一-周三
- 内容创作与发布
- 商品选品优化

### 周四-周五
- 数据复盘
- 策略调整

### 周末
- 下周规划
- 素材准备
`,

  merchant_growth_plan: `# 商家增长计划

## 增长目标
- GMV增长: XX%
- 订单增长: XX%
- 退款率控制: <X%

## 策略方向
1. 佣金优化
2. 商品组合
3. 渠道拓展

## 执行时间表
- Q1: 基础优化
- Q2: 规模扩张
- Q3: 精细化运营
`,

  merchant_commission_strategy: `# 佣金策略方案

## 当前状况
- 平均佣金率: X.X%
- 佣金成本: ¥XX,XXX

## 优化方案
1. 分层佣金体系
   - 高价值商品: X%
   - 常规商品: X%
   - 促销商品: X%

2. 效果激励
   - 转化率奖励
   - GMV奖励

## 预期效果
- 成本降低: X%
- ROI提升: X%
`,

  creative_brief: `# 内容素材 Brief

## 项目信息
- 目标受众: XXX
- 核心卖点: XXX
- 内容形式: 图文/视频

## 内容要求
1. 突出商品优势
2. 真实使用场景
3. 优惠信息
4. 行动号召

## 交付标准
- 尺寸规格
- 格式要求
- 文案要求
`,

  experiment_design: `# 实验设计

## 实验目标
验证XXX策略对转化率的影响

## 实验设计
- 对照组: 当前策略
- 实验组: 新策略
- 样本量: XXX
- 实验周期: X天

## 评估指标
- 主要指标: CVR
- 次要指标: EPC, GMV

## 成功标准
CVR提升 > X%
`,

  anomaly_alert: `# 异常告警

## 告警类型
[类型]: XXX异常

## 告警详情
- 时间: XXXX-XX-XX
- 实体: XXX
- 指标: XXX
- 当前值: XXX
- 阈值: XXX

## 影响评估
- 严重程度: 高/中/低
- 影响范围: XXX

## 处理建议
1. 立即排查
2. 数据验证
3. 策略调整
`,

  weekly_business_review: `# 周业务复盘

## 本周数据概览
- GMV: ¥XX,XXX
- 订单: XXX单
- 退款: XX单

## 关键事件
1. XXX
2. XXX

## 亮点与不足
### 亮点
- XXX

### 不足
- XXX

## 下周计划
- 目标设定
- 重点事项
- 资源需求
`,
}

export default function ExportPage() {
  const router = useRouter()
  const [selectedTemplate, setSelectedTemplate] = useState<string>('taoke_diagnosis_report')
  const [content, setContent] = useState<string>(templates.taoke_diagnosis_report)

  const handleTemplateChange = (template: string) => {
    setSelectedTemplate(template)
    setContent(templates[template as keyof typeof templates])
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(content)
    alert('已复制到剪贴板！')
  }

  return (
    <div className="container">
      <div style={{ marginBottom: '20px' }}>
        <button className="btn btn-secondary" onClick={() => router.push('/')}>
          ← 返回首页
        </button>
      </div>

      <h1>导出报告</h1>

      <div className="card" style={{ marginBottom: '20px' }}>
        <label>
          选择模板:
          <select
            value={selectedTemplate}
            onChange={(e) => handleTemplateChange(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px', minWidth: '300px' }}
          >
            <option value="taoke_diagnosis_report">淘客诊断报告</option>
            <option value="taoke_weekly_plan">淘客周计划</option>
            <option value="merchant_growth_plan">商家增长计划</option>
            <option value="merchant_commission_strategy">佣金策略方案</option>
            <option value="creative_brief">内容素材 Brief</option>
            <option value="experiment_design">实验设计</option>
            <option value="anomaly_alert">异常告警</option>
            <option value="weekly_business_review">周业务复盘</option>
          </select>
        </label>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2>报告内容</h2>
          <button className="btn" onClick={copyToClipboard}>
            复制到剪贴板
          </button>
        </div>
        <pre style={{
          background: '#f5f5f5',
          padding: '20px',
          borderRadius: '4px',
          whiteSpace: 'pre-wrap',
          overflow: 'auto',
          maxHeight: '600px',
          fontFamily: 'monospace',
          fontSize: '14px',
          lineHeight: '1.6'
        }}>
          {content}
        </pre>
      </div>
    </div>
  )
}

