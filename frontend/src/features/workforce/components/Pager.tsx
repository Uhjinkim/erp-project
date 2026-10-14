import { Button } from "../../../components/ui"
import styles from "../workforce.module.css"

// 현재 조회된 배열 안에서만 나눈다. 서버 페이지네이션이 아니다.
export function Pager({ page, pages, total, onChange }: { page: number; pages: number; total: number; onChange: (page: number) => void }) {
  if (pages <= 1) return <p className={styles.hint}>총 {total}명</p>
  return (
    <nav className={styles.pager} aria-label="목록 페이지">
      <span className={styles.hint}>총 {total}명 · {page}/{pages} 페이지</span>
      <span className={styles.row}>
        <Button variant="secondary" size="small" disabled={page <= 1} onClick={() => onChange(page - 1)}>이전</Button>
        <Button variant="secondary" size="small" disabled={page >= pages} onClick={() => onChange(page + 1)}>다음</Button>
      </span>
    </nav>
  )
}
