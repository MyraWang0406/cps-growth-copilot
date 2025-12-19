'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Opportunity {
  id: string
  title: string
  description: string
  impact: string
  effort: string
  estimated_gain?: string
  evidence: Array<{ metric: string; value: string; comparison?: string; time_window: string }>
  action_items: string[]
}

interface OpportunitiesResponse {
  entity_id: number
  entity_type: string
  window: string
  opportunities: Opportunity[]
}

export default function CopilotPage() {
  const router = useRouter()
  const [entityType, setEntityType] = useState<'taoke' | 'merchant'>('taoke')
  const [entityId, setEntityId] = useState(1)
  const [window, setWindow] = useState('14d')
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [plan, setPlan] = useState<string | null>(null)

  const fetchOpportunities = async () => {
    setLoading(true)
    setError(null)
    try {
      const endpoint = entityType === 'taoke' 
        ? `/opportunities/taoke/${entityId}?window=${window}`
        : `/opportunities/merchant/${entityId}?window=${window}`
      
      const res = await fetch(`${API_URL}${endpoint}`)
      if (!res.ok) throw new Error('Failed to fetch opportunities')
      const data: OpportunitiesResponse = await res.json()
      setOpportunities(data.opportunities)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const generatePlan = () => {
    // Simple plan generation (can be replaced with API call)
    const planText = `# ${entityType === 'taoke' ? '淘客' : '商家'}周计划

## 本周目标
基于机会分析，制定以下行动计划：

${opportunities.map((opp, idx) => `
### ${idx + 1}. ${opp.title}
- **影响**: ${opp.impact}
- **难度**: ${opp.effort}
${opp.estimated_gain ? `- **预期收益**: ${opp.estimated_gain}` : ''}

**行动项**:
${opp.action_items.map(item => `- ${item}`).join('\n')}
`).join('\n')}

## 执行时间表
- 周一-周三: 执行高影响、低难度任务
- 周四-周五: 推进中等难度任务
- 周末: 数据复盘与下周规划
`
    setPlan(planText)
  }

  const generateBrief = () => {
    const briefText = `# 内容素材 Brief

## 目标
为${entityType === 'taoke' ? '淘客' : '商家'} ${entityId} 创建高转化内容素材

## 核心信息
- 目标受众: 关注性价比的用户
- 核心卖点: 基于数据分析的高转化商品
- 内容形式: 图文/视频

## 内容要求
1. 突出商品核心优势
2. 包含真实使用场景
3. 强调优惠和性价比
4. 添加明确的行动号召

## 参考数据
${opportunities.length > 0 ? `- 当前转化率有提升空间` : ''}
- 建议关注高EPC商品组合
`
    setPlan(briefText)
  }

  const getImpactClass = (impact: string) => {
    if (impact === 'high') return 'impact-high'
    if (impact === 'medium') return 'impact-medium'
    return 'impact-low'
  }

  return (
    <div className="container">
      <div style={{ marginBottom: '20px' }}>
        <button className="btn btn-secondary" onClick={() => router.push('/')}>
          ← 返回首页
        </button>
      </div>

      <h1>Copilot 智能助手</h1>

      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <label>
              身份:
              <select
                value={entityType}
                onChange={(e) => setEntityType(e.target.value as 'taoke' | 'merchant')}
                style={{ marginLeft: '10px', padding: '5px' }}
              >
                <option value="taoke">淘客</option>
                <option value="merchant">商家</option>
              </select>
            </label>
            <label>
              ID:
              <input
                type="number"
                value={entityId}
                onChange={(e) => setEntityId(Number(e.target.value))}
                style={{ marginLeft: '10px', padding: '5px', width: '80px' }}
              />
            </label>
            <label>
              时间窗口:
              <select
                value={window}
                onChange={(e) => setWindow(e.target.value)}
                style={{ marginLeft: '10px', padding: '5px' }}
              >
                <option value="7d">7天</option>
                <option value="14d">14天</option>
                <option value="30d">30天</option>
              </select>
            </label>
          </div>
          <div>
            <button className="btn" onClick={fetchOpportunities} disabled={loading}>
              {loading ? '分析中...' : '分析机会'}
            </button>
            {opportunities.length > 0 && (
              <>
                <button className="btn" onClick={generatePlan} style={{ marginLeft: '10px' }}>
                  生成周计划
                </button>
                <button className="btn" onClick={generateBrief} style={{ marginLeft: '10px' }}>
                  生成素材 Brief
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading && <div className="loading">分析中，请稍候...</div>}

      {opportunities.length > 0 && (
        <div>
          <h2>发现的机会</h2>
          {opportunities.map((opp) => (
            <div key={opp.id} className="opportunity-card">
              <div className="opportunity-header">
                <h3>{opp.title}</h3>
                <span className={`impact-badge ${getImpactClass(opp.impact)}`}>
                  {opp.impact} impact
                </span>
              </div>
              <p style={{ marginBottom: '15px' }}>{opp.description}</p>
              {opp.estimated_gain && (
                <p style={{ marginBottom: '15px', fontWeight: 'bold', color: '#0070f3' }}>
                  预期收益: {opp.estimated_gain}
                </p>
              )}
              <div>
                <h4>行动项:</h4>
                <ul>
                  {opp.action_items.map((item, idx) => (
                    <li key={idx} style={{ margin: '5px 0' }}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}

      {plan && (
        <div className="card" style={{ marginTop: '20px' }}>
          <h2>生成的计划</h2>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '20px', 
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            overflow: 'auto'
          }}>
            {plan}
          </pre>
          <button 
            className="btn" 
            onClick={() => {
              navigator.clipboard.writeText(plan)
              alert('已复制到剪贴板')
            }}
            style={{ marginTop: '10px' }}
          >
            复制内容
          </button>
        </div>
      )}
    </div>
  )
}

