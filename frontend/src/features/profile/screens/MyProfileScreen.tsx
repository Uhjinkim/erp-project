import { useState } from "react"
import { Alert, Badge, Button, Card, DetailList } from "../../../components/ui"
import type { PersonalInfoChangeRequest } from "../../../types/profile"
import type { EmployeeDetail } from "../../../types/workforce"
import { maskAccount } from "../model"
import styles from "../profile.module.css"

const genderLabels: Record<string, string> = { M: "남성", F: "여성" }
const savedMessages: Record<string, string> = { contact: "연락처·주소를 수정했습니다." }

type MyProfileProps = {
  employee: EmployeeDetail
  pending: PersonalInfoChangeRequest | null
  search: URLSearchParams
}

// FN-HR-001: 본인 인사정보 조회 전용 화면. 수정·변경 요청은 메뉴의 전용 화면에서 처리한다.
export function MyProfileScreen({ employee, pending, search }: MyProfileProps) {
  const [showAccount, setShowAccount] = useState(false)
  const saved = savedMessages[search.get("saved") ?? ""]
  return (
    <div className={styles.stack}>
      {saved && <Alert tone="success">{saved}</Alert>}
      <Card title={`${employee.name} · 사번 ${employee.emp_no}`}>
        <DetailList items={[
          { key: "dept", label: "부서", value: employee.dept_name ?? "미배정" },
          { key: "position", label: "직급", value: employee.position_name ?? "미배정" },
          { key: "status", label: "재직 상태", value: <Badge tone={employee.tenure_status === "재직" ? "success" : "neutral"}>{employee.tenure_status}</Badge> },
          { key: "hire", label: "입사일", value: employee.hire_date },
          { key: "birth", label: "생년월일", value: employee.birth_date ?? "미등록" },
          { key: "gender", label: "성별", value: employee.gender ? genderLabels[employee.gender] ?? employee.gender : "미등록" },
          { key: "extension", label: "내선번호", value: employee.extension_no ?? "미등록" },
        ]} />
        <p className={styles.hint}>부서·직급·내선번호 등 인사정보 변경은 인사관리자에게 요청하세요.</p>
      </Card>

      <div className={styles.grid}>
        <Card title="연락처·주소">
          <DetailList items={[
            { key: "phone", label: "연락처", value: employee.phone ?? "미등록" },
            { key: "address", label: "주소", value: <span className={styles.wrap}>{employee.address ?? "미등록"}</span> },
          ]} />
          <p className={styles.hint}>&lsquo;연락처·주소 직접 수정&rsquo; 메뉴에서 승인 없이 수정할 수 있습니다(HR-002).</p>
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
          {pending
            ? <Alert tone="info" title="처리 대기 중인 변경 요청이 있습니다">{pending.requested_at.slice(0, 10)}에 요청했습니다. 승인되면 반영됩니다.</Alert>
            : <p className={styles.hint}>&lsquo;민감 정보 변경 요청&rsquo; 메뉴에서 요청하면 인사관리자 승인 후 반영됩니다(HR-003).</p>}
        </Card>
      </div>
    </div>
  )
}
