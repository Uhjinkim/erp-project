import { useCallback, useEffect, useRef, useState } from "react"
import { ApiError } from "../../api/client"

function errorMessage(failure: unknown, fallback: string) {
  return failure instanceof Error ? failure.message : fallback
}

export type QueryState<T> = {
  data: T | null
  error: string
  forbidden: boolean
  notFound: boolean
  loading: boolean
  reload: () => Promise<void>
  replace: (data: T) => void
}

// enabled 동안 load를 실행한다. 더 최근 요청이 시작되면 이전 응답은 버린다.
export function useProfileQuery<T>(enabled: boolean, load: () => Promise<T>): QueryState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState("")
  const [status, setStatus] = useState<number | undefined>()
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
      setStatus(undefined)
    } catch (failure) {
      if (run !== generation.current) return
      setError(errorMessage(failure, "정보를 불러오지 못했습니다."))
      setStatus(failure instanceof ApiError ? failure.status : undefined)
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

  // 처리 응답으로 받은 최신 값을 재조회 없이 반영한다. 진행 중인 이전 조회 응답은 버린다.
  const replace = useCallback((next: T) => {
    generation.current++
    setData(next)
    setError("")
    setStatus(undefined)
    setLoading(false)
  }, [])

  return { data, error, forbidden: status === 403, notFound: status === 404, loading, reload, replace }
}

// 처리 요청은 동기 잠금으로 연속 클릭을 막고, 실패 시 입력값을 유지하도록 오류만 반환한다.
export function useMutation() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState("")
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({})
  const locked = useRef(false)

  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | null> => {
    if (locked.current) return null
    locked.current = true
    setPending(true)
    setError("")
    setFieldErrors({})
    try {
      return await action()
    } catch (failure) {
      setError(errorMessage(failure, "요청을 처리하지 못했습니다."))
      if (failure instanceof ApiError) setFieldErrors(failure.fieldErrors)
      return null
    } finally {
      locked.current = false
      setPending(false)
    }
  }, [])

  const reset = useCallback(() => {
    setError("")
    setFieldErrors({})
  }, [])

  return { pending, error, fieldErrors, run, reset }
}
