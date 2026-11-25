import type { GameEvent } from "./model.ts";

export class GameAudio {
  enabled = true;
  context?: AudioContext;
  unlock() {
    if (!this.enabled) return;
    try {
      this.context ??= new AudioContext();
      void this.context.resume().catch(() => {});
    } catch {
      this.enabled = false;
    }
  }
  play(kind: GameEvent["kind"]) {
    if (!this.enabled || !this.context || this.context.state !== "running")
      return;
    const sounds: Record<string, [number, number, number]> = {
      shot: [440, 240, 0.075],
      hit: [150, 60, 0.07],
      hurt: [130, 70, 0.15],
      block: [820, 540, 0.09],
      dash: [280, 800, 0.12],
      laugh: [360, 900, 0.32],
      heal: [660, 990, 0.24],
      wave: [392, 588, 0.22],
      win: [523, 1046, 0.7],
      defeat: [220, 110, 0.55],
      thunder: [80, 30, 0.25],
    };
    const [from, to, duration] = sounds[kind] ?? sounds.hit;
    const now = this.context.currentTime;
    const osc = this.context.createOscillator(),
      gain = this.context.createGain();
    osc.type = kind === "hit" || kind === "hurt" ? "triangle" : "sine";
    osc.frequency.setValueAtTime(from, now);
    osc.frequency.exponentialRampToValueAtTime(to, now + duration);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(
      kind === "shot" ? 0.035 : 0.09,
      now + 0.01,
    );
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
    osc.connect(gain);
    gain.connect(this.context.destination);
    osc.start(now);
    osc.stop(now + duration + 0.02);
    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
  }
  suspend() {
    void this.context?.suspend().catch(() => {});
  }
}
