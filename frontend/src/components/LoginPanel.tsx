import { FormEvent, useState } from "react"

type LoginPanelProps = {
  loading: boolean
  error: string
  onLogin: (email: string, password: string) => Promise<void>
}

export function LoginPanel({ loading, error, onLogin }: LoginPanelProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  async function submit(event: FormEvent) {
    event.preventDefault()
    await onLogin(email, password)
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <p className="eyebrow">ERP · SECURE ACCESS</p>
        <h1>업무 계정 로그인</h1>
        <p className="lede">회사 이메일과 비밀번호로 로그인하세요.</p>
        {error && <div className="notice notice--error" role="alert">{error}</div>}
        <form onSubmit={submit}>
          <label>
            이메일
            <input
              autoComplete="username"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label>
            비밀번호
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          <button className="primary" disabled={loading} type="submit">
            {loading ? "로그인 중" : "로그인"}
          </button>
        </form>
      </section>
    </main>
  )
}
