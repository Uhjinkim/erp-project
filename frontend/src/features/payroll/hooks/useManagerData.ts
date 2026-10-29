import { useCallback } from "react"

import { loadAllPayrollStatements, loadPayrollComponents, loadPayrollTargets } from "../../../api/payroll"
import { usePayrollQuery } from "./usePayrollQuery"

// Components, payroll targets and every statement: the inputs of the manager screens.
export function useManagerData(enabled: boolean) {
  const load = useCallback(async () => {
    const [components, targets, statements] = await Promise.all([
      loadPayrollComponents(),
      loadPayrollTargets(),
      loadAllPayrollStatements(),
    ])
    return { components, targets, statements }
  }, [])
  return usePayrollQuery(enabled, load)
}
