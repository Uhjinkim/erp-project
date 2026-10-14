import { useCallback, useEffect, useRef, useState } from "react"
import { ApiError } from "../../api/client"
import { listDepartments, listPositions, listRoles } from "../../api/workforce"
import type { DepartmentSummary, PositionSummary, RoleSummary } from "../../types/workforce"
import { sortPositions } from "./model"

export function errorMessage(failure: unknown, fallback: string) {
  return failure instanceof Error ? failure.message : fallback
}

// 403은 세션 재확인과 별개로 화면에서 권한 오류로 표시한다.
export function isForbidden(failure: unknown) {
  return failure instanceof ApiError && failure.status === 403
}

export type QueryState<T> = {
  data: T | null
  error: string
  forbidden: boolean
  loading: boolean
  reload: () => Promise<void>
}

// enabled 동안 load를 실행한다. 더 최근 요청이 시작되면 이전 응답은 버린다.
export function useWorkforceQuery<T>(enabled: boolean, load: () => Promise<T>): QueryState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState("")
  const [forbidden, setForbidden] = useState(false)
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
      setForbidden(false)
    } catch (failure) {
      if (run !== generation.current) return
      setError(errorMessage(failure, "사원 정보를 불러오지 못했습니다."))
      setForbidden(isForbidden(failure))
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

  return { data, error, forbidden, loading, reload }
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

export type MasterData = {
  departments: DepartmentSummary[]
  positions: PositionSummary[]
  roles: RoleSummary[]
}

const loadMasterData = async (): Promise<MasterData> => {
  const [departments, positions, roles] = await Promise.all([listDepartments(), listPositions(), listRoles()])
  return { departments: [...departments].sort((a, b) => a.dept_no - b.dept_no), positions: sortPositions(positions), roles }
}

export function useMasterData(enabled: boolean) {
  return useWorkforceQuery(enabled, loadMasterData)
}
