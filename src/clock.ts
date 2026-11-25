import { World, type Input } from "./model.ts";

// Rendering may be slow; simulation still advances in safe collision steps.
export function advanceWorld(world: World, elapsed: number, input: Input) {
  let remaining=Math.min(.25,Math.max(0,elapsed));
  while (remaining>1e-7) {
    const dt=Math.min(1/60,remaining);
    world.update(dt,input);
    remaining-=dt;
  }
}
