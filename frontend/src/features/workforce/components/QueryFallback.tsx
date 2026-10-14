import { EmptyState, ErrorState, Spinner } from "../../../components/ui"
import type { QueryState } from "../hooks"

// 첫 조회의 로딩·권한 없음·오류를 표시한다. 데이터가 있으면 null을 반환해 화면이 그대로 그린다.
export function QueryFallback<T>({ query, label }: { query: QueryState<T>; label: string }) {
  if (query.data !== null) return null
  if (query.forbidden) {
    return <EmptyState title="이 정보를 볼 권한이 없습니다">{query.error || "인사관리자 권한이 필요한 업무입니다."}</EmptyState>
  }
  if (query.error) return <ErrorState onRetry={() => void query.reload()}>{query.error}</ErrorState>
  return <Spinner label={label} />
}
