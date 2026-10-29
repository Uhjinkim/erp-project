export const BUSINESS_TIME_ZONE = "Asia/Seoul"

const dateTimeFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: BUSINESS_TIME_ZONE,
  year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
})

/** ISO-shaped wall time for business date fields, independent of the browser zone. */
export function businessDateTime(value: string | Date) {
  const date = typeof value === "string" ? new Date(value) : value
  if (Number.isNaN(date.getTime())) return ""
  const parts = Object.fromEntries(dateTimeFormatter.formatToParts(date).map(({ type, value }) => [type, value]))
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}`
}

export function businessToday(now = new Date()) {
  return businessDateTime(now).slice(0, 10)
}

/** datetime-local has no zone; modern Korean business input is UTC+09:00. */
export function parseBusinessDateTime(value: string) {
  const wallTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/
  const zonedTime = /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/i
  return new Date(wallTime.test(value) ? `${value}+09:00` : zonedTime.test(value) ? value : NaN)
}
