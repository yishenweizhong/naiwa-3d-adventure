# 西红柿历险记 · 可爱卡通三关冒险

在线游玩：https://yishenweizhong.github.io/naiwa-3d-adventure/

点击「开始冒险」即可开打。「安全练习」为可选入口，练习中随时可以直接开打。依次守住奶笑村、穿过风车谷、击败晨光钟楼的长夜钟守，首页可重返已解锁关卡。

新玩家默认「轻松玩」，受到的伤害为标准模式的约六成，补给回复更多；可切换「标准挑战」。每关通关得一星，剩余生命至少 60 得一星，限时通关得一星（第一关 90 秒、第二关 140 秒、第三关 200 秒）。两种模式分别保存最佳星级与最快用时。

Three.js 绘制三维人物、敌人、村庄、风车、河流、桥梁、钟楼、弹幕、落雷和风墙。HUD 与触控按钮使用 HTML。游戏不需要登录，也不调用在线模型。

## 操作

| 动作 | 电脑 | 手机 |
|---|---|---|
| 移动 | WASD / 方向键 | 拖动摇杆 |
| 奶弹 | 按住 J，自动瞄准 | 按住奶弹 |
| 举盾 | 按住 K，减少 60% 伤害 | 按住举盾 |
| 冲刺 | L，2.5 秒冷却 | 点击冲刺 |
| 大笑 | 笑能满后按空格 | 点击大笑 |
| 暂停 | Esc | 点击右上角暂停 |

失败只重开当前关卡。进度保存在当前浏览器的 localStorage，刷新后点击「继续上次冒险」，在「进度已恢复」窗口中点击「继续冒险」再开打；不同设备不会同步进度。切到后台会自动暂停。手机横屏视野更好，竖屏也保留全部触控控件。

## 人物与动作

Blender 人物重新建模为柔和的玩偶比例，保留棕色双马尾、黑色猫耳帽、黄黑围巾、深蓝外套、斜纹领带，以及偏细长的眼形。圆润脸型、几何五官、柔和微笑替代上一版的照片投射脸。敌人改为不同职业的玩偶角色，三章场景共用圆角建筑与柔和材质。

模型有 20 根骨骼、41,972 个三角面和六组动作：待机、行走、攻击、举盾、冲刺、大笑。关节使用混合权重，头发和围巾有延迟摆动；运行时平滑转向、渐变切换，将移动与上肢动作分层组合。暂停冻结骨骼画面。优化后的 GLB 为 1,436,524 字节，格式校验无错误和警告。

人物根据用户提供的照片在本地独立制作，没有贴真人脸照片。它是可辨识的卡通表达，没有进行 3D 扫描，不能保证真人 100% 还原。原始照片不进入公开仓库或交付包。

## 本地运行

需要 Node.js 22.18 或以上。

```sh
npm ci
npm run dev
npm test
npm run build
npm run preview -- --port 4188
```

默认开发地址为 http://localhost:5186；上面预览命令地址为 http://localhost:4188。部署包需要通过 HTTP 服务或静态网站打开，不能直接双击 HTML。

## 文件

| 路径 | 用途 |
|---|---|
| `src/model.ts` | 独立的战斗、碰撞与存档规则 |
| `src/levels.ts` | 三关配置、敌人波次与首领 |
| `src/scene3d.ts` | 三维场景、人物动作、投射物与预警 |
| `src/clock.ts` | 将渲染间隔拆成安全步长，保持低帧率下的战斗计时 |
| `src/main.ts` | 键盘、触控、页面与存档 |
| `public/models/reference-hero.glb` | 游戏实际加载的模型 |
| `3D人物/可爱卡通人物.blend` | 交付包内可编辑的本地 Blender 模型 |
| `3D人物/制作卡通人物.py` | 独立新场景中的可复现建模脚本 |
| `src/cute.css` | 电脑、手机竖屏与横屏的布局和控件 |
| `src/progress.ts` | 两种难度的星级与最佳成绩 |
| `public/models/kenney/` | 实际导入的 CC0 云朵与草丛几何 |
| `参考项目/使用说明.md` | 六个 GitHub 项目的来源、许可与实际使用范围 |
| `tests/` | 规则、真实按键、手机模拟触控与资源失败检查 |
| `docs/` | GitHub Pages 静态部署目录 |

公开仓库只包含游戏运行所需文件和可复现源码。完整 Blender 模型、三视图和实际操作录像随本地交付包提供。

## 发布

GitHub Pages 从 `main` 分支 `/docs` 目录发布。修改后执行 `npm run build`，将 `dist` 内容同步到 `docs` 并保留 `.nojekyll`。相对资源路径支持仓库子目录托管。

本版验证结果与实际操作录像见交付目录的 `验收/` 和 `优化说明.md`。规则测试、真实通关与公开网站验收分别记录，不以页面返回 200 代替实际可玩验证。

本次核实了 Three.js、glTF Transform、glTF Validator、Kenney 3D Platformer、drei 与 ActionPoser 六个 GitHub 项目，五项进入工作流程，第六项仅评估。完整来源与差异说明见 `参考项目/使用说明.md`。运行时使用 Three.js 的 MIT 代码与 Kenney 的 CC0 几何，声明见 `public/THIRD_PARTY_NOTICES.md`；独立参考文件保留各自原许可。

重新制作模型时，在仓库根目录执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python 3D人物/制作卡通人物.py
python3 tools/normalize_model.py
npm install --no-save @gltf-transform/cli@4.2.1 gltf-validator
npx gltf-transform dedup public/models/reference-hero.glb /tmp/naiwa-dedup.glb
npx gltf-transform resample /tmp/naiwa-dedup.glb /tmp/naiwa-resampled.glb
npx gltf-transform prune /tmp/naiwa-resampled.glb public/models/reference-hero.glb
node tools/validate_model.mjs
npm run build
python3 tools/package_game.py
```

打包脚本另需 Python Pillow。浏览器验收另需 Python Playwright 和 Chromium；执行前设置 `NAIWA_URL` 为当前预览地址。桌面浏览器与模拟触控分别验证，未将模拟结果说成真实手机实测。
