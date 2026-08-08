// Compact token formatting: 16608 -> "16.6K", 1642400 -> "1.64M"
export function fmtTokens(n) {
  n = n || 0
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}
