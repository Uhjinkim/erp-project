import { useEffect, useRef, useState } from "react"
import { emptyData, loadVacationData } from "./data"
import type { VacationData } from "./data"
import type { VacationRequest } from "../../types/vacation"

export function useVacationData(employeeNo: number, connected: boolean, screen: string, requestId: number | null) {
  const key = `${employeeNo}:${screen}:${requestId}:${connected}`
  const [version, setVersion] = useState(0)
  const [state, setState] = useState<{ key: string; data: VacationData; loading: boolean }>({ key: "", data: emptyData(), loading: true })
  useEffect(() => {
    if (!connected) return
    let active = true
    const timer = window.setTimeout(() => {
      setState({ key, data: emptyData(), loading: true })
      void loadVacationData(employeeNo, screen, requestId).then((data) => {
        if (active) setState({ key, data, loading: false })
      })
    }, 0)
    return () => { active = false
      window.clearTimeout(timer)
    }
  }, [key, employeeNo, connected, screen, requestId, version])
  const current = state.key === key ? state : { data: emptyData(), loading: connected }
  return { ...current.data, loading: current.loading, refresh: () => setVersion((value) => value + 1) }
}

export function useVacationMutation() {
  const busy = useRef(false)
  const mounted = useRef(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [saved, setSaved] = useState<VacationRequest | null>(null)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])
  async function execute(operation: () => Promise<VacationRequest>) {
    if (busy.current) return null
    busy.current = true
    setPending(true)
    setError(null)
    try {
      const item = await operation()
      if (!mounted.current) return null
      setSaved(item)
      return item
    } catch (failure) {
      if (mounted.current) setError(failure instanceof Error ? failure : new Error("처리하지 못했습니다."))
      return null
    } finally {
      busy.current = false
      if (mounted.current) setPending(false)
    }
  }
  return { pending, error, saved, execute, reset: () => { if (!busy.current) { setSaved(null); setError(null) } } }
}
