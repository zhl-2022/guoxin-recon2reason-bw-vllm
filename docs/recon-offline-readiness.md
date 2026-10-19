# Recon2Reason 离线交付与外部正式材料执行桥

更新日期：2026-10-20（Asia/Shanghai）。本轮只完成 CPU 可验证的工程工作，没有启动模型、检查 GPU、访问算力平台或提交赛事。

## 已完成的入口

Recon 的 `tasks/recon2reason-bw-vllm/run.sh` 为唯一服务入口，默认参数已对齐历史成功命令：BF16、TP1、eager、maxseq4、image2/video0。专属 `RECON2REASON_*` 覆盖避免与 ASR/RoboBrain 混用环境。该次本地整理并不替代后续干净环境真实复跑。

共享 `scripts/recon2reason_runtime.py` 的 `verify/bench` 已改成外部材料执行桥，保留原版脚本和 baseline；不再要求未知官方 baseline 迁就本地假设的 `model/metrics` schema。

| 入口 | 不开卡行为 | 未来实际执行行为 |
|---|---|---|
| `run.sh --dry-run` | 只展开服务参数 | 不启动服务 |
| `verify.sh --dry-run` | 检查脚本、baseline、非空数据目录；列缺项和命令，不查健康、不写文件 | 不执行自检或正式脚本 |
| `verify.sh` | 本轮不运行 | 健康检查后保存原始材料和旧结果，先自检，成功后执行外部评测，分别保留日志与新输出 |
| `bench.sh --dry-run` | 给出六档两轮计划、各档请求数、图像规格缺项，不查健康、不写文件 | 不压测 |
| `bench.sh` | 本轮不运行 | 执行外部 benchmark，保留原版脚本、日志、旧结果和新输出；不自行计算成绩 |

verify 的 baseline、数据为必需输入；bench 只强制需要外部脚本，baseline/data 若提供则检查。原版官方脚本仍负责自己的数据和参数校验。镜像地址、正式指标和数据尚未完整取得；这项桥接改动不会把任务改成已验收。

## 输入参数与保全

Recon 专属环境变量映射到共享桥的同名通用变量；其他视觉任务继续通过原有 `verify.sh/bench.sh` 接入共享桥。ASR 的独立正式入口仍按它自己的 T04 实现，不套用本文的 T02 六档计划。

| Recon 覆盖变量 | 用途 |
|---|---|
| `RECON2REASON_OFFICIAL_VERIFY_SCRIPT` / `...BENCH_SCRIPT` | 原版外部脚本，Python 用当前解释器，其他脚本用 Bash |
| `RECON2REASON_OFFICIAL_BASELINE` / `...DATA_DIR` | 原始参考文件、固定数据目录；不改写，不假造 |
| `RECON2REASON_OFFICIAL_VERIFY_ARGS_JSON` / `...BENCH_ARGS_JSON` | 正式阶段参数字符串数组，默认 `[]` |
| `RECON2REASON_OFFICIAL_SELFCHECK_ARGS_JSON` | 自检参数数组，默认 `["--selfcheck"]`；与正式阶段分开记录 |
| `RECON2REASON_OFFICIAL_SELFCHECK_TIMEOUT_SECONDS` | 默认 120 秒 |
| `RECON2REASON_OFFICIAL_TIMEOUT_SECONDS` | 默认 7200 秒；服务生命周期也须单独覆盖到足够长 |
| `RECON2REASON_OFFICIAL_VERIFY_OUTPUTS_JSON` / `...BENCH_OUTPUTS_JSON` | 真实产物的相对路径数组；不允许路径逃逸、替换输入文件或目录 |

路径和参数均作为结构化 argv 传递，不经 shell eval。桥把 `OFFICIAL_BASELINE/BASELINE_PATH`、`OFFICIAL_DATA_DIR/DATA_DIR` 同时传给外部脚本，正式脚本是否读取这些变量需要按真实接口核对；必要 CLI 参数由显式 JSON 数组提供，不能改官方源码适配桥。

实际执行的独立目录为 `runtime/official-verify-<id>/` 或 `official-bench-<id>/`，包括：

- `record.json`：调用身份、参数、时限、步骤退出码和状态；不采集全环境或凭据。
- `materials/`：原版脚本与 baseline 副本、SHA-256；执行前后检查内容没有漂移。数据目录原样提供，当前不对整套大数据内容做哈希认证。
- `previous-outputs/`：执行前已有产物，保留原始内容与时间信息；自检失败不进入正式阶段。
- `selfcheck.log`、`evaluation.log` 或 `benchmark.log`：完整 stdout/stderr，分别记录 SHA-256。
- `outputs/`：本轮新文件快照与哈希；缺失、空文件、旧产物未重建均拒绝计为执行完成。

自检超时、非零退出或材料漂移时，不执行正式步骤。Linux 按新进程组运行外部脚本，超时与脚本退出后清理残留子进程。Windows 仅适合本地轻量 mock；实际进程组行为已在 WSL 单独验证。

## 结果的含义

外部脚本退出 0、新产物存在，不代表已经达到赛事精度或性能门槛。未知正式结果仅标记 `executed_uninterpreted`、`official_acceptance=false`；桥返回 0 表示本轮执行与证据保全完成。必须接入实际分题的判分契约后才能作验收结论。

若结果 JSON 明确提供模板身份字段 `MODEL_ID/CARD/FRAMEWORK/PRECISION` 且不匹配，桥记录 `identity_mismatch` 并失败。若明确 `passed=false`，记录 `reported_failure`。这只是阻止显然矛盾的结果，不构成完整未知 schema 判分器，也不从任意 `passed=true` 推导正式 PASS。

## T02 纯计划

模板六个负载每档连续跑两轮，第二轮计分；每个请求一张图片，正式图像规格待确认。

| 输入 token | 输出 token | 并发 | 每轮请求数 | 两轮请求数 |
|---|---|---|---|---|
| 4096 | 1024 | 1 | 8 | 16 |
| 4096 | 1024 | 8 | 16 | 32 |
| 4096 | 1024 | 64 | 128 | 256 |
| 16384 | 1024 | 1 | 8 | 16 |
| 16384 | 1024 | 8 | 16 | 32 |
| 16384 | 1024 | 64 | 128 | 256 |
| 合计 | | | 304 | 608 |

该计划不包含测量值、生成的 baseline 或假日志，不是压测客户端。图片规格、实际请求参数、结果解析和负载完成状态需由真实分题方法确定。

## CPU 验证

`tests/test_official_bridge.py` 使用临时目录与临时 mock 脚本，测试自检顺序、失败阻断、脚本/baseline 漂移、超时及进程组清理、旧产物不能充当新结果、错误身份、明确失败、未知 schema 不变 PASS、CLI dry-run 无副作用、参数记录和六档 608 请求计划。mock 数据只在临时目录生成，不属于任何正式 baseline 或评测结果。

本轮实际结果：WSL 的 15 项桥接测试全部通过；Windows 同样运行 15 项，其中 14 项通过、Linux 进程组专项按平台跳过。Recon 的 4 项 Linux 入口回归与 7 个 Shell 语法检查也通过，任务本地 `runtime/` 未创建。一次 Windows 100 毫秒超时测试赶在冷启动打印前结束，已将测试限时改为 1 秒后复测通过；这不改变正式执行的超时实现。

```bash
python3 -B -m unittest discover -s tests -p test_official_bridge.py -v
python3 -B -m unittest discover -s tests -p test_recon_task_entry.py -v
```

正式评测仍需取得：Recon 的适用指标、固定数据与样本版本、GPU baseline/参考输出、原版判分器及自检、解码/思考/预处理、性能图片要求。完整镜像、真实精度性能和干净环境复跑也仍待完成；CPU 测试通过不消除这些差距。
