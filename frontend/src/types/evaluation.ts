export type EvaluationStatus = "작성중" | "제출" | "반려" | "확정" | "제외"

export type Grade = "S" | "A" | "B" | "C"

export type Evaluation = {
  eval_id: number
  emp_no: number
  employee_name: string | null
  eval_year: string
  snapshot_dept_no: number | null
  snapshot_pos_code: string | null
  evaluator_no: number
  evaluator_name: string | null
  created_by: number | null
  score: string
  grade: Grade
  comments: string
  eval_status: EvaluationStatus
  confirmed_by: number | null
  confirmed_at: string | null
  updated_at: string
}

export type EvaluationAction =
  | "CREATE"
  | "REVISE"
  | "SUBMIT"
  | "RETURN"
  | "REASSIGN"
  | "CONFIRM"
  | "CANCEL_CONFIRMATION"
  | "EXCLUDE"
  | "CANCEL_EXCLUSION"

export type EvaluationHistoryEntry = {
  history_id: number
  eval_id: number
  action: EvaluationAction
  from_status: EvaluationStatus | null
  to_status: EvaluationStatus
  actor_no: number
  actor_name: string | null
  from_evaluator_no: number | null
  to_evaluator_no: number | null
  score: string | null
  reason: string
  changed_at: string
}

export type EvaluatorCandidate = {
  emp_no: number
  name: string
  dept_no: number
  dept_name: string
}
