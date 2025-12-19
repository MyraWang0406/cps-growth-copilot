'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Metrics {
  window: string
  impressions: number
  clicks: number
  orders: number
  refunds: number
  gmv: string
  commission_paid: string
  ctr: number
  cvr: number
  epc: string
  refund_rate: number
  commission_rate: number
}

interface Insight {
  type: string
  title: string
  description: string
  evidence: Array<{ metric: string; value: string; comparison?: string; time_window: string }>
  impact: string
}

interface Diagnosis {
  entity_id: number
  entity_type: string
  window: string
  summary: string
  insights: Insight[]
  risks: Insight[]
  next_actions: string[]
}

export default function TaokePage() {
  const router = useRouter()
  const [taokeId, setTaokeId] = useState(1)
  const [window, setWindow] = useState('7d')
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/metrics/taoke/${taokeId}?window=${window}`)
      if (!res.ok) throw new Error('Failed to fetch metrics')
      const data = await res.json()
      setMetrics(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchDiagnosis = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/diagnosis/taoke/${taokeId}?window=14d`)
      if (!res.ok) throw new Error('Failed to fetch diagnosis')
      const data = await res.json()
      setDiagnosis(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
    fetchDiagnosis()
  }, [taokeId, window])

  return (
    <div className="container">
      <div style={{ marginBottom: '20px' }}>
        <button className="btn btn-secondary" onClick={() => router.push('/')}>
          ← 返回首页
        </button>
      </div>

      <h1>淘客 Dashboard</h1>

      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '20px' }}>
          <label>
            淘客 ID:
            <input
              type="number"
              value={taokeId}
              onChange={(e) => setTaokeId(Number(e.target.value))}
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
          <button className="btn" onClick={fetchMetrics}>
            刷新
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading && !metrics && <div className="loading">加载中...</div>}

      {metrics && (
        <div className="card">
          <h2>核心指标</h2>
          <div className="metrics-grid">
            <div className="metric-item">
              <div className="metric-value">{metrics.impressions}</div>
              <div className="metric-label">曝光</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">{metrics.clicks}</div>
              <div className="metric-label">点击</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">{metrics.orders}</div>
              <div className="metric-label">订单</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">{metrics.ctr.toFixed(2)}%</div>
              <div className="metric-label">CTR</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">{metrics.cvr.toFixed(2)}%</div>
              <div className="metric-label">CVR</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">¥{metrics.epc}</div>
              <div className="metric-label">EPC</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">¥{metrics.gmv}</div>
              <div className="metric-label">GMV</div>
            </div>
            <div className="metric-item">
              <div className="metric-value">¥{metrics.commission_paid}</div>
              <div className="metric-label">佣金</div>
            </div>
          </div>
        </div>
      )}

      {diagnosis && (
        <>
          <div className="card">
            <h2>诊断报告</h2>
            <p style={{ marginBottom: '20px', color: '#666' }}>{diagnosis.summary}</p>

            {diagnosis.insights.length > 0 && (
              <div>
                <h3>洞察</h3>
                {diagnosis.insights.map((insight, idx) => (
                  <div key={idx} className={`insight-item ${insight.type}`}>
                    <h4>{insight.title}</h4>
                    <p>{insight.description}</p>
                  </div>
                ))}
              </div>
            )}

            {diagnosis.risks.length > 0 && (
              <div style={{ marginTop: '20px' }}>
                <h3>风险</h3>
                {diagnosis.risks.map((risk, idx) => (
                  <div key={idx} className="insight-item risk">
                    <h4>{risk.title}</h4>
                    <p>{risk.description}</p>
                  </div>
                ))}
              </div>
            )}

            {diagnosis.next_actions.length > 0 && (
              <div style={{ marginTop: '20px' }}>
                <h3>下一步行动</h3>
                <ul>
                  {diagnosis.next_actions.map((action, idx) => (
                    <li key={idx} style={{ margin: '5px 0' }}>{action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

