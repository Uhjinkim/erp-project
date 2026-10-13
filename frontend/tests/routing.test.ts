import { describe, expect, test } from "bun:test"
import { modules } from "../src/app/modules"
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
  test("malformed and unregistered URLs cannot resolve a screen", () => {
    for (const hash of ["#https://evil.example", "#/vacation/leave-apply/extra", "#/%2f/login", "#/vacation"])
      expect(parseRoute(hash)).toBeNull()
    expect(findScreen(parseRoute("#/unknown/screen"), modules)).toBeNull()
  })
  test("feature screens have one owner", () => {
    const ids = modules.flatMap((module) => module.screens.map((screen) => screen.id))
    expect(new Set(ids).size).toBe(ids.length)
    // Login and expired/forbidden are handled by the session layer.
    expect(ids.length).toBe(35)
  })
  test("detail query remains on the registered screen", () => {
    const route = { moduleId: "vacation", screenId: "leave-detail", search: "requestId=12" }
    expect(parseRoute(routeHref(route))).toEqual(route)
    expect(findScreen(parseRoute(routeHref(route)), modules)?.screen.id).toBe("leave-detail")
  })
})
