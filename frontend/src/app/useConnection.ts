import { useCallback, useEffect, useRef, useState } from "react"
import { requestJson } from "../api/client"
import { environment } from "../config/environment"
import type { SystemHealth } from "../types/health"

export function useConnection() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [checking, setChecking] = useState(false)
  const [message, setMessage] = useState("")
  const [simulatedOffline, setSimulatedOffline] = useState(environment.startsOffline)
  const generation = useRef(0)
  const check = useCallback(async () => {
    const run = ++generation.current
    if (simulatedOffline) return
    setChecking(true)
    try {
      const result = await requestJson<SystemHealth>("/api/health/")
      if (run !== generation.current) return
      setHealth(result)
      setMessage(result.end_to_end.status === "connected" ? "서비스가 연결되었습니다." : "일부 서비스가 연결되지 않았습니다.")
    } catch {
      if (run !== generation.current) return
      setHealth(null)
      setMessage("서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도하세요.")
    } finally {
      if (run === generation.current) setChecking(false)
    }
  }, [simulatedOffline])

  useEffect(() => {
    const counter = generation
    const timer = window.setTimeout(() => void check(), 0)
    const interval = window.setInterval(() => void check(), environment.healthPollIntervalMs)
    return () => { counter.current++; window.clearTimeout(timer); window.clearInterval(interval) }
  }, [check])

  const toggleOffline = () => {
    generation.current++
    setHealth(null)
    setChecking(false)
    setMessage("")
    setSimulatedOffline((value) => !value)
  }

  return {
    health: simulatedOffline ? null : health,
    checking, message: simulatedOffline ? "개발용 오프라인 상태입니다." : message,
    simulatedOffline, check, toggleOffline,
    backendConnected: !simulatedOffline && health?.services.backend.status === "connected",
    vacationConnected: !simulatedOffline && health?.end_to_end.status === "connected",
  }
}
