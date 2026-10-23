# Recon2Reason-Reasoning-4B on BW + vLLM：session005 单并发补测

本页记录已完成并独立核验的四个单并发负载原件。session004 封存报告及其补充审计保持原样；本页不声称官方验收或一次完整正式矩阵已经通过。

## 1. 简介

任务为 `BAAI/Recon2Reason-Reasoning-4B × BW 64GB × vLLM × BF16`。本轮复用上一批实际执行的 supervisor 和 SGLang 客户端 driver，单独补测 4096/16384 文本目标、输出 1024、并发 1 的两轮，共四个负载格。服务框架仍是 vLLM；SGLang 仅为压测客户端，不另计一个服务框架任务。

本模型既有七项功能原件和八格 c8/c64 原生性能文件均见 [session004 报告](report-004-recon2reason-bw-vllm.md)。[性能口径补充审计](session004-recon-performance-scope-audit.md)限定了附加正文检查与服务端 token 计数推断的适用范围。005 补测发生在另一个 Notebook/服务生命周期，不把两批原件改写为一次独立、完整的正式矩阵。

代码保存于 [GitHub 私有仓库](https://github.com/zhl-2022/guoxin-recon2reason-bw-vllm)。004 最终提交为 `0dfc02beb214e07f618fa0ac8c3ac8a0b2fec682`；005 的精确提交与远端回读另见交付回执。最终赛事表单由用户手动提交，本工程没有提交。

本轮四个原生客户端均退出0且被回收，32条测量回答全部非空、原报errors均为空；四份原始JSONL均保留。服务端完成数36、实际生成与请求上界总和均32896，与32个1024-token测量请求及四个32-token预热一致；这一结论有指标语义与请求闭集前提，不冒称保存了每请求raw SSE。控制器因原生JSON中的 `request_rate: Infinity` 序列化检查退出1，原始退出码保留；独立停止成功、两进程身份消失、30000端口关闭。

最终导出ZIP为223420B，SHA256 `bfd26699ad2ff8d53698ffd9d8813c6ca4a2df52776d9c755949aee86cfd05a8`，manifest SHA256 `ac8787321a5e448c6f2ba0b7f5da381571981bb790739a583edd44af09ae80ae`。91个entry、90份payload和44份源码前后seal均通过路径、大小、SHA256、CRC和安全解包回读；见[本地完整性核验](../evidence/session005/remote-recon-c1-final-001.local-verification.json)、[独立审计](../evidence/session005/remote-recon-c1-final-001-audit.json)及[逐格分析](../evidence/session005/recon-c1-final-001-analysis/analysis.json)。该包还保存当时共享Kimi目录的快照；Recon结论只使用自身运行身份。

## 2. 验证环境

本轮使用 SCNet 华中一区 A 区、资源组 `113 / hx1hgbwnormal` 的 B Notebook `2112237945233408001`：BW 64GB×1、CPU15核、内存59GB。UTC `2026-10-23T13:09:12` 重启，平台兜底关机为 UTC15:00（北京时间23:00、用户当地08:00）。这些时间是本轮平台记录，不能用 004 的已关机截图表示本轮终态。

账户镜像 ID `2071293281204580354`、version `2082674417745739777`、可选择标签 `jupyter-vllm018-ubuntu22.04-dtk26.04-qwen3.6-20260423`。完整实际 `registry/repo:tag` 与评审获取方式尚未闭合；不把公开基础镜像地址冒充实际 Jupyter 镜像。

| 字段 | 本轮实际配置或证据边界 |
|---|---|
| 服务解释器 | `/usr/bin/python` |
| 客户端解释器 | `/root/private_data/sglang-client-004c/bin/python`，已存在的隔离客户端环境 |
| 服务版本 | 原生 `vllm 0.18.1+das.fa71803.dtk2604`；Torch `2.10.0+das.opt1.dtk2604.20260325.g6b060a`、Transformers 5.5.0，隔离SGLang client 0.5.12 |
| checkpoint | `/root/private_data/SothisAI/model/Aihub/Recon2Reason-Reasoning-4B/main/Recon2Reason-Reasoning-4B` |
| 精度及并行 | BF16、TP=1、max-model-len=32768、gpu-memory-utilization=0.85 |
| 调度及输入限制 | enforce-eager、max-num-seqs=16、image=2/video=0；不另外开启 prefix cache |
| 服务地址 | 仅 `http://127.0.0.1:30000` |
| 独立运行身份 | `c78f8f7f9b24488a9d0d529a5ad28f0f` |
| 并行活动 | Kimi checkpoint下载、哈希校验及部分CPU预检共用B的CPU/网络/存储；后续Kimi GPU独立在A运行。Recon不是隔离的正式性能环境 |

## 3. 适配优化方案

本轮不新增模型 attention、权重或采样补丁。复用的 [supervisor](../scripts/recon2reason_runtime.py) SHA256 为 `0edc33da22c07a804c93047f918a4a39a58af90997390c49695d8b39a891d85b`；[客户端 driver](../scripts/t02_sglang_bench.py) SHA256 为 `ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000`。这两份文件与已执行的 004 原件封存字节一致。

新增 [005 控制器](../scripts/session005_recon_c1.py)把固定 run ID、项目目录、端口、冻结源码、两轮负载、总时限及清理绑定。客户端退出后，无论是否因 `Infinity` JSON 序列化而报非零，均先保存服务完整 `/metrics`，再按本次 run ID 停服，并独立检查两个 PID/start token 和端口。原生结果保留不修改，序列化问题与模型请求错误分别记录。

最小执行包仅有七个 payload，不安装依赖、不包含权重；[封包与 CPU 检查](../evidence/session005/recon-c1-preparation/validation.json)核对真实 canonical dry-run、UUID、原 004 源码 SHA、路径/CRC、安装后回读和拒绝覆盖，Windows 5/5、WSL 5/5。CPU 检查不当作 GPU 或官方评测成绩。

## 4. 启动与停止

本轮专用项目为 `/root/private_data/guoxin-hackathon-20261023-session005-recon-c1`。安装包先逐文件验证，运行前确认 Trident 30119 和 Recon 30000 均关闭。首次 shell 启动因重定向日志目录尚未存在而未执行模型程序；随后显式创建目录再启动，保留该事实，不把第一次命令尝试写为实际运行。

```bash
mkdir -p /root/private_data/guoxin-hackathon-20261023-session005-recon-c1/evidence/session005
timeout -s TERM -k 65s 2400s /usr/bin/python -B \
  /root/private_data/guoxin-hackathon-20261023-session005-recon-c1/scripts/session005_recon_c1.py
```

服务于 UTC `13:50:59.860296` 进入 ready，server PID `2095`。控制器从UTC `13:48:55`运行至 `14:21:05.528824`，wall=1930.166226秒，bench子进程wall=1793.707368秒、退出1且未超时/已回收。退出后的完整metrics已保存；run ID绑定的停止命令退出0，独立清理确认supervisor/server原进程token均不存在、30000关闭、最终state为stopped。七份冻结源码前后及直接export seal一致。服务最长2400秒，控制器内部阶段预算2200秒，每格客户端600秒；平台15:00兜底不延长。原生四个client各自退出0，不能把外层序列化退出1改写为请求失败，也不删除该退出码。

## 5. Smoke 测试

本次控制器只补性能负载，没有伪造新的七项功能 smoke。既有真实 health/models/单图/多图/多轮/流式七项结果来自 004 独立功能服务，见 [004 报告第5节](report-004-recon2reason-bw-vllm.md)。这些结果证明 API 和功能链路；不能当空间推理精度。

根标准入口继续保留真实 `env_check.sh / run.sh / stop.sh / smoke.sh / verify.sh / bench.sh / summarize.sh` 和透明 `verify.py`；缺少官方脚本时不生成假 PASS。

## 6. 精度测评

正式精度未执行。已核的最新赛事说明和模板给出通用任务、阈值及交付格式，但还未取得与 Recon 分题准确绑定的固定数据/reference、原版 evaluator/selfcheck、GPU baseline 和答案/坐标解析与容差契约。用户已确认尚未收到另行下发材料；目前不再重复询问。

取得材料后应保存文件 SHA、入口参数、自检原文、逐样本预测及正式 `verify_result.json`。合成图 smoke、发布方模型卡分数、随机压测和服务正常返回都不能替代这些记录。`official_accuracy_verified=false`、`submission_ready=false`。

## 7. 性能参考

本轮实际为四格，每格八个测量请求和一个32-token预热，共32个测量请求、四个预热。四份native原件各报completed=8、output_lens全部1024、total_output_tokens=8192；32条正文均非空，errors均为空，TTFT均为正，均有ITL样本。producer把四格标为 `invalid_native_result` 的原因仅为JSON顶层 `request_rate: Infinity`；新分析器只在内存中处理该非有限字段，不修改原始JSONL。

| 文本目标 | 并发 | 轮次 | 完成请求 | duration(s) | 输出token/s | mean TTFT(ms) | mean TPOT(ms) |
|---|---|---|---|---|---|---|---|
| 4096 | 1 | 1 | 8 | 376.052524 | 21.784191 | 770.549060 | 45.194768 |
| 4096 | 1 | 2 | 8 | 378.532021 | 21.641498 | 718.281399 | 45.548848 |
| 16384 | 1 | 1 | 8 | 426.228877 | 19.219721 | 6530.274097 | 45.695277 |
| 16384 | 1 | 2 | 8 | 425.842751 | 19.237148 | 6590.166043 | 45.589902 |

输入采用固定 seed 的一张1024×1024随机 JPEG，4096/16384是随机文本目标；图像、tokenization差异及chat包装额外计入，尚未认证为模板总输入长度。原生第二轮4K的input_lens为4324–4377，16K为17222–17385。请求体为 `temperature=0 / ignore_eos=true / include_usage=true`，SGLang backend `sglang-oai-chat` 指向 vLLM 服务。第二轮作为取数轮；先后两轮不等于独立冷启动。

原生 `output_lens` 可能来自实际 usage，也可能保留请求长度fallback。独立审计读取了运行前后完整服务metrics：所选counter运行前全部为0，没有用缺项补0；delta success=36且全部finish_reason=length，其它reason=0；`generation_tokens_total`、`request_generation_tokens_sum`、`request_params_max_tokens_sum`均为32896，两个histogram的count均36，bucket也一致。最终server.log恰有36个chat POST且全部HTTP200，完成后无running/waiting。计数为 `32×1024+4×32=32896`。

在DAS fork保持已核上游同一finished-request集合及每请求生成量不超过其max_tokens语义、归档请求清单完整的前提下，实际生成和请求上界的非负差总和为0，可推各请求均达到各自上限。这是服务端配对计数推断，仍不是逐请求raw usage/SSE/token IDs的直接保存；native DAS指标实现源码未额外封存。正文非空是单独开发检查，不提升为模板新增门槛。

每请求ITL数组只有62–122个样本，不是1023个逐token间隔；TTFT/TPOT/ITL均按原SGLang客户端定义报告，不能把客户端接收chunk时间冒称每个生成token的真实时序。正式性能验收状态仍为false。

## 8. 注意事项

- 004 八格与005四格属于不同 Notebook、时间和服务身份；可以说明跨批次覆盖位置，不能拼成一份同环境正式12格矩阵。
- 004 十二条空正文及其零 TTFT/空 ITL 原件保持不变；[补充审计](session004-recon-performance-scope-audit.md)解释其负载与延迟意义，不删样本、不造 SSE。
- 本轮与 Kimi CPU 下载共跑，吞吐结果有这一环境条件；未取得正式 baseline，不声称性能提升比例。
- 原生 GELU 等框架告警继续以日志披露，正式正确性须由固定集判断。
- 保留版权范围说明与上游许可；模板没有要求另选全仓开源许可证，不增加该门槛。
- 评审镜像获取方式、私有仓库访问和正式材料仍缺，最终赛事表单由用户手动提交。
