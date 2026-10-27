import { useState } from "react"
import { Alert, Badge, Button, Card, DetailList } from "../../../components/ui"
import type { PersonalInfoChangeRequest } from "../../../types/profile"
import type { EmployeeDetail } from "../../../types/workforce"
import { ProfileEditForm } from "../components/ProfileEditForm"
import { maskAccount, navigate, profileHref } from "../model"
import styles from "../profile.module.css"

const genderLabels: Record<string, string> = { M: "남성", F: "여성" }
const savedMessages: Record<string, string> = { request: "수정 요청을 제출했습니다. 인사관리자가 승인하면 반영됩니다." }

type MyProfileProps = {
  employee: EmployeeDetail
  pending: PersonalInfoChangeRequest | null
  search: URLSearchParams
  onSubmitted: () => void
}

// FN-HR-001 본인 인사정보 조회, FN-HR-002 수정 버튼으로 같은 화면에서 수정 모드로 전환한다.
export function MyProfileScreen({ employee, pending, search, onSubmitted }: MyProfileProps) {
  const [showAccount, setShowAccount] = useState(false)
  const [editing, setEditing] = useState(false)
  const saved = savedMessages[search.get("saved") ?? ""]

  if (editing) {
    return <ProfileEditForm employee={employee} onCancel={() => setEditing(false)} onSubmitted={() => {
      setEditing(false)
      onSubmitted()
      navigate(profileHref("my-profile", { saved: "request" }))
    }} />
  }

  return (
    <div className={styles.stack}>
      {saved && <Alert tone="success">{saved}</Alert>}
      {pending && (
        <Alert tone="info" title="처리 대기 중인 수정 요청이 있습니다">
          {pending.requested_at.slice(0, 10)}에 요청했습니다. 인사관리자가 승인하면 반영됩니다. 다시 수정하려면 <a href={profileHref("change-history")}>내 수정 요청 이력</a>에서 기존 요청을 취소하세요.
        </Alert>
      )}
      <Card title={`${employee.name} · 사번 ${employee.emp_no}`} actions={<Button size="small" disabled={pending !== null} onClick={() => setEditing(true)}>수정</Button>}>
        <DetailList items={[
          { key: "dept", label: "부서", value: employee.dept_name ?? "미배정" },
          { key: "position", label: "직급", value: employee.position_name ?? "미배정" },
          { key: "status", label: "재직 상태", value: <Badge tone={employee.tenure_status === "재직" ? "success" : "neutral"}>{employee.tenure_status}</Badge> },
          { key: "hire", label: "입사일", value: employee.hire_date },
          { key: "birth", label: "생년월일", value: employee.birth_date ?? "미등록" },
          { key: "gender", label: "성별", value: employee.gender ? genderLabels[employee.gender] ?? employee.gender : "미등록" },
          { key: "extension", label: "내선번호", value: employee.extension_no ?? "미등록" },
        ]} />
        <p className={styles.hint}>연락처·주소·사내 이메일·급여계좌는 &lsquo;수정&rsquo;에서 고치면 인사관리자 승인 후 반영됩니다(HR-002). 부서·직급·내선번호 등 인사정보 변경은 인사관리자에게 요청하세요.</p>
      </Card>

      <div className={styles.grid}>
        <Card title="연락처·주소">
          <DetailList items={[
            { key: "phone", label: "연락처", value: employee.phone ?? "미등록" },
            { key: "address", label: "주소", value: <span className={styles.wrap}>{employee.address ?? "미등록"}</span> },
          ]} />
        </Card>

        <Card title="사내 이메일·급여계좌">
          <DetailList items={[
            { key: "email", label: "사내 이메일", value: employee.email ?? "미등록" },
            { key: "bank", label: "은행 코드", value: employee.bank_code ?? "미등록" },
            {
              key: "account", label: "급여계좌", value: (
                <span className={styles.row}>
                  {showAccount ? employee.account_no ?? "미등록" : maskAccount(employee.account_no)}
                  {employee.account_no && <Button size="small" variant="ghost" aria-pressed={showAccount} onClick={() => setShowAccount(!showAccount)}>{showAccount ? "가리기" : "전체 보기"}</Button>}
                </span>
              ),
            },
          ]} />
        </Card>
      </div>
    </div>
  )
}
