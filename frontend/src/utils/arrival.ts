export function daysSinceArrivalLabel(acquiredDate: string | null, today = new Date()): string {
  if (!acquiredDate) {
    return 'お迎え日は未記録'
  }

  const [acquiredYear, acquiredMonth, acquiredDay] = acquiredDate.split('-').map(Number)

  if (!acquiredYear || !acquiredMonth || !acquiredDay) {
    return 'お迎え日は未記録'
  }

  const todayDate = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  const acquiredDateOnly = Date.UTC(acquiredYear, acquiredMonth - 1, acquiredDay)
  const millisecondsPerDay = 24 * 60 * 60 * 1000
  const daysSinceArrival = Math.max(0, Math.floor((todayDate - acquiredDateOnly) / millisecondsPerDay))

  return `いっしょに暮らして${daysSinceArrival}日目`
}
