---
name: blender-editable-timeline
slug: blender-editable-timeline
displayName: "Blender Editable Timeline (可交给客户微调的 Blender 工程)"
category: video
version: 1.0.0
description: "Hand a non-technical client a Blender video timeline they can actually adjust themselves: every caption is a native TEXT strip (not baked into a PNG), every image layer sits on a documented channel, and the project survives a client saving over it. Use when the deliverable is 'a project file I can tweak' rather than a rendered MP4, when captions/subtitles must be editable, or when you hit Blender 5.x VSE traps: a blank sequencer with a populated timeline, strips silently shoved to a different frame range, a canvas colour that disagrees with the pasted image, or a collapsed undo history. Ships the measured API facts and a safe channel-plan script."
description_zh: "把一个客户自己能改的 Blender 时间线交出去：字幕全部用原生 TEXT 条（不烤进 PNG）、每层占用有文档的通道、工程能扛住客户覆盖保存。适用于「交付物是工程文件而不是成片」、字幕必须可改、以及 Blender 5.x 序列编辑器的几处坑：时间线有内容但编辑器一片空白、条被静默推到别的帧段、画布颜色与贴图色不一致、undo 历史只有一步。含实测 API 事实与通道重排脚本。"
agent_created: true
---

# 交付一个「客户自己能改」的 Blender 时间线

## 0. 什么时候该用这条路线

| 需求 | 该给什么 |
|---|---|
| 一次性成片，不需要再改 | 直接渲 MP4，别给工程 |
| 客户说「我要自己调字幕/位置/大小」 | **本 skill**：给 .blend + 原生文字条 |
| 客户要调色 | 给 .blend 的 ADJUSTMENT 条 |
| 客户不懂软件 | 还要给：桌面双击启动器 + 5 分钟操控卡 + 备份/还原按钮 |

⭐ **核心判断：客户的"可调"需求，不能用「我帮他改」满足。** 每次改动都走一轮沟通，成本远高于给他一个能拖的东西。

⛔ **不要把文字烤进 PNG。** 一旦烤进去，客户想改一个字就得回来找你重渲整条片。
正确做法：装饰元素导出**去掉文字**的"plain"版，文字单独用 TEXT 条。

---

## 1. 通道规划（先定表，再动手）

一个能维护的版面：

```
 1  bg            背景
 2  elem_plain    装饰（线/网点），已去掉烤进去的字
 3  lyric_l       竖排左列
 4  lyric_r       竖排右列
 5  char          角色
 6  fg            前景光斑（ADD）
 7  sub_text      底部字幕
 8  sub_acc       强调条
12  调色          ADJUSTMENT（必须在所有内容之上）
```

规则：
- **ADJUSTMENT 永远放最高通道**，否则上面的层不受调色影响。
- 同一个视觉元素拆多份（如两列竖排）就各占一条通道 —— **一条通道在同一帧只能有一个条**。
- 通道号留空位（1–8 然后跳 12），以后加层不用重排。

---

## 2. ⛔ 六个实测坑（每一个都让我返工过）

### 2.1 赋值 `channel` 会**静默挤走**同通道的条
```python
strips["lyric_l"].channel = 3   # char 本来也在 3
# -> char 被推到 89..177 帧，整段消失，没有任何报错
```
**修法：两段式重排。先把所有条推到高位空通道，再逐个落到目标通道。**

```python
FINAL = {"bg": 1, "elem": 2, "char": 3, "lyric_l": 4, ...}
for i, name in enumerate(FINAL):
    strips[name].channel = 20 + i      # 先全部搬到 20+
for name, ch in FINAL.items():
    strips[name].channel = ch          # 再落位
```
见 `scripts/relayout_channels.py`。

### 2.2 `color` 的维度按条类型不同
```python
text_strip.color  = (r, g, b, 1.0)     # 4 个分量
color_strip.color = (r, g, b)          # 3 个分量
```
写错会报 `sequences of dimension 0 should contain N items`，**但报错行号指向的是"另一个"颜色的赋值**，
容易看反（我被这个误导了两轮）。

### 2.3 `transform.offset_*` 单位就是像素，符号是 `kx=+1, ky=−1`
```python
# +offset_x 右移；+offset_y 上移（屏幕 y 变小）
```
⛔ **不要手写 `offset_y += dy` 去凑位置** —— 我第一次把两段字幕推到了 2310px，整段飞出画面。
用两点标定反解：

```python
def calibrate(strip, axis, target, bbox_fn):
    setattr(strip.transform, axis, 0.0);   b0 = bbox_fn()
    setattr(strip.transform, axis, 200.0); b1 = bbox_fn()
    setattr(strip.transform, axis, 0.0)
    k = (b1 - b0) / 200.0                  # 每单位 offset 造成的屏幕位移
    setattr(strip.transform, axis, (target - b0) / k)
```
实测 `kx = +1.000`、`ky = −1.000` —— 干净的一次函数，标定两次就够。

### 2.4 ⛔ 时间线有内容，编辑器却一片空白（Blender 5.0+）
Blender 5.0 起 Sequencer 与场景解绑，属性在 **`workspace.sequencer_scene`**（在 Workspace 上，不在 Area/Space 上）。

```python
for w in bpy.data.workspaces:
    if w.sequencer_scene is None:
        w.sequencer_scene = scene      # 不设置 ⇒ 编辑器空白，但渲染照常出图
```
⚠️ 这个坑极具欺骗性：**渲染完全正常**，只有人在界面里看是空的。

### 2.5 色彩管理会把已经调过色的素材二次调色
```python
sc.view_settings.view_transform = 'Standard'   # 默认 AgX
sc.view_settings.look = 'None'
```
不设的话，同一帧渲出来的 R 通道和源图差 20 左右（157 vs 178）。

### 2.6 文字条**不能**在画面里双击打字
只能在 `N` 侧栏的 `Text` 字段改。客户会问"我怎么改字"，**必须提前在操控卡里写清楚**，
或者另做一个弹窗输入工具。

---

## 3. 让工程扛得住"客户存坏了"

| 层 | 做法 |
|---|---|
| 自动 | `prefs.filepaths.save_version = 32`（**上限就是 32**，设 64 会被静默夹到 32） |
| 手动 | 桌面放「备份」按钮，一键把 .blend + 文档 + 生成脚本打成一个约 250KB 的 zip |
| 兜底 | 一份整包副本（含素材），客户整目录删了也能回拷 |

⛔ **写 userpref 的脚本里只要有一行报错，后面的 `save_userpref()` 就不执行。**
我第一次多写了一个不存在的属性，整个脚本中断、偏好没存，还以为是 API 不支持。
⇒ 改偏好的脚本**只做最少的事 + 存完复查一次**。

```python
p = bpy.context.preferences.filepaths
p.save_version = 32
bpy.ops.wm.save_userpref()
# 另起一个进程复查，别在同一次运行里假设成功
```

**还原脚本必须先把"当前版本"另存一份再覆盖** —— 这样连"还原"这个动作都能反悔。

---

## 4. 启动器：别从 agent 进程里开软件

```
@echo off
start "" "C:\path\to\blender.exe" "D:\project\file.blend"
```
- 用 `.cmd`（**CRLF 行尾**），不要用需要 COM 的 `.lnk` 创建（很多环境的安全策略会拦）。
- ⛔ 不要用 `printf '%s\r\n'` 之类拼路径 —— `\U`、`\b` 会被当转义序列吃掉，把 `C:\Users` 变成 `C:` + 退格。
  用 Python 的 `io.open(..., "wb")` 写字节。

---

## 5. 同色底"无接缝"合成（这条让竖图能直接放进横画布）

竖版角色图要放进 1920×1080 横画布，常规做法是抠图 —— **但如果素材底色是精确的纯色，可以不抠。**

```python
canvas[:, :] = BG            # 与素材底色完全相同的值
canvas[y0:y1, x0:x1] = resized_char_image     # 直接把整张图贴上去
canvas = canvas.astype(np.float32) * VIGNETTE  # ⭐ 暗角在贴完之后统一乘
```
**接缝之所以不存在，是因为两侧是同一条色带、同一个乘性函数。**

⛔ 两个必须同时成立的条件：
1. 素材底色与画布**逐通道相等**（差 1 都行，差 4 就能看出矩形）
2. 任何渐变/暗角必须**在贴图之后**对整幅施加，不能只施加到背景上

### 5.1 ⛔ 最容易踩的一步：BGR / RGB 顺序
`cv2.imread` 返回 **BGR**。如果你 `canvas[:, :] = (92, 27, 48)` 以为是 RGB，
画布就变成 `#301B5C`（深蓝紫），而素材是 `#5C1B30`（暗红）—— **画面里出现一个明显的矩形色块**。

⚠️ 而且底色偏色时**不要**用"把接近底色的像素替换成目标色"来修：
那会在轮廓外侧留一圈硬边（实测改动 75.93% 像素并产生边缘台阶）。
✅ 用**整体通道偏移**：`img + [Δb, Δg, Δr]`，对人物只动 1~2 个单位，肉眼不可辨，边缘连续性不变
（实测轮廓处逐像素跳变修改前后都是 7）。

---

## 6. 交付物清单

```
project.blend            工程本体
元素目录/                 各层 PNG 序列（保持相对或绝对路径别动）
操控卡.md                 ← 5 个键、4 件最可能想改的事、怎么撤销
备份说明.md               ← 三层备份与三种救法
桌面\启动工程.cmd
桌面\备份.cmd  /  还原.cmd
```

**操控卡只写 5 个键**：`空格` 播放、`方向键` 逐帧、`左键` 选中、`G` 移动、`S` 缩放。
**别写快捷键大全** —— 客户记不住，写了等于没写。

---

## 7. 素材路径的硬约束
`.blend` 里的图片条按**绝对路径**引用。
⇒ 交付文档里必须写死：**`bg/ char/ elem/ fg/` 这些目录不许改名、不许挪位置**，一改就是一片粉色。
