import { useCallback, useEffect, useRef, useState } from "react"

// Loads with `load` while enabled. Responses from superseded loads are ignored.
export function usePayrollQuery<T>(enabled: boolean, load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const generation = useRef(0)

  const reload = useCallback(async () => {
    const run = ++generation.current
    setLoading(true)
    try {
      const result = await load()
      if (run !== generation.current) return
      setData(result)
      setError("")
    } catch (failure) {
      if (run === generation.current) setError(failure instanceof Error ? failure.message : "급여 정보를 불러오지 못했습니다.")
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [load])

  useEffect(() => {
    const counter = generation
    if (!enabled) return
    const timer = window.setTimeout(() => void reload(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [enabled, reload])

  return { data, error, loading, reload }
}
