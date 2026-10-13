import { FormEvent, useState } from "react"
import { Alert, Button, TextInput } from "./ui"
import styles from "../app/auth.module.css"

type LoginPanelProps = {
  loading: boolean
  error: string
  onLogin: (email: string, password: string) => Promise<void>
  expired?: boolean
}

export function LoginPanel({ loading, error, onLogin, expired }: LoginPanelProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  async function submit(event: FormEvent) {
    event.preventDefault()
    await onLogin(email, password)
  }

  return (
    <main className={styles.stage}>
      <div className={styles.layout}>
      <section className={styles.intro}><strong>WORKLY ERP</strong><h1>업무를 한곳에서,<br />명확하게.</h1><p>사원 정보 · 휴가 · 게시판 · 평가 · 급여</p></section>
      <section className={styles.form}>
        <h2>업무 계정 로그인</h2>
        <p>회사 이메일과 비밀번호로 로그인하세요.</p>
        {expired && <Alert tone="warning">로그인 시간이 만료되었습니다. 다시 로그인하면 이전 화면으로 돌아갑니다.</Alert>}
        {error && <Alert tone="error">{error}</Alert>}
        <form onSubmit={submit}>
            <TextInput label="이메일"
              autoComplete="username"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <TextInput label="비밀번호"
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          <Button pending={loading} type="submit">
            {loading ? "로그인 중" : "로그인"}
          </Button>
        </form>
        <p className={styles.help}>로그인에 문제가 있으면 시스템 관리자에게 문의하세요.</p>
      </section>
      </div>
    </main>
  )
}
