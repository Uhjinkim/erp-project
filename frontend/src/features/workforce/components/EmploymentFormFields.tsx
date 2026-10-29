import type { ChangeEvent } from "react"
import { Checkbox, Select, TextInput, Textarea } from "../../../components/ui"
import type { MasterData } from "../hooks"
import type { EmploymentForm, FieldErrors } from "../model"
import styles from "../workforce.module.css"

type EmploymentFormFieldsProps = {
  mode: "create" | "rehire"
  form: EmploymentForm
  errors: FieldErrors
  master: MasterData
  disabled: boolean
  onChange: (form: EmploymentForm) => void
}

// FN-HR-006 신규 등록과 FN-HR-009 재입사에서 같은 입력 구조를 사용한다.
export function EmploymentFormFields({ mode, form, errors, master, disabled, onChange }: EmploymentFormFieldsProps) {
  const rehire = mode === "rehire"
  const set = <K extends keyof EmploymentForm>(key: K, value: EmploymentForm[K]) => onChange({ ...form, [key]: value })
  const text = (key: keyof EmploymentForm) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    set(key, event.target.value as never)
  const toggleRole = (code: string, checked: boolean) =>
    set("role_codes", checked ? [...form.role_codes, code] : form.role_codes.filter((item) => item !== code))

  return (
    <div className={styles.stack}>
      <fieldset className={styles.fieldset} disabled={disabled}>
        <legend>인적사항</legend>
        {rehire && <p className={styles.hint}>비워 둔 항목은 기존 인적사항을 그대로 유지합니다.</p>}
        <div className={styles.fieldGrid}>
          <TextInput label="이름" required={!rehire} maxLength={50} value={form.name} error={errors.name} onChange={text("name")} />
          <TextInput label="생년월일" type="date" required={!rehire} value={form.birth_date} error={errors.birth_date} onChange={text("birth_date")} />
          <Select label="성별" required={!rehire} value={form.gender} error={errors.gender} onChange={text("gender")}>
            <option value="">{rehire ? "변경하지 않음" : "선택"}</option>
            <option value="M">남성</option>
            <option value="F">여성</option>
          </Select>
        </div>
      </fieldset>

      <fieldset className={styles.fieldset} disabled={disabled}>
        <legend>고용 정보</legend>
        <div className={styles.fieldGrid}>
          <TextInput label="사내 이메일" type="email" required maxLength={100} value={form.email} error={errors.email} onChange={text("email")} />
          <TextInput label={rehire ? "재입사일" : "입사일"} type="date" required value={form.hire_date} error={errors.hire_date} onChange={text("hire_date")} />
          <Select label="부서" required value={form.dept_no} error={errors.dept_no} onChange={text("dept_no")}>
            <option value="">선택</option>
            {master.departments.map((item) => <option key={item.dept_no} value={item.dept_no}>{item.dept_name} (#{item.dept_no})</option>)}
          </Select>
          <Select label="직급" required value={form.position_code} error={errors.position_code} onChange={text("position_code")}>
            <option value="">선택</option>
            {master.positions.map((item) => <option key={item.position_code} value={item.position_code}>{item.position_name}</option>)}
          </Select>
          <TextInput label="기본급(원)" required inputMode="decimal" value={form.base_salary} error={errors.base_salary} hint="최초 인사이력에 기록됩니다." onChange={text("base_salary")} />
        </div>
      </fieldset>

      <fieldset className={styles.fieldset} disabled={disabled}>
        <legend>연락처</legend>
        <div className={styles.fieldGrid}>
          <TextInput label="연락처" type="tel" maxLength={20} value={form.phone} error={errors.phone} onChange={text("phone")} />
          <TextInput label="내선번호" maxLength={20} value={form.extension_no} error={errors.extension_no} onChange={text("extension_no")} />
          <div className={styles.fullWidth}>
            <Textarea label="주소" maxLength={255} rows={2} value={form.address} error={errors.address} onChange={text("address")} />
          </div>
        </div>
      </fieldset>

      <fieldset className={styles.fieldset} disabled={disabled}>
        <legend>업무 역할·계정</legend>
        {master.roles.length === 0
          ? <p className={styles.hint}>등록된 역할이 없습니다. 역할은 등록 후 역할 부여 화면에서도 지정할 수 있습니다.</p>
          : <div className={styles.choices} role="group" aria-label="부여할 업무 역할">
              {master.roles.map((role) => (
                <Checkbox key={role.role_code} label={role.role_name} checked={form.role_codes.includes(role.role_code)} onChange={(event) => toggleRole(role.role_code, event.target.checked)} />
              ))}
            </div>}
        {errors.role_codes && <p className={styles.hint} role="alert">{errors.role_codes}</p>}
        <Checkbox label="로그인 계정을 함께 만듭니다 (아이디: 사내 이메일)" checked={form.create_account} onChange={(event) => set("create_account", event.target.checked)} />
        {form.create_account && (
          <TextInput label="초기 비밀번호" type="password" autoComplete="new-password" required minLength={8} value={form.password} error={errors.password} hint="8자 이상. 응답과 화면에 다시 표시하지 않습니다." onChange={text("password")} />
        )}
      </fieldset>
    </div>
  )
}
