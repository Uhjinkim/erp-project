import { TextInput } from "../../../components/ui"
import type { PayrollComponent } from "../../../types/payroll"
import type { AmountValues } from "../model"
import styles from "../payroll.module.css"

type AmountFieldsProps = {
  components: PayrollComponent[]
  values: AmountValues
  onChange: (code: string, value: string) => void
  disabled?: boolean
}

export function AmountFields({ components, values, onChange, disabled = false }: AmountFieldsProps) {
  // Components arrive from the API already in payslip order.
  const groups: [string, PayrollComponent[]][] = [
    ["지급 항목", components.filter((item) => item.category === "지급")],
    ["공제 항목", components.filter((item) => item.category === "공제")],
  ]
  return (
    <div className={styles.amountGroups}>
      {groups.map(([legend, items]) => (
        <fieldset key={legend} className={styles.amountGroup} disabled={disabled}>
          <legend>{legend}</legend>
          {items.map((component) => (
            <TextInput
              key={component.code}
              label={component.name}
              type="number"
              min="0"
              step="1"
              inputMode="numeric"
              placeholder="미입력 시 저장하지 않음"
              value={values[component.code] ?? ""}
              onChange={(event) => onChange(component.code, event.target.value)}
            />
          ))}
        </fieldset>
      ))}
    </div>
  )
}
