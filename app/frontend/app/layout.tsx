import './globals.css'

export const metadata = {
  title: 'CPS Growth Copilot',
  description: 'CPS Growth Copilot - 智能增长助手',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  )
}

