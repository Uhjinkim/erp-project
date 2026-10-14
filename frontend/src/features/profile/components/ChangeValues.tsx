import type { PersonalInfoChangeRequest } from "../../../types/profile"
import { displayValue, fieldLabel } from "../model"
import styles from "../profile.module.css"

// 목록용 요약: 변경 항목만 "이전 → 요청" 한 줄로 표시한다. 계좌는 항상 가린다.
export function ChangeList({ request }: { request: PersonalInfoChangeRequest }) {
  return (
    <ul className={styles.changeList}>
      {request.changed_fields.map((field) => (
        <li key={field}>
          <span className={styles.subtext}>{fieldLabel(field)}</span>
          {displayValue(field, request.previous[field])} → <strong>{displayValue(field, request.requested[field])}</strong>
        </li>
      ))}
    </ul>
  )
}

// 처리 화면용 전후 비교. 처리자에게 서버가 원문 계좌를 준 경우에만 revealAccount로 원문을 보여 준다.
export function ChangeComparison({ request, revealAccount = false }: { request: PersonalInfoChangeRequest; revealAccount?: boolean }) {
  return (
    <dl className={styles.compare}>
      <dt className={styles.compareHead}>항목</dt><dd className={styles.compareHead}>현재 값</dd><dd className={styles.compareHead}>요청 값</dd>
      {request.changed_fields.flatMap((field) => {
        const requested = field === "account_no" && revealAccount ? request.requested[field] ?? "미등록" : displayValue(field, request.requested[field])
        return [
          <dt key={`${field}-label`}>{fieldLabel(field)}</dt>,
          <dd key={`${field}-before`}>{displayValue(field, request.previous[field])}</dd>,
          <dd key={`${field}-after`} className={styles.changed}>{requested}</dd>,
        ]
      })}
    </dl>
  )
}
