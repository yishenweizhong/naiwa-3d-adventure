/** Presentation scale is uniform; arena positions and hitboxes keep their own units. */
export function heroFraming(menu: boolean, portrait: boolean) {
  return {
    scale: menu ? (portrait ? 4 : 4.3) : 2,
    zoom: menu && portrait ? 1.75 : 1,
    cameraY: menu ? 6.5 : 12,
    cameraZ: 27,
    lookY: menu ? (portrait ? 2.35 : 2) : 0,
    lookZ: menu ? 0 : -2,
  };
}
