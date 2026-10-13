import { expect, mock, test } from "bun:test"

mock.module("../src/config/environment", () => ({ environment: { apiBaseUrl: "", apiTimeoutMs: 1000, authMode: "session" } }))
const { ModuleScreen } = await import("../src/app/ModuleScreen")
const { modules } = await import("../src/app/modules")
const { BoardScreen } = await import("../src/features/board")
const { EvaluationModule } = await import("../src/features/evaluation")
const { PayrollScreen } = await import("../src/features/payroll")
const { VacationPanel } = await import("../src/features/vacation")
const { EmptyState } = await import("../src/components/ui")
const user = { id: 1, email: "synthetic@example.test", employee: null, roles: [], is_staff: false, is_superuser: false }
const connection: Parameters<typeof ModuleScreen>[0]["connection"] = {
  health: null, checking: false, message: "", simulatedOffline: false,
  check: async () => {}, toggleOffline: () => {}, backendConnected: false, vacationConnected: false,
}

test("merged module dispatcher reaches every registered implementation screen", () => {
  const entries = { board: BoardScreen, evaluation: EvaluationModule, payroll: PayrollScreen, vacation: VacationPanel }
  for (const [moduleId, entry] of Object.entries(entries)) {
    const registration = modules.find((module) => module.id === moduleId)!
    for (const screen of registration.screens) {
      const route = { moduleId, screenId: screen.id, search: "requestId=12" }
      const result = ModuleScreen({ route, user, connection })
      expect(result.type).toBe(entry)
      if (moduleId === "vacation") {
        expect(result.props.screenId).toBe(screen.id)
        expect(result.props.search).toBe(route.search)
      } else expect(result.props.route).toEqual(route)
    }
  }
})

test("session-only modules keep their session gate and unfinished screens stay placeholders", () => {
  for (const moduleId of ["board", "evaluation", "payroll"]) {
    const screenId = modules.find((module) => module.id === moduleId)!.entry
    expect(ModuleScreen({ route: { moduleId, screenId }, user: null, connection }).type).toBe(EmptyState)
  }
  expect(ModuleScreen({ route: { moduleId: "workforce", screenId: "employee-detail" }, user, connection }).type).toBe(EmptyState)
})
