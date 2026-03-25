export type TruthState = 'available' | 'unknown' | 'hidden'

export type TruthValue<T> = {
  state: TruthState
  value?: T
}

export function available<T>(value: T): TruthValue<T> {
  return { state: 'available', value }
}

export function unknown<T>(): TruthValue<T> {
  return { state: 'unknown' }
}

export function hidden<T>(): TruthValue<T> {
  return { state: 'hidden' }
}

export function isAvailable<T>(value: TruthValue<T>): value is TruthValue<T> & { value: T } {
  return value.state === 'available' && value.value !== undefined
}

export function withCriticalFallback<T>(input: TruthValue<T>): TruthValue<T> {
  return input.state === 'unknown' ? hidden<T>() : input
}

export function withNonCriticalFallback<T>(input: TruthValue<T>, fallback: T): TruthValue<T> {
  if (input.state === 'available' && input.value !== undefined) return input
  if (input.state === 'hidden') return input
  return available(fallback)
}
