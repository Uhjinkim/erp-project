import { BUSINESS_TIME_ZONE, businessToday } from "../../utils/dateTime"
import { routeHref } from "../../app/routing"
import type { EvaluationAction, EvaluationHistoryEntry, EvaluationStatus } from "../../types/evaluation"

export const HR_MANAGER_ROLE = "HR_MANAGER"
export const EDITABLE: EvaluationStatus[] = ["작성중", "반려"]
export const UNCONFIRMED: EvaluationStatus[] = ["작성중", "제출", "반려"]
export const STATUSES: EvaluationStatus[] = ["작성중", "제출", "반려", "확정", "제외"]
const CONTENT_ACTIONS: EvaluationAction[] = ["CREATE", "REVISE", "SUBMIT"]

type Tone = "neutral" | "info" | "success" | "warning" | "error"

// The backend decides every transition; tones only make the status readable.
export const STATUS_TONE: Record<EvaluationStatus, Tone> = {
  작성중: "neutral",
  제출: "info",
  반려: "warning",
  확정: "success",
  제외: "neutral",
}

export const ACTION_LABELS: Record<EvaluationAction, string> = {
  CREATE: "작성",
  REVISE: "수정",
  SUBMIT: "제출",
  RETURN: "반려",
  REASSIGN: "평가자 재배정",
  CONFIRM: "확정",
  CANCEL_CONFIRMATION: "확정 취소",
  EXCLUDE: "평가 제외",
  CANCEL_EXCLUSION: "제외 취소",
}

/** Years a new evaluation may target: this year and last year (backend rule). */
export function creatableYears() {
  const year = Number(businessToday().slice(0, 4))
  return [String(year), String(year - 1)]
}

export function filterYears() {
  const year = Number(businessToday().slice(0, 4))
  return [String(year), String(year - 1), String(year - 2)]
}

export function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString("ko-KR", { timeZone: BUSINESS_TIME_ZONE, dateStyle: "medium", timeStyle: "short" }) : "-"
}

/** Whoever wrote the evaluation leaves HR actions to another HR manager (guidance only). */
export function isAuthor(myNo: number, evaluatorNo: number, history: EvaluationHistoryEntry[]) {
  return evaluatorNo === myNo
    || history.some((entry) => CONTENT_ACTIONS.includes(entry.action) && entry.actor_no === myNo)
}

export function evaluationHref(screenId: string, params: Record<string, string> = {}) {
  const search = new URLSearchParams(params).toString()
  return routeHref({ moduleId: "evaluation", screenId, ...(search ? { search } : {}) })
}

export function go(screenId: string, params: Record<string, string> = {}) {
  window.location.hash = evaluationHref(screenId, params)
}

export function errorText(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}
