# 西红柿历险记 · 指定人物三关冒险

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

主角脸部直接使用用户指定的第二张原画，保留原图的眼睛、鼻子、微笑与刘海，并映射到有体积的头部曲面。Blender 重做约 6.4 头身的身体、连续肩臂与手腕、黑发侧马尾、白色蕾丝上衣、黑裙和白色金链斜挎包。蕾丝纹理取自同一原画的局部细节，裙子用连续腰臀曲线和细褶替换圆锥。移动时小幅转向，保持脸部可见。

战斗镜头俯角由约 36° 降至约 22°，三个轴保持一致缩放；人物在战斗画面中的缩放由 1.5 改为 2。电脑菜单和手机菜单分别适配画布尺寸。投影检查与实际截图分别记录，物理碰撞与攻击范围仍由游戏规则控制。

模型保留 20 根骨骼和六组动作：待机、行走、攻击、举盾、冲刺、大笑。关节使用混合权重，侧马尾、包与链条有轻微摆动；运行时将移动与上肢动作分层组合。暂停冻结骨骼与特效。面数、文件大小与格式检查记录见模型包中的 `模型规格.json` 和 `验收/GLB校验.json`。

所有敌人头部使用第一张照片的裁切头像，始终面向镜头，身体与职业装备仍有区别。真实命中事件携带敌人 ID，单独触发该小兵的头像闪色、回弹和星星，并保留伤害数字；击退后星星消散，头像实例释放。头像与特效共享纹理，实例材质各自独立。资源失败会显示重试入口，主角与小兵素材齐备后才开始推进战斗。

公开仓库与交付包包含游戏使用的脸部、敌人头像与蕾丝局部贴图，不包含完整原图。脸部为原图像素，侧后方、身体、鞋子和动作由本地补全；这不是 3D 扫描，侧面也不能当作原人物的准确侧脸。

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
| `src/hero-framing.ts` | 菜单与战斗的等比缩放及镜头位置 |
| `src/clock.ts` | 将渲染间隔拆成安全步长，保持低帧率下的战斗计时 |
| `src/main.ts` | 键盘、触控、页面与存档 |
| `public/models/reference-hero.glb` | 游戏实际加载的模型 |
| `3D人物/指定人物.blend` | 交付包内可编辑的本地 Blender 模型 |
| `3D人物/制作指定人物.py` | 指定原画人物的可复现建模脚本 |
| `tools/prepare_portraits.py` | 传入两张原始图片路径后生成裁切贴图 |
| `tools/prepare_lace.py` | 提取原画蕾丝局部并生成服装纹理 |
| `public/textures/` | 主角原画脸部、小兵照片头像与服装细节 |
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
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python 3D人物/制作指定人物.py
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

人物与受击专项验证：

```sh
NAIWA_URL=http://localhost:4192 python3 tests/browser_portraits.py
NAIWA_URL=http://localhost:4192 python3 tests/browser_framing.py
```

头像裁切可通过 `python3 tools/prepare_portraits.py --enemy <第一张照片路径> --hero <第二张原画路径>` 复现；脚本验证尺寸，不把原始图片复制到游戏目录。制作模型时只需要现有裁切贴图。
