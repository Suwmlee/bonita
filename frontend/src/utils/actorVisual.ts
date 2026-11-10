const PALETTES: Array<[string, string]> = [
  ["#8d6a52", "#3a2a22"],
  ["#5e86a0", "#24343f"],
  ["#9a6d8a", "#3a2833"],
  ["#6d9478", "#24352b"],
  ["#a56b5d", "#3a2622"],
  ["#7380a8", "#262a3d"],
  ["#b08a4f", "#3a301c"],
  ["#6d8e96", "#223033"],
]

export function actorGradient(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i)
    hash |= 0
  }
  const [from, to] = PALETTES[Math.abs(hash) % PALETTES.length]
  return `linear-gradient(155deg, ${from}, ${to})`
}

export function actorInitial(name: string): string {
  const trimmed = name.trim()
  if (!trimmed) return "?"
  return trimmed.slice(0, 1).toUpperCase()
}
