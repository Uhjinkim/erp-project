import { describe, expect, test } from "bun:test"
import { creatableYears, isAuthor } from "../src/features/evaluation/model"
import type { EvaluationAction, EvaluationHistoryEntry } from "../src/types/evaluation"

const entry = (history_id: number, action: EvaluationAction, actor_no: number): EvaluationHistoryEntry => ({
  history_id, eval_id: 1, action, from_status: null, to_status: "작성중", actor_no, actor_name: null,
  from_evaluator_no: null, to_evaluator_no: null, score: null, reason: "", changed_at: "2026-10-01T00:00:00Z",
})

describe("evaluation model", () => {
  test("creatable years are this year and last year", () => {
    const year = new Date().getFullYear()
    expect(creatableYears()).toEqual([String(year), String(year - 1)])
  })

  test("the current evaluator is an author", () => {
    expect(isAuthor(10, 10, [])).toBe(true)
  })

  test("a former evaluator who wrote content stays an author after reassignment", () => {
    expect(isAuthor(10, 20, [entry(1, "CREATE", 10), entry(2, "REASSIGN", 30)])).toBe(true)
  })

  test("HR actions alone do not make an author", () => {
    expect(isAuthor(30, 20, [entry(1, "CREATE", 20), entry(2, "RETURN", 30), entry(3, "REASSIGN", 30)])).toBe(false)
  })
})
