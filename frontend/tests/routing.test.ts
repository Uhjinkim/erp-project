import { describe, expect, test } from "bun:test"
import { modules, visibleModules } from "../src/app/modules"
import { defaultRoute, findScreen, parseRoute, routeHref } from "../src/app/routing"

describe("screen routing", () => {
  test("default and registered URLs survive serialization", () => {
    expect(parseRoute("")).toEqual(defaultRoute)
    for (const module of modules) {
      expect(module.screens.some((screen) => screen.id === module.entry)).toBe(true)
      for (const screen of module.screens) {
        const route = { moduleId: module.id, screenId: screen.id }
        expect(findScreen(parseRoute(routeHref(route)), modules)?.screen.id).toBe(screen.id)
      }
    }
  })
  test("workforce menu matches the HR_MANAGER or superuser server permission", () => {
    const user = (roles: string[], is_superuser = false) => ({ id: 1, email: "synthetic@example.test", is_staff: false, is_superuser, employee: null, roles })
    const workforce = parseRoute("#/workforce/employee-list")
    expect(findScreen(workforce, visibleModules(user(["HR_MANAGER"])))?.module.id).toBe("workforce")
    expect(findScreen(workforce, visibleModules(user([], true)))?.module.id).toBe("workforce")
    for (const viewer of [user([]), user(["PAYROLL_MANAGER"]), null]) {
      expect(visibleModules(viewer).some((module) => module.id === "workforce")).toBe(false)
      expect(findScreen(workforce, visibleModules(viewer))).toBeNull()
      expect(visibleModules(viewer).some((module) => module.id === "profile")).toBe(true)
    }
  })
  test("malformed and unregistered URLs cannot resolve a screen", () => {
    for (const hash of ["#https://evil.example", "#/vacation/leave-apply/extra", "#/%2f/login", "#/vacation"])
      expect(parseRoute(hash)).toBeNull()
    expect(findScreen(parseRoute("#/unknown/screen"), modules)).toBeNull()
  })
  test("feature screens have one owner", () => {
    const ids = modules.flatMap((module) => module.screens.map((screen) => screen.id))
    expect(new Set(ids).size).toBe(ids.length)
    // Login and expired/forbidden are handled by the session layer.
    // contact-edit and change-request are merged into the my-profile edit mode.
    expect(ids.length).toBe(30)
  })
  test("removed diagnostic routes do not resolve", () => {
    for (const hash of ["#/system/system-health", "#/design-system/gallery", "#/home/home", "#/home/manager-home", "#/system/account-admin"]) {
      expect(findScreen(parseRoute(hash), modules)).toBeNull()
    }
  })
  test("detail query remains on the registered screen", () => {
    const route = { moduleId: "vacation", screenId: "leave-detail", search: "requestId=12" }
    expect(parseRoute(routeHref(route))).toEqual(route)
    expect(findScreen(parseRoute(routeHref(route)), modules)?.screen.id).toBe("leave-detail")
  })
})


describe("role-specific navigation", () => {
  const user = (roles: string[] = [], is_department_head = false, is_superuser = false) => ({
    id: 1, email: "synthetic@example.test", is_staff: false, is_superuser, is_department_head, employee: null, roles,
  })
  const menu = (viewer: ReturnType<typeof user>, moduleId: string) => visibleModules(viewer)
    .find((module) => module.id === moduleId)!.screens.filter((screen) => screen.menu !== false).map((screen) => screen.id)

  test("members enter their own evaluation and never see HR or payroll management menus", () => {
    const member = user()
    expect(menu(member, "evaluation")).toEqual(["evaluation-mine"])
    expect(menu(member, "payroll")).toEqual(["payslip"])
    expect(menu(member, "profile")).toEqual(["my-profile", "change-history"])
    expect(menu(member, "vacation")).toEqual(["leave-apply", "leave-mine"])
    expect(visibleModules(member).find((module) => module.id === "evaluation")!.entry).toBe("evaluation-mine")
    for (const hash of ["#/payroll/payroll-create", "#/evaluation/evaluation-hr", "#/profile/change-review?requestId=1"]) {
      expect(findScreen(parseRoute(hash), visibleModules(member))).toBeNull()
    }
  })
  test("heads and mixed roles get their existing workflows without losing the personal screens", () => {
    expect(menu(user([], true), "evaluation")).toEqual(["evaluation-team", "evaluation-mine"])
    expect(menu(user([], true), "vacation")).toContain("leave-queue")
    expect(menu(user(["HR_MANAGER"], true), "evaluation")).toEqual(["evaluation-team", "evaluation-hr", "evaluation-mine"])
    expect(menu(user(["HR_MANAGER"]), "profile")).toContain("change-queue")
    expect(menu(user(["HR_MANAGER"]), "vacation")).toContain("leave-queue")
    expect(menu(user(["HR_LEAVE_APPROVER"]), "vacation")).not.toContain("leave-queue")
    expect(visibleModules(user(["HR_MANAGER"])).find((module) => module.id === "evaluation")!.entry).toBe("evaluation-hr")
    for (const viewer of [user(["PAYROLL_MANAGER"]), user(["PAYROLL_MANAGER"], false, true)]) {
      expect(menu(viewer, "payroll")).toHaveLength(5)
    }
    expect(menu(user([], false, true), "payroll")).toEqual(["payslip"])
    expect(menu(user([], false, true), "profile")).toContain("change-queue")
  })
  test("contextual links remain registered for previous authors and assigned approvers", () => {
    for (const hash of ["#/evaluation/evaluation-form?evalId=1", "#/vacation/leave-approve?requestId=1", "#/vacation/leave-recall?requestId=1"]) {
      expect(findScreen(parseRoute(hash), visibleModules(user()))).not.toBeNull()
    }
    expect(visibleModules(user()).some((module) => ["home", "system"].includes(module.id))).toBe(false)
    for (const module of visibleModules(user())) expect(module.screens.some((screen) => screen.id === module.entry)).toBe(true)
  })
})
