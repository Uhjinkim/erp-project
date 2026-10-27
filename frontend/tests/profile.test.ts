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

describe("my-profile edit mode", () => {
  const current = { phone: "010", address: null, email: "a@example.test", bank_code: "004", account_no: "111-111" }

  test("edit form starts from current values without the raw account number", () => {
    expect(model.toEditForm(current)).toEqual({ phone: "010", address: "", email: "a@example.test", bank_code: "004", account_no: "" })
  })

  test("only changed fields become the edit request and cleared contact fields are sent as empty (HR-002)", () => {
    const form = model.toEditForm(current)
    expect(model.toEditPayload(form, current)).toEqual({})
    expect(model.toEditPayload({ ...form, phone: " 011 ", address: " 새 주소 " }, current)).toEqual({ phone: "011", address: "새 주소" })
    expect(model.toEditPayload({ ...form, phone: "  " }, current)).toEqual({ phone: "" })
    expect(model.toEditPayload({ ...form, email: " New@Example.test " }, current)).toEqual({ email: "new@example.test" })
    expect(model.toEditPayload({ ...form, account_no: " 222 " }, current)).toEqual({ bank_code: "004", account_no: "222" })
  })

  test("edit validation needs a change, a valid email, and bank code with account number together", () => {
    const form = model.toEditForm(current)
    expect(model.validateEdit(form, current).form).toBeDefined()
    expect(model.validateEdit({ ...form, email: "" }, current).email).toBeDefined()
    expect(model.validateEdit({ ...form, email: "invalid" }, current).email).toBeDefined()
    expect(model.validateEdit({ ...form, bank_code: "088" }, current).account_no).toBeDefined()
    expect(model.validateEdit({ ...form, bank_code: "", account_no: "222" }, current).bank_code).toBeDefined()
    expect(model.validateEdit({ ...form, phone: "011" }, current)).toEqual({})
  })
})
