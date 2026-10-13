import { useCallback, useEffect, useRef, useState } from "react"
import { getCurrentUser, loginWithEmail, logoutSession } from "../api/auth"
import { ApiError, subscribeAccessFailure } from "../api/client"
import { environment } from "../config/environment"
import type { CurrentUser } from "../types/auth"

type Session =
  | { status: "checking" | "anonymous" | "expired" | "unavailable" | "development"; user: null }
  | { status: "authenticated"; user: CurrentUser }

export function useSession() {
  const [session, setSession] = useState<Session>({ status: environment.authMode === "development" ? "development" : "checking", user: null })
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const generation = useRef(0)
  const verifying = useRef(false)

  const verify = useCallback(async (expired = false) => {
    if (verifying.current) return
    verifying.current = true
    const run = generation.current
    try {
      const user = await getCurrentUser()
      if (run === generation.current) {
        setSession({ status: "authenticated", user })
        setError("")
      }
    } catch (failure) {
      if (run !== generation.current) return
      if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) {
        setSession({ status: expired ? "expired" : "anonymous", user: null })
      } else {
        // An unavailable auth service does not prove that a live session expired.
        setSession((current) => current.status === "authenticated" ? current : { status: "unavailable", user: null })
        setError("인증 서버에 연결할 수 없습니다.")
      }
    } finally { verifying.current = false }
  }, [])

  useEffect(() => {
    const counter = generation
    if (environment.authMode === "development") return
    const timer = window.setTimeout(() => void verify(), 0)
    const unsubscribe = subscribeAccessFailure(() => { void verify(true) })
    return () => { counter.current++; window.clearTimeout(timer); unsubscribe() }
  }, [verify])

  async function login(email: string, password: string) {
    setPending(true)
    setError("")
    const run = ++generation.current
    try {
      const user = await loginWithEmail(email, password)
      if (run === generation.current) setSession({ status: "authenticated", user })
    } catch (failure) {
      if (run === generation.current) setError(failure instanceof Error ? failure.message : "로그인하지 못했습니다.")
    } finally { if (run === generation.current) setPending(false) }
  }

  async function logout() {
    setPending(true)
    setError("")
    generation.current++
    try {
      await logoutSession()
      setSession({ status: "anonymous", user: null })
    } catch (failure) {
      if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) {
        await verify(true)
      }
      setError("로그아웃을 확인하지 못했습니다. 다시 시도하세요.")
    } finally { setPending(false) }
  }

  return { ...session, pending, error, login, logout, retry: () => void verify() }
}
