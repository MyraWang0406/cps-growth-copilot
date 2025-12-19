'use client'

import { useRouter } from 'next/navigation'
import './globals.css'

export default function Home() {
  const router = useRouter()

  return (
    <div className="container" style={{ paddingTop: '100px' }}>
      <div style={{ textAlign: 'center', maxWidth: '600px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '48px', marginBottom: '20px' }}>
          CPS Growth Copilot
        </h1>
        <p style={{ fontSize: '18px', color: '#666', marginBottom: '40px' }}>
          智能增长助手 - 淘客侧 & 商家侧数据分析与策略生成
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center' }}>
          <button
            className="btn"
            onClick={() => router.push('/taoke')}
            style={{ width: '300px', padding: '15px', fontSize: '16px' }}
          >
            淘客 Dashboard
          </button>

          <button
            className="btn"
            onClick={() => router.push('/merchant')}
            style={{ width: '300px', padding: '15px', fontSize: '16px' }}
          >
            商家 Dashboard
          </button>

          <button
            className="btn btn-secondary"
            onClick={() => router.push('/copilot')}
            style={{ width: '300px', padding: '15px', fontSize: '16px' }}
          >
            进入 Copilot
          </button>

          <button
            className="btn btn-secondary"
            onClick={() => router.push('/export')}
            style={{ width: '300px', padding: '15px', fontSize: '16px' }}
          >
            导出报告
          </button>
        </div>
      </div>
    </div>
  )
}

