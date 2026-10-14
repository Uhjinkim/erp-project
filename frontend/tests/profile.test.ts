import { describe, expect, mock, test } from "bun:test"

mock.module("../src/config/environment", () => ({ environment: { apiBaseUrl: "", apiTimeoutMs: 1000 } }))
const model = await import("../src/features/profile/model")

describe("profile display rules", () => {
  test("screen links keep query keys and drop empty ones", () => {
    expect(model.profileHref("change-review", { requestId: 4 })).toBe("#/profile/change-review?requestId=4")
    expect(model.profileHref("change-history", { status: "" })).toBe("#/profile/change-history")
  })

  test("account numbers are masked like the server and server-masked values stay as they are", () => {
    expect(model.maskAccount("123-456-7890")).toBe("******7890")
    expect(model.maskAccount("1234")).toBe("****")
    expect(model.maskAccount("******7890")).toBe("******7890")
    expect(model.maskAccount(null)).toBe("미등록")
    expect(model.displayValue("email", "a@example.test")).toBe("a@example.test")
    expect(model.displayValue("account_no", "1234567890")).toBe("******7890")
  })

  test("status filter accepts known statuses only", () => {
    expect(model.parseStatus("반려")).toBe("반려")
    expect(model.parseStatus("unknown")).toBeUndefined()
    expect(model.parseStatus(null)).toBeUndefined()
  })
})

describe("self-service forms", () => {
  test("contact edit sends trimmed values and nulls for blanks (HR-002)", () => {
    expect(model.toContactPayload({ phone: " 010 ", address: "  " })).toEqual({ phone: "010", address: null })
    expect(model.contactChanged({ phone: "010", address: "" }, { phone: "010", address: null })).toBe(false)
    expect(model.contactChanged({ phone: "011", address: "" }, { phone: "010", address: null })).toBe(true)
  })

  test("change requests need a value and bank code with account number together (FN-HR-003)", () => {
    const empty = { email: "", bank_code: "", account_no: "" }
    expect(model.validateChangeRequest(empty).form).toBeDefined()
    expect(model.validateChangeRequest({ ...empty, account_no: "123" }).bank_code).toBeDefined()
    expect(model.validateChangeRequest({ ...empty, bank_code: "004" }).account_no).toBeDefined()
    expect(model.validateChangeRequest({ ...empty, email: "invalid" }).email).toBeDefined()
    expect(model.validateChangeRequest({ ...empty, email: "new@example.test" })).toEqual({})
  })

  test("only entered fields are requested so the rest stay unchanged", () => {
    expect(model.toChangeRequestPayload({ email: " New@Example.test ", bank_code: "", account_no: "" })).toEqual({ email: "new@example.test" })
    expect(model.toChangeRequestPayload({ email: "", bank_code: "004", account_no: " 123 " })).toEqual({ bank_code: "004", account_no: "123" })
  })
})
