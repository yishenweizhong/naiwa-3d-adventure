import fs from "node:fs";
import { createRequire } from "node:module";
// Resolve from this project (or the caller's explicit NODE_PATH for optional tools).
const require = createRequire(import.meta.url);
const validator = require("gltf-validator");
const path = new URL("../public/models/reference-hero.glb", import.meta.url);
const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(path)), { uri:"reference-hero.glb" });
fs.mkdirSync(new URL("../验收/",import.meta.url), {recursive:true});
fs.writeFileSync(new URL("../验收/GLB校验.json",import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report.issues,null,2));
if(report.issues.numErrors || report.issues.numWarnings) process.exit(1);
