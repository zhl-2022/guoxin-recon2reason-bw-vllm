# 云文档与光合仓库访问核对

日期：2026-10-20（Asia/Shanghai）。本记录区分当前访问尝试、既有页面证据和仍需主代理完成的检查，不能当作“云文档已刷新且无新附件”的结论。

## 1. 当前浏览器访问情况

子代理先按 CUA 要求执行 `rewriteDocumentation()`，随后尝试读取既有 tab1 / browser2，返回 `Browser is not available: 2`；`cua.listBrowsers()` 返回 `[]`。因此本子代理没有完成实时云文档刷新、光合账号/namespace 或新建项目表单的读取。

**这只是子代理缺少可用浏览器表面，不能据此说用户退出登录、光合不可访问或云文档没有新材料。**已将限制告知持有实际浏览器会话的主代理，由其只读检查 tab1 和 tab4；本子代理没有触碰 SCNet tab6 或 Jupyter tab14。

## 2. 已有可复查的文档入口

以下来自此前保存的 `evidence/official-materials/20261019/cloud-sections.json` 页面 UI 快照，属于历史证据，不是本次刷新结果：

- [赛事云文档](https://bvjoh3z2qoz.feishu.cn/wiki/OkLBws6uWiG1Q0kpHLKcxXLmnif)。
- [脚本模板锚点](https://bvjoh3z2qoz.feishu.cn/wiki/OkLBws6uWiG1Q0kpHLKcxXLmnif#UJB3d40PnolR0kxm32PcJ6AUnnh)。
- [分题材料（评测 / 基线）锚点](https://bvjoh3z2qoz.feishu.cn/wiki/OkLBws6uWiG1Q0kpHLKcxXLmnif#HQZOdkz3SoSSktx9hFwcDmHUn7b)。
- 历史 UI 显示附件 `国芯国模黑客松-技术报告模板.md`；已实际下载并保存在 `evidence/official-materials/20261019/report-template.md`。

需要主代理实时核对：页面最新修改时间、上述章节是否出现新增文件/独立链接，以及 Recon、RoboBrain、ASR 各题的实际评测包入口。不能把章节标题本身当成已取得文件。

## 3. 光合仓库能力与账号权限

本轮公开 HTTP 核查中，光合实例自身的[项目帮助](https://developer.sourcefind.cn/codes/help/user/project/index.md)和 [Projects API 帮助](https://developer.sourcefind.cn/codes/help/api/projects.md)均 HTTP 200，明确支持 private/internal/public；private 项目访问须逐用户授权。原文见第二轮材料目录。

主代理随后转述其直接 UI 核实结果：tab4 起初为匿名状态，点击 Sign in 后进入光合独立登录；SCNet SSO 入口曾转到账号绑定。主代理改用用户再次明确授权的独立账号登录成功，现位于安全的 `/codes/-/profile` 页面，namespace 为 `ghu_30ebea88e`，User ID 为 `25562`，页面提示 `Please complete your profile with email address`。这些是**主代理转述的实际 UI 观察，不是本子代理直接观察**；本记录不保存登录凭据、手机号或票据 URL。

主代理已看到 `New...` 项目入口，尚未尝试创建或完成 New Project 表单验证；不能断言无权限，也不能仅凭入口可见就认定创建已成功。云文档仍待主代理刷新。SCNet 登录、GitHub `zhl-2022` 身份与光合 namespace 不能相互推导。GitLab Draft 指合并请求状态，不是仓库私有性；若后续创建准备仓库，应确认实际 visibility，而不是只在项目名写 Draft。

当前后续检查是新建项目页的 visibility 选项、创建权限及 profile 邮箱提示是否实际阻断。应按用户授权继续处理，不能编造邮箱或把提示预先当成必然阻碍。本访问记录本身没有创建项目、接受条款或发送消息。

## 4. 同步准备的 GPU 数值复验脚本

[validate_robobrain_vision_math_compat.py](../scripts/validate_robobrain_vision_math_compat.py) 已新增与当前 CPU 修正一致的 head/batch 广播几何：float32/BF16，heads 1/4/4、1/1/4、4/1/1，batch 1/2/1，Vdim40。每次实际 SDPA 分块检查 3752 元素 score 预算，预期每个 case 为五块 7 query 加最后 2 query。

该脚本预期 GPU 数值 case 数由 18 增为 24。新 validator SHA256 为 `ba6a94283fa63418948c466eac7fc8949a56cf244eb6f9c3be8dcd78ef673dd1`；Python 编译和 `--help` 检查通过。还提取新增源码块在真实 CPU Torch 中执行，六个广播数值 case、36 个实际 SDPA 分块全部通过；只将分配设备替换为 CPU，没有运行 GPU，不能当作 GPU 验证。核心兼容源码仍为 `083dc53f3e4f8171b774469bffa724c2269a9d289769f56a9d7a5624cd81659f`，未修改。

结构化访问记录见 [cloud-materials-and-repository-access-20261020.json](../evidence/cloud-materials-and-repository-access-20261020.json)。本轮没有远端写操作。
