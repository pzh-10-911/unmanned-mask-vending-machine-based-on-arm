# GitHub 网页端使用指南

给第一次用的队友。**全程在网页上操作，不需要安装任何东西。**

---

## 1. 注册账号

打开 https://github.com/signup

- 输入邮箱
- 设密码（至少 8 位，英文 + 数字）
- 起个用户名（比如 `zhangsan`）
- 验证邮箱

注册完后把**用户名**告诉组长。

---

## 2. 加入仓库

组长添加你为协作者后，你会收到 GitHub 发来的邮件。

**确认加入：**

方法一：点邮件里的 **View invitation** → **Accept invitation**

方法二：直接打开这个链接
```
https://github.com/pzh-10-911/unmanned-mask-vending-machine-based-on-arm/invitations
```
点绿色的 **Accept invitation**

---

## 3. 认识仓库页面

打开仓库地址：
```
https://github.com/pzh-10-911/unmanned-mask-vending-machine-based-on-arm
```

顶部导航栏：

```
[<> Code]  [Issues]  [Pull requests]  [Projects]  [Wiki]
```

| 菜单 | 用途 |
|------|------|
| **Code** | 文件列表，看代码和文档 |
| **Issues** | 任务列表，看谁负责什么 |
| **Projects** | 看板，看任务进度 |
| **Pull requests** | 合并代码（本项目暂时不需要） |

文件目录说明：

```
📁 仓库根目录
├── README.md                ← 项目说明
├── app.py                   ← Flask 主程序（Person C 负责）
├── config.py                ← 配置
├── docs/                    ← 文档（所有人看这里）
│   ├── A-硬件驱动.md        ← Person A 的分工
│   ├── A-硬件驱动-测试.md   ← Person A 的测试
│   ├── B-状态机与库存.md    ← Person B 的分工
│   ├── B-状态机与库存-测试.md
│   ├── C-Flask-API集成.md   ← Person C 的分工
│   ├── C-Flask-API集成-测试.md
│   ├── D-前端页面.md        ← Person D 的分工
│   ├── D-前端页面-测试.md
│   ├── Git提交指南.md       ← 本文
│   └── design.md            ← 完整设计文档
├── hardware/                ← Person A 放代码的地方
│   ├── gpio_init.py
│   ├── led.py
│   ├── ir_sensor.py
│   └── button.py
├── logic/                   ← Person B 放代码的地方
│   ├── state_machine.py
│   └── inventory.py
└── static/                  ← Person D 放代码的地方
    ├── index.html
    ├── style.css
    └── script.js
```

**找到自己的分工文档：**

点进 `docs/` 文件夹 → 找到你的角色对应的文件（A/B/C/D），点开看要求。

---

## 4. 看自己的任务（Issues）

点顶部导航栏的 **Issues**。

会看到 4 个任务卡片：

```
Issues
├── 📌 Person A — 硬件驱动与接线     
├── 📌 Person B — 状态机与库存
├── 📌 Person C — Flask API 集成
├── 📌 Person D — 前端页面
```

**点你自己的那个 Issue：**

你会看到：

```
┌──────────────────────────────────────────┐
│ Person A — 硬件驱动与接线                │
│ #1                                       │
│                                          │
│ 【任务目标】                             │
│ 完成树莓派 GPIO 硬件接线和驱动模块开发。 │
│                                          │
│ 【产出文件】                             │
│ - hardware/gpio_init.py                  │
│ - hardware/led.py                        │
│ ...                                      │
│                                          │
│ 左侧: Assignees                          │
│ 你的头像 ← 说明这个任务分给你了          │
│                                          │
│ 右侧: Labels                             │
│ hardware ← 标签                          │
│                                          │
│ 底部: 评论区                             │
│ ┌──────────────────────────────────┐     │
│ │ 写你的进度、问题、完成报告...    │     │
│ │                                  │     │
│ │ [Comment]  (点此提交评论)        │     │
│ └──────────────────────────────────┘     │
└──────────────────────────────────────────┘
```

**在 Issue 里能做什么：**

| 操作 | 怎么用 |
|------|--------|
| 报进度 | 在底部评论框写 "已完成 LED 驱动，开始写红外" → 点 Comment |
| 提问 | 写 "按键中断不会写，有人会吗" → @ 队友用户名 |
| 报告完成 | 写 "所有功能已完成，测试通过" → 点 Close issue |
| @ 人 | 输入 `@` 再选队友，对方会收到通知 |
| 贴图 | 拖截图到评论框，直接贴上去 |

---

## 5. 关于分支

仓库默认只有一个分支 `main`，所有文件都在这上面。

分支相当于**每个人的独立工作区**，互不影响。但是本项目直接用 `main` 分支即可，网页端添加文件时选 **Commit directly to main branch**。

**如果你想在自己的分支上开发：**

上传文件或编辑文件时，在 Commit 页面底部选 **Create a new branch**，输入分支名（比如 `person-a-hardware`）。

```
○ Commit directly to main branch       ← 直接提交到主分支（推荐）
○ Create a new branch for this commit  ← 自己建一个分支
  Start new branch name: person-a-hardware
```

切换分支：仓库首页左上角有个写着 `main` 的下拉菜单，点它可以看到所有分支，点击切换。

**分支合并：** 你的代码完成测试后，点 **Pull requests** → **New pull request**，选择你的分支 → `main`，点 **Create pull request** → **Merge pull request**。

> 本项目简单，**所有人直接提交到 main 即可**，可以不建分支。

## 6. 上传你的代码文件

**场景：** 你按分工文档写完代码了，要提交到仓库。

**步骤：**

1. 打开仓库首页
2. 点进你负责的文件夹（A→ `hardware/`，B→ `logic/`，C→ 根目录，D→ `static/`）
3. 点右上角的 **Add file** 按钮 → **Upload files**

```
           ┌──────────────┐
           │  Add file ▼  │
           │  Create new  │
           │  Upload files│ ← 点这个
           └──────────────┘
```

4. 从电脑里选中你的代码文件，**拖到网页中间的框里**
5. 往下翻，写 Commit message

```
Commit message
┌──────────────────────────────────┐
│ 完成全部硬件驱动模块             │  ← 写清楚你做了啥
├──────────────────────────────────┤
│ Add a description...             │  ← 可以空着不写
├──────────────────────────────────┤
│ ● Commit directly to main       │  ← 选这个（默认）
│ ○ Create a new branch           │
├──────────────────────────────────┤
│         [Commit changes]         │  ← 点这个提交
└──────────────────────────────────┘
```

6. 点绿色的 **Commit changes**

✅ 上传完成。文件已经存到仓库里了。

---

## 6. 修改已有文件

**场景：** 发现之前代码有 bug 要改。

1. 点开要改的文件
2. 点右上角的 ✏️ 图标（Edit this file）

```
led.py
┌────────────────────────────────────────────┐
│  ⋮  │  ✏️  │  🗑️  │                        │
│     │ 编辑  │ 删除 │                        │
└────────────────────────────────────────────┘
```

3. 网页上直接编辑内容
4. 下面写 Commit message（比如 "修复 LED 闪烁问题"）
5. 点 **Commit changes**

---

## 7. 删除文件

1. 点开要删的文件
2. 点右上角 🗑️ 图标
3. 下面写原因（比如 "这个文件不需要了"）
4. 点 **Commit changes**

**注意：不要删别人的文件。**

---

## 8. 查看进度（Projects 看板）

点顶部导航栏的 **Projects**。

可以看到看板：

```
┌───── To Do ─────┬─── In Progress ───┬─────── Done ───────┐
│                  │                   │                   │
│ Person B 状态机  │ Person A 硬件驱动 │                   │
│ Person C API     │                   │                   │
│ Person D 前端    │                   │                   │
│                  │                   │                   │
└──────────────────┴───────────────────┴───────────────────┘
```

- **To Do** — 待做
- **In Progress** — 正在做（组长帮你拖过去）
- **Done** — 已完成

---

## 9. 注意事项

| 事项 | 说明 |
|------|------|
| **只动自己的文件** | A 不要改 B 的代码，B 不要改 D 的页面 |
| **提交说明写清楚** | 写 "完成 LED 驱动" 而不是 "修改" 或 "123" |
| **一次传完** | 所有文件写好了再一起传，不要写一半就传 |
| **不懂就 Issue 里问** | 评论区 @ 组长或队友 |

---

## 一句话总结

```
登录 → Issues 看任务 → docs/ 看分工要求 → 写代码
→ 点 Add file 上传 → 写说明 → Commit（选 main 分支）
→ Issue 评论区报完成
```

有问题直接在 Issue 评论区问。
