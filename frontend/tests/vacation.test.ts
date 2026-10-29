import { describe, expect, mock, test } from "bun:test"
import { availableActions, canResubmit, filterRequests, formFromRequest, formWithVacationType, requestIdFromSearch, snapshotChanges, transportInput, validateInput } from "../src/features/vacation/model"
import type { VacationHistory, VacationRequest, VacationSnapshot } from "../src/types/vacation"

mock.module("../src/config/environment", () => ({ environment: { apiBaseUrl: "", apiTimeoutMs: 1000, authMode: "session" } }))
const { loadVacationData } = await import("../src/features/vacation/data")
const item: VacationRequest = { request_id: 12, employee_no: 1001, approver_no: 2001, type_id: "ANNUAL", start_datetime: "2026-10-20T00:00:00.000Z", end_datetime: "2026-10-20T09:00:00.000Z", use_days: 1, status: "대기", approved_at: null, reject_reason: null, request_reason: "개인 일정" }

describe("vacation UI contracts", () => {
  test("direct request links reject ambiguous or unsafe identifiers", () => {
    expect(requestIdFromSearch("requestId=12")).toBe(12)
    for (const value of ["", "0", "-1", "1.5", "01", "1e2", "9007199254740992"]) expect(requestIdFromSearch(`requestId=${value}`)).toBeNull()
  })
  test("LV-005~007 guidance follows assigned employee and state without an HR override", () => {
    expect(availableActions(item, 1001)).toEqual(["cancel"])
    expect(availableActions(item, 2001)).toEqual(["approve", "reject"])
    expect(availableActions(item, 9001)).toEqual([])
    expect(availableActions({ ...item, status: "승인" }, 2001)).toEqual(["recall"])
    for (const status of ["반려", "취소", "회수"] as const) expect(availableActions({ ...item, status }, 2001)).toEqual([])
    expect(canResubmit({ ...item, status: "회수" }, 1001)).toBe(true)
    expect(canResubmit({ ...item, status: "회수" }, 2001)).toBe(false)
    expect(canResubmit({ ...item, status: "반려" }, 1001)).toBe(false)
  })
  test("resubmit retains dates and decimal data; transport is ISO", () => {
    const form = formFromRequest(item)
    expect(validateInput(form)).toEqual({})
    expect(new Date(transportInput(form).start_datetime).getTime()).toBe(new Date(item.start_datetime).getTime())
    expect(form.use_days).toBe("1")
    expect(form.reason).toBe("개인 일정")
  })
  test("new requests default to Seoul today at 09:00–18:00, including near midnight", () => {
    for (const instant of ["2026-10-28T15:59:37Z", "2026-10-29T14:59:37Z"]) {
      const form = formFromRequest(undefined, new Date(instant))
      expect(form.start_datetime).toBe("2026-10-29T09:00")
      expect(form.end_datetime).toBe("2026-10-29T18:00")
    }
  })
  test("request and resubmit transport always drop seconds and milliseconds", () => {
    const seconds = { ...item, start_datetime: "2026-10-20T00:15:37.123Z", end_datetime: "2026-10-20T09:30:59.999Z" }
    const form = formFromRequest(seconds)
    expect(form.start_datetime).toBe("2026-10-20T09:15")
    expect(form.end_datetime).toBe("2026-10-20T18:30")
    const expected = { ...form, start_datetime: "2026-10-20T00:15:00.000Z", end_datetime: "2026-10-20T09:30:00.000Z" }
    expect(transportInput(form)).toEqual(expected)
    expect(transportInput({ ...form, start_datetime: seconds.start_datetime, end_datetime: seconds.end_datetime })).toEqual(expected)
  })
  test("start times before 09:00 are rejected on any selected date", () => {
    const form = { ...formFromRequest(item), end_datetime: "2027-01-01T18:00" }
    for (const date of ["2026-10-29", "2027-01-01"]) {
      for (const time of ["00:00", "08:59"]) expect(validateInput({ ...form, start_datetime: `${date}T${time}` }).start_datetime).toBeDefined()
      for (const time of ["09:00", "13:30"]) expect(validateInput({ ...form, start_datetime: `${date}T${time}` })).toEqual({})
    }
  })
  test("form validates transport bounds without inventing duration policies", () => {
    const form = formFromRequest(item)
    for (const days of ["0", "-1", "10", "1.001", "NaN"]) expect(validateInput({ ...form, use_days: days }).use_days).toBeDefined()
    expect(validateInput({ ...form, use_days: "0.01", end_datetime: form.start_datetime })).toEqual({})
    expect(validateInput({ ...form, start_datetime: "" }).start_datetime).toBeDefined()
    expect(validateInput({ ...form, end_datetime: "2026-01-01T00:00" }).end_datetime).toBeDefined()
    expect(validateInput({ ...form, reason: "가".repeat(256) }).reason).toBeDefined()
  })
  test("filters and sorting use fetched scope and do not mutate it", () => {
    const rows = [item, { ...item, request_id: 13, status: "승인" as const }]
    expect(filterRequests(rows, "status=승인&type=ANNUAL&q=1001&from=2026-10-19&to=2026-10-21").map((row) => row.request_id)).toEqual([13])
    expect(filterRequests(rows, "q=missing")).toEqual([])
    expect(filterRequests(rows, "order=asc").map((row) => row.request_id)).toEqual([12, 13])
    expect(filterRequests(rows, "").map((row) => row.request_id)).toEqual([13, 12])
    expect(rows.map((row) => row.request_id)).toEqual([12, 13])
  })
  test("history only compares persisted snapshots", () => {
    const snapshot: VacationSnapshot = { type_id: item.type_id, start_datetime: item.start_datetime, end_datetime: item.end_datetime, use_days: 1, approver_no: 2001, request_reason: null, approved_at: null, reject_reason: null }
    const entry: VacationHistory = { history_id: 1, request_id: 12, from_status: "회수", to_status: "대기", actor_employee_no: 1001, reason: null, changed_at: item.start_datetime }
    expect(snapshotChanges(entry, [])).toBeNull()
    expect(snapshotChanges({ ...entry, before_values: snapshot, after_values: { ...snapshot, use_days: "1.00" } }, [])).toEqual([])
    expect(snapshotChanges({ ...entry, before_values: snapshot, after_values: { ...snapshot, use_days: "2.00", request_reason: "수정" } }, []).map((change) => change.key)).toEqual(["use_days", "request_reason"])
  })
  test("partial list failures preserve accessible history", async () => {
    const mine = mock(async () => { throw new Error("forbidden") })
    const history = mock(async () => [])
    const api = { types: async () => [], mine, approvals: async () => [item], history }
    const result = await loadVacationData(2001, "leave-detail", 12, api)
    expect(result.approvals).toEqual([item])
    expect(result.errors.mine?.message).toBe("forbidden")
    expect(result.errors.history).toBeUndefined()
    expect(history).toHaveBeenCalledWith(2001, 12)
    await loadVacationData(2001, "leave-queue", null, api)
    expect(mine).toHaveBeenCalledTimes(1)
    expect(history).toHaveBeenCalledTimes(1)
  })
})


test("balance reads share the initial types request and are limited to request forms", async () => {
  const types = mock(async () => [{ type_id: "ANNUAL", type_name: "연차", is_paid: true, deduct_days: 1, remaining_days: "3.50" }])
  const api = { types, mine: mock(async () => []), approvals: mock(async () => []), history: mock(async () => []) }
  const result = await loadVacationData(1001, "leave-apply", null, api)
  expect(types).toHaveBeenLastCalledWith(1001, true)
  expect(types).toHaveBeenCalledTimes(1)
  expect(api.mine).toHaveBeenCalledTimes(0)
  expect(api.approvals).toHaveBeenCalledTimes(0)
  expect(result.types[0].remaining_days).toBe("3.50")
  await loadVacationData(1001, "leave-resubmit", 12, api)
  expect(types).toHaveBeenLastCalledWith(1001, true)
  await loadVacationData(1001, "leave-mine", null, api)
  expect(types).toHaveBeenLastCalledWith(1001, false)
})


test("type selection uses the supplied day unit while retaining the schedule and reason", () => {
  const form = formFromRequest(item)
  const half = formWithVacationType(form, { type_id: "HALF", type_name: "반차", deduct_days: "0.50", is_paid: true })
  expect(half).toEqual({ ...form, type_id: "HALF", use_days: "0.50" })
  expect(formWithVacationType(half, { type_id: "ANNUAL", type_name: "연차", deduct_days: 1, is_paid: true }).use_days).toBe("1.00")
  expect(formWithVacationType(half, { type_id: "SICK", type_name: "병가", deduct_days: 0, is_paid: true }).use_days).toBe("0.50")
})
