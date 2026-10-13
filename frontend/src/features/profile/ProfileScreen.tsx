import { useCallback, useEffect, useState } from "react"
import { getMyEmployeeInfo } from "../../api/profile"
import { EmployeeInfoCard } from "../../components/EmployeeInfoCard"
import { PersonalInfoEditor } from "../../components/PersonalInfoRequests"
import { EmptyState, ErrorState, Spinner } from "../../components/ui"
import type { CurrentUser } from "../../types/auth"
import type { EmployeeDetail } from "../../types/workforce"

export function ProfileScreen({ user, enabled }: { user: CurrentUser; enabled: boolean }) {
  const [employee, setEmployee] = useState<EmployeeDetail | null>(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(async () => {
    setLoading(true)
    setError("")
    try { setEmployee(await getMyEmployeeInfo()) }
    catch (failure) { setError(failure instanceof Error ? failure.message : "본인 정보를 불러오지 못했습니다.") }
    finally { setLoading(false) }
  }, [])
  useEffect(() => {
    if (!enabled || !user.employee) return
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [enabled, user.employee, refresh])
  if (!user.employee) return <EmptyState title="연결된 사원 정보가 없습니다">관리자에게 계정과 사원 연결을 문의하세요.</EmptyState>
  if (!enabled) return <EmptyState title="연결 후 본인 정보를 불러옵니다" />
  if (loading) return <Spinner />
  if (error) return <ErrorState onRetry={() => void refresh()}>{error}</ErrorState>
  if (!employee) return <Spinner />
  return <div className="legacy-module"><EmployeeInfoCard title="내 인사정보" loading={false} employee={employee} /><PersonalInfoEditor employee={employee} reloadKey={version} onContactUpdated={setEmployee} onRequestsChanged={() => setVersion((value) => value + 1)} /></div>
}
