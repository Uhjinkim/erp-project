import { requestJson } from "./client"
import type {
  Evaluation,
  EvaluationHistoryEntry,
  EvaluatorCandidate,
} from "../types/evaluation"

const BASE = "/api/evaluations/"

function post<T>(path: string, body?: object) {
  return requestJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  })
}

export async function listEvaluations(year?: string) {
  const query = year ? `?year=${encodeURIComponent(year)}` : ""
  return requestJson<Evaluation[]>(`${BASE}${query}`)
}

export async function getEvaluation(evalId: number) {
  return requestJson<Evaluation>(`${BASE}${evalId}/`)
}

export async function getEvaluationHistory(evalId: number) {
  return requestJson<EvaluationHistoryEntry[]>(`${BASE}${evalId}/history/`)
}

export async function listEvaluatorCandidates() {
  return requestJson<EvaluatorCandidate[]>(`${BASE}evaluator-candidates/`)
}

export async function createEvaluation(input: {
  emp_no: number
  eval_year: string
  score: string
  comments: string
}) {
  return post<Evaluation>(BASE, input)
}

export async function reviseEvaluation(evalId: number, input: { score: string; comments: string }) {
  return requestJson<Evaluation>(`${BASE}${evalId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })
}

export async function submitEvaluation(evalId: number) {
  return post<Evaluation>(`${BASE}${evalId}/submit/`)
}

export async function returnEvaluation(evalId: number, reason: string) {
  return post<Evaluation>(`${BASE}${evalId}/return/`, { reason })
}

export async function reassignEvaluation(evalId: number, evaluatorNo: number, reason: string) {
  return post<Evaluation>(`${BASE}${evalId}/reassign/`, { evaluator_no: evaluatorNo, reason })
}

export async function confirmEvaluation(evalId: number) {
  return post<Evaluation>(`${BASE}${evalId}/confirm/`)
}

export async function cancelConfirmation(evalId: number, reason: string) {
  return post<Evaluation>(`${BASE}${evalId}/cancel-confirmation/`, { reason })
}

export async function excludeEvaluation(evalId: number, reason: string) {
  return post<Evaluation>(`${BASE}${evalId}/exclude/`, { reason })
}

export async function cancelExclusion(evalId: number, reason: string) {
  return post<Evaluation>(`${BASE}${evalId}/cancel-exclusion/`, { reason })
}
