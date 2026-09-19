export type CurrentEmployee = {
  emp_no: number
  name: string
  dept_no: number | null
  dept_name: string | null
  position_code: string | null
  position_name: string | null
  tenure_status: string
}

export type CurrentUser = {
  id: number
  email: string
  is_staff: boolean
  is_superuser: boolean
  employee: CurrentEmployee | null
  roles: string[]
}
