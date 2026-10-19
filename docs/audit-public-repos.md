# 公开仓库与评测材料核查

核对时间：北京时间 2026-10-19 晚至 2026-10-20 凌晨；证据文件沿用 `20261019` 名称。范围为光合 ModelZoo、光合公开项目检索、模型发布方仓库和 HYGON-AI 官方框架仓库。本轮只读取和下载文本、源码；没有开卡、执行下载的代码、修改远端、发消息或提交成果。赛事云文档附件、赛题板和提交表由主核查记录汇总，本文不代替其结论。

## 1. 核查结果与边界

已经成功读取 [ModelZoo](https://developer.sourcefind.cn/codes/modelzoo) 的真实项目列表、候选项目目录和源码，不能把结果概括成“网站打不开”。[匿名 GitLab API](https://developer.sourcefind.cn/codes/api/v4/groups/831/projects?include_subgroups=true&per_page=100&page=1) 分 7 页列出了 626 个公开项目。精确读取了 Qwen3-ASR、旧 RoboBrain、Kimi-VL 两个变体及社区通用模板。[光合代码根入口](https://developer.sourcefind.cn/codes) 在匿名 HTTP 下返回 SSO 页面，但 ModelZoo 和公开 GitLab API 可用。

本轮没有从所列公开入口取得六个候选题的赛事专用 baseline、固定子集和正式判分包。这个结论只限定于已经检查的入口，不能推出主办方未发布，也不能把公开推理例程、模型发布方成绩表或框架开发测试冒充赛事验收材料。

特别需要注意：Qwen3-ASR-1.7B 的 BW/K100AI 原生 vLLM 适配在社区已公开。**已有公开适配不证明它已在本赛事提交或验收，也不证明首件奖励已被占用。**计奖状态仍应以赛事记录和规则为准。

## 2. 六个候选题逐项结果

| 候选模型 | 取得的公开材料 | 没有在所检入口取得的材料 |
|---|---|---|
| Recon2Reason-Reasoning-4B | BAAI 模型卡、文件清单、`verify_release.py`；公开模型卡指定 BF16、PyTorch 2.8.0、Transformers 4.57.1、SDPA、greedy | 赛事对应 T02 类型、具体数据集/子集题号/数量、GPU 数字基线、答案解析和判分脚本、固定解码参数、压测图片分辨率 |
| RoboBrain2.5-8B-NV | FlagOpen/RoboBrain2.5 推理源码及 general/grounding/pointing/trajectory 等任务例程；24 项完整树清单 | 该版本赛事图集、参考动作/坐标输出、解析器、精度基线、对应场景的验收类型与固定参数 |
| Qwen3-ASR-1.7B | ModelZoo 已有精确模型的 vLLM 部署、初始化顺序修复和示例；Qwen 发布方评测参数/结果表；HYGON SGLang 的开发用 ASR WER 压测脚本 | 赛事 T04 具体数据集版本/split/样本清单、官方参考转写、中文规范化/CER 与英文 WER 算法、GPU 基线、正式音频压测负载和 RTF 口径 |
| Qwen3-ForcedAligner-0.6B | Qwen 推理例程、模型文件清单、AAS 结果表；HYGON vLLM pooling 启动配方 | 完整服务请求与时间 bin 后处理的验证、赛事强制对齐样本及标注、AAS 算法/聚合与门槛、官方基线、性能负载 |
| MiMo-V2.6-Distill-Qwen-9B | XiaomiMiMo 精确模型卡、权重/配置文件清单、SGLang 启动方式、公开/内部 agent 基准成绩表 | 赛事 T01 指定数据、baseline JSON、greedy/思考开关/max_tokens、判分脚本；发布方 agent 表不能代替赛事指定文本评测 |
| Kimi-VL-A3B | MoonshotAI/Kimi-VL 官方源码；光合 Instruct/Thinking 两个社区项目及 Transformers 图片示例 | 精确变体是否按同一件计、赛事 T02 数据和 GPU 基线、固定思考设置、OCR/MMMU 对应判分和图像负载 |

### 2.1 Recon2Reason

- [BAAI 精确模型卡](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B)。当前模型修订 `f8faf41a1d5fe392f2d1ee31884f79398da59c99`，公开文件清单含 `SHA256SUMS`、`verify_release.py` 及标准模型文件，没有赛事 `baselines/`、`data/`。
- [`verify_release.py` 固定修订](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/verify_release.py) 已实际下载阅读。它检查参数量与特殊 token，可选白图单 token 生成；没有数据集精度计算。
- ModelZoo 全组项目名和光合全站公开项目搜索中没有精确名称命中；这不是全站源码内容搜索，也不是未发布证明。

### 2.2 RoboBrain

- [FlagOpen/RoboBrain2.5](https://github.com/FlagOpen/RoboBrain2.5/tree/af98c932aac9ff715d70da177088d7bb95573ff7) 已读取完整未截断的 24 项目录；仓库提供推理示例，没有独立 `eval/`、`baseline/` 或赛事数据目录。README 指向 FlagEvalMM 等上游项目，但没有在此指定赛事的固定配置。
- [光合 RoboBrain 项目](https://developer.sourcefind.cn/codes/modelzoo/robobrain_pytorch) 的固定提交为 `5a0bc33e6c7657f8083fbbcc437ceeef38ef4b78`（2025-06-27 16:21:42 +08:00）。实际 README 加载的是 **`BAAI/RoboBrain`、Qwen2.5、vLLM 0.8.5、K100AI 两卡**，不是本轮 2.5-8B-NV。其数据集写“无”，精度没有数值表；不能套作本题基线。
- HF 的 RoboBrain 模型卡 HTML 可读；直接 raw 文件下载返回 401。本轮没有接受访问条款或尝试绕过限制，推理源码由发布方公开 GitHub 取得。

### 2.3 Qwen3-ASR

- [光合精确项目](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch)，GitLab 项目 ID `2144`。当前最新提交 `baae2d0d52e4d4aac2476d0960bb62f0d0076609`，提交时间 **2026-07-16 17:49:47 +08:00**，早于本轮开发。
- [固定 README](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch/-/blob/baae2d0d52e4d4aac2476d0960bb62f0d0076609/README.md) 指定 DTK 26.04、Python 3.10.12、Torch 2.10.0 DAS、Transformers 5.5.0、vLLM 0.18.1 DAS，BF16、BW1000/K100AI 单卡，并给出 `vllm serve` 与 `/v1/audio/transcriptions` 示例。
- [初始化顺序修复脚本](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch/-/blob/baae2d0d52e4d4aac2476d0960bb62f0d0076609/fix_qwen3asr_vllm_init_order.sh) 已按固定提交下载，未执行。其修复将 `thinker_config` 赋值放到 `super().__init__` 之前，和本轮遇到的问题属于同一类。
- 完整目录只有 12 项：演示音频/图片、README/原 README、修复脚本、`inference.py`、依赖、许可和元数据。没有赛事要求的 `verify.py`、`bench.sh`、官方 `data/`、`baselines/`。README 数据集写“暂无”；“精度一致”是一句说明，没有可复算数值与样本清单。
- [Qwen 官方仓库固定修订](https://github.com/QwenLM/Qwen3-ASR/tree/7c6daf77a2421100f5fb066495372c00129d39ff) 的完整目录为 46 项，没有独立评测脚本目录；README 提供 BF16/vLLM/greedy/1024 token/不强制语言的评测参数及公开基准结果。这些是发布方基准信息，不是赛事固定子集。

### 2.4 ForcedAligner

- [Qwen 官方示例](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_forced_aligner.py) 提供输入音频和参考文本的对齐用法。
- [HYGON 官方 vLLM 配方](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/vllm/qwen3-forcedaligner.md) 已实际读取，包含 0.21/0.28.1、BW1100 单卡、pooling/token-classification 配置。它明确写明：只完成服务启动；对齐请求格式、time-bin 后处理、时间戳精度仍待验证。因此不能据此认为已存在完整可交付题解，也不能当作当前 0.18.1 已支持的证据。

### 2.5 MiMo 9B 与 Kimi-VL

- [MiMo 精确模型卡](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B) 修订 `2367e865d009c13ac81713a2878291d33ab28177`。模型文件清单没有赛事数据或评测脚本；卡片列 agent 评测成绩，部分为内部集，不应代替赛事 T01 baseline。不要与 MiMo-VL-7B 或 MiMo-V2.5 混同。
- [Kimi 官方仓库固定修订](https://github.com/MoonshotAI/Kimi-VL/tree/41d5ef072bc52a04524f94ab736ff9c29f125fda) 的完整目录为 12 项，没有独立评测代码。
- [光合 Thinking 项目](https://developer.sourcefind.cn/codes/modelzoo/kimi-vl-a3b-thinking_pytorch) 提交 `540877bf6efc02232c82790b86881bb1895d6b03`，2025-05-07 14:10:59 +08:00；[Instruct 项目](https://developer.sourcefind.cn/codes/modelzoo/kimi-vl-a3b-instruct_pytorch) 提交 `3b64d3e2de06953bfa102d0a6cfd28abf8bd45dd`，2025-05-07 14:06:45 +08:00。两个都是 Transformers 原生多图/单图例程，数据集、精度写“无”。它们不是现成赛事包。

## 3. 可以复用的开发测试及其限制

[HYGON SGLang ASR benchmark](https://github.com/HYGON-AI/sglang-das/tree/f89209aa84a4fd0619d0662f6adf6980740efc78/benchmark/asr) 的 README 和 `bench_sglang.py` 均已取得。它支持 Qwen3-ASR，记录 WER、请求吞吐、token 吞吐及延迟，可以帮助开发完整测试链路。

这个脚本默认数据为 `D4nt3/esb-datasets-earnings22-validation-tiny-filtered` 的 validation，自动过滤 30 秒以上音频；优先调用 tokenizer 的 normalize，否则只做小写/去首尾空白。它没有证明赛事指定该子集，也不能不加审核地作中文 CER 或长音频 RTF 的正式验收程序。仓库中的手工 ASR 功能测试默认 0.6B，内置转写容差 15%，也不是本赛事“相对官方基线 2%”的规则。

[OpenDAS/evalscope_dataset](https://developer.sourcefind.cn/codes/OpenDAS/evalscope_dataset)（15891）也可读，但本轮取得的根目录和 README 是通用 EvalScope 框架，未声明与本赛事及六个模型的固定基线关联。没有把它登记成赛事下发材料。未把该大型仓库所有深层文件逐一下载，因此不作“内部绝无相关文件”的断言。

## 4. 社区代码入库要求与赛事要求应并存

[ModelZoo 通用模板](https://developer.sourcefind.cn/codes/modelzoo/template/-/blob/88a5074ab8b2c88bbf24de306ffcab97ee9e87a4/README.md) 和 [ModelZooStd.md](https://developer.sourcefind.cn/codes/modelzoo/template/-/blob/88a5074ab8b2c88bbf24de306ffcab97ee9e87a4/ModelZooStd.md) 已取得。通用标准要求模型元数据 `model.properties`、真实 GitLab Project ID、`LICENSE`、`icon.png`、依赖文件、演示小数据，原 README 改存 `README_origin.md`，非权重文件尽量不超过 50 MB。

通用模板允许资源限制下仅给中英文正常输出的说明；**本赛事另有官方 baseline、精度门槛、两轮性能、镜像和八章报告要求，应按赛事口径补齐，不能用社区通用模板降低要求。**把代码托管到光合也不等于完成赛事提交表或获得验收。

## 5. 本地证据索引

- `evidence/research-modelzoo-project-list-20261019.json`：626 个公开项目的精简元数据，7 页匿名 API 完整遍历。
- `evidence/research-sourcefind-project-search-20261019.json` 与 `research-sourcefind-project-search-extra-20261019.json`：模型名、赛事、baseline、eval 等公开项目元数据检索；不是源码全站搜索。
- `evidence/research-modelzoo-{2144,1628,1498,1497,365,15891}-20261019.json`：真实目录及 README，15891 仅取递归第一页和完整根目录。
- `evidence/research-modelzoo-commits-20261019.json`：精确提交 SHA、时间和链接。
- `evidence/research-modelzoo-source-files-20261019.json`：选取的原始推理、修复、依赖和属性文本。
- `evidence/public-repos/qwen3-asr-baae2d0d/`：按固定提交下载的 ASR 修复脚本、推理、依赖、属性；`research-modelzoo-qwen3asr-download-hashes-20261019.json` 保存 SHA256。没有执行这些代码。
- `evidence/research-publisher-repos-20261019.json`、`research-publisher-model-cards-20261019.json`、`research-publisher-file-lists-20261019.json`：发布方完整目录、模型卡、模型文件清单。
- `evidence/research-framework-eval-files-20261019.json`、`research-framework-asr-benchmark-20261019.json`：HYGON 框架配方/测试原文及 Recon release smoke。

GitHub 公共匿名 API 返回 rate limit 后，复用了本机已登录 `zhl-2022` 的 gh 凭据读取公开资料；未输出或保存 token，未修改 GitHub。搜索出现的第三方新闻聚合内容未作为技术结论来源。
