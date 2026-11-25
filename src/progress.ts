import type { LevelId } from "./levels.ts";
import type { Phase } from "./model.ts";

export type Difficulty = "easy" | "normal";
export type Records = Partial<Record<`${Difficulty}-${LevelId}`, { stars: number; time: number }>>;
const par = { 1: 90, 2: 140, 3: 200 };
export function starsFor(phase: Phase, hp: number, elapsed: number, level: LevelId) {
  return phase === "won" ? 1 + Number(hp >= 60) + Number(elapsed <= par[level]) : 0;
}
export function readRecords(text: string | null): Records {
  if (!text || text.length > 3000) return {};
  try {
    const raw = JSON.parse(text), records: Records = {};
    if (!raw || typeof raw !== "object") return records;
    for (const [key, value] of Object.entries(raw)) {
      const v = value as { stars?: number; time?: number } | null;
      if (!/^(easy|normal)-[123]$/.test(key) || !v ||
          !Number.isInteger(v.stars) || v.stars! < 1 || v.stars! > 3 ||
          typeof v.time !== "number" || !Number.isFinite(v.time) || v.time < 0 || v.time > 86400) continue;
      records[key as keyof Records] = { stars: v.stars!, time: v.time };
    }
    return records;
  } catch { return {}; }
}
export function updateRecord(records: Records, level: LevelId, mode: Difficulty, stars: number, time: number): Records {
  if (!Number.isInteger(stars) || stars < 1 || stars > 3 || !Number.isFinite(time) || time < 0) return records;
  const key = `${mode}-${level}` as const, before = records[key];
  return { ...records, [key]: { stars: Math.max(before?.stars ?? 0, stars), time: Math.min(before?.time ?? Infinity, time) } };
}
