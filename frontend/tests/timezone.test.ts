import { describe, expect, test } from "bun:test"
import { businessDateTime, businessToday, parseBusinessDateTime } from "../src/utils/dateTime"
import { displayDateTime, filterRequests, formFromRequest, transportInput, validateInput } from "../src/features/vacation/model"
import { formatDateTime as workforceDateTime, localToday } from "../src/features/workforce/model"
import { formatDateTime as profileDateTime } from "../src/features/profile/model"
import { formatDateTime as boardDateTime } from "../src/features/board/boardModel"
import { formatDateTime as evaluationDateTime } from "../src/features/evaluation/model"
import { currentPeriod } from "../src/features/payroll/model"
import type { VacationRequest } from "../src/types/vacation"

describe("Asia/Seoul business time regardless of device timezone", () => {
  test("Seoul midnight, today and month rollover use the same instant", () => {
    const now = new Date("2026-10-31T15:00:00Z")
    expect(businessDateTime(now)).toBe("2026-11-01T00:00:00")
    expect(businessToday(now)).toBe("2026-11-01")
    expect(localToday(now)).toBe("2026-11-01")
    expect(currentPeriod(now)).toBe("2026-11")
    expect(businessDateTime("invalid")).toBe("")
  })
  test("09:00 input means 00:00 UTC and resubmits without drifting", () => {
    const form = { ...formFromRequest(undefined, new Date("2026-10-28T15:00:00Z")), type_id: "ANNUAL" }
    expect(validateInput(form)).toEqual({})
    const payload = transportInput(form)
    expect(payload.start_datetime).toBe("2026-10-29T00:00:00.000Z")
    expect(payload.end_datetime).toBe("2026-10-29T09:00:00.000Z")
    const item: VacationRequest = { ...payload, request_id: 1, employee_no: 1, approver_no: 2, status: "대기", approved_at: null, reject_reason: null, request_reason: "" }
    expect(formFromRequest(item).start_datetime).toBe("2026-10-29T09:00")
    expect(transportInput(formFromRequest(item))).toEqual(payload)
    expect(parseBusinessDateTime("2026-10-29T09:00:37+09:00").toISOString()).toBe("2026-10-29T00:00:37.000Z")
    expect(Number.isNaN(parseBusinessDateTime("").getTime())).toBe(true)
    expect(Number.isNaN(parseBusinessDateTime("2026-10-29").getTime())).toBe(true)
  })
  test("vacation filtering follows Seoul date across UTC midnight", () => {
    const item = { request_id: 1, start_datetime: "2026-10-28T15:30:00Z" } as VacationRequest
    expect(filterRequests([item], "from=2026-10-29&to=2026-10-29")).toEqual([item])
    expect(filterRequests([item], "from=2026-10-28&to=2026-10-28")).toEqual([])
  })
  test("vacation and other processing histories display Seoul time", () => {
    const instant = "2026-10-29T00:00:00Z"
    for (const format of [displayDateTime, workforceDateTime, profileDateTime, boardDateTime, evaluationDateTime]) {
      expect(format(instant)).toContain("오전 9:00")
      expect(format(instant)).toContain("29")
    }
  })
})
