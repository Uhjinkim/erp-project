import { EmptyState, ErrorState, Spinner } from "../../../components/ui"
import type { QueryState } from "../hooks"

// 첫 조회의 로딩·권한 없음·없음·오류를 표시한다. 데이터가 있으면 null을 반환한다.
export function QueryFallback<T>({ query, label, notFoundTitle = "요청을 찾을 수 없습니다" }: { query: QueryState<T>; label: string; notFoundTitle?: string }) {
  if (query.data !== null) return null
  if (query.forbidden) return <EmptyState title="이 정보를 볼 권한이 없습니다">{query.error}</EmptyState>
  if (query.notFound) return <EmptyState title={notFoundTitle}>{query.error}</EmptyState>
  if (query.error) return <ErrorState onRetry={() => void query.reload()}>{query.error}</ErrorState>
  return <Spinner label={label} />
}
