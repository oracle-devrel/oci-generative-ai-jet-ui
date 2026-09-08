// Display helpers — keep raw API numbers; format only at the edge.

export const pct = (v: number): string => `${(v * 100).toFixed(1)}%`;
export const pctRound = (v: number): string => `${Math.round(v * 100)}%`;
export const num1 = (v: number): string => v.toFixed(1);
export const num2 = (v: number): string => v.toFixed(2);

export const signed = (v: number, digits = 1): string =>
  `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;

// A pure team-name -> stable hue, used only for the small team monogram tile
// styling. Deterministic so a team always renders the same.
export function teamHue(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) % 360;
  }
  return h;
}

// First-letter monogram (Spain -> ES-ish initial). We use the first
// character; for two-word names take the first letter of each word.
export function monogram(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}
