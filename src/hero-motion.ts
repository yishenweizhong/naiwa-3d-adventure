export type HeroMotion = "idle" | "walk" | "attack" | "defend" | "dash" | "laugh";

export function heroMotion(s: {
  phase: string;
  dashTime: number;
  defending: boolean;
  moving: boolean;
  action: string;
  actionTime: number;
}): HeroMotion {
  if (s.phase !== "playing" && s.phase !== "tutorial") return "idle";
  if (s.dashTime > 0 || (s.action === "dash" && s.actionTime > 0)) return "dash";
  if (s.action === "laugh" && s.actionTime > 0) return "laugh";
  if (s.defending) return "defend";
  if (s.action === "attack" && s.actionTime > 0) return "attack";
  return s.moving ? "walk" : "idle";
}
