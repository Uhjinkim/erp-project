import type { Route } from "../../app/routing"
import type { CurrentUser } from "../../types/auth"
import { FormScreen } from "./screens/FormScreen"
import { HrScreen } from "./screens/HrScreen"
import { MineScreen } from "./screens/MineScreen"
import { TeamScreen } from "./screens/TeamScreen"

/** Public entry for the evaluation screens registered in registration.ts. */
export function EvaluationModule({ route, user, enabled }: { route: Route; user: CurrentUser; enabled: boolean }) {
  if (route.screenId === "evaluation-form") return <FormScreen user={user} enabled={enabled} search={route.search} />
  if (route.screenId === "evaluation-hr") return <HrScreen user={user} enabled={enabled} search={route.search} />
  if (route.screenId === "evaluation-mine") return <MineScreen user={user} enabled={enabled} />
  return <TeamScreen user={user} enabled={enabled} />
}
