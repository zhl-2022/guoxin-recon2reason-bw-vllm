# 六个候选模型的公开评测材料审计

核查时段：2026-10-19 晚至 2026-10-20 凌晨（Asia/Shanghai）。本次只读取本地规则、发布方模型仓库、官方代码和数据集作者页面；没有启动算力、运行模型、提交表单或下载权重／大数据集。赛事云文档附件、赛题板和提交表由主审计另行核对，本文不据模型卡替代赛事验收。

## 1. 结论与使用边界

**模型与推理示例公开，不等于对应赛事的固定评测包齐备。**六个模型中，Kimi-VL 的通用 OCRBench／MMMU 对照资料最接近可复现，ASR 有明确通用解码设置和公开语料成绩；但本次读取的模型发布方仓库均没有明确标为本次赛事的固定子集、GPU baseline JSON、预测文件、统一评测入口和提交检查器。只能写“在这些已核查来源中未发现”，不能推断材料必须私发、报名后才可取得或尚未发布。

此前工程要求的“先取得认领确认”“必须镜像 digest”不是由本次模型资料支持的正式门槛。是否必须、是否先到先得、提交需要哪些字段，应回到赛事原文及表单。模型固定 revision 和文件校验是复现证据，不等于新增比赛条件。

| 候选模型 | 已核验的公开材料 | 仍缺少的具体映射 | 对集中完成的影响 |
|---|---|---|---|
| Recon2Reason-Reasoning-4B | 模型、生成配置、发布完整性检查；BF16／SDPA／greedy 环境说明 | 实际 benchmark 名、样本清单、得分、赛事适用指标／GPU 参考 | 服务已跑通，但不能只凭体量小判定正式评测最容易齐备 |
| RoboBrain2.5-8B-NV | 官方推理器、四类提示与 demo；关联 FlagEvalMM 公开评分器 | 本模型赛事图集、动作／坐标解析器、GPU 参考输出、固定解码 | 通用 RoboSpatial 准确率和赛事坐标对参考的一致率不是同一指标 |
| Qwen3-ASR-1.7B | 明确的 BF16／vLLM／greedy／1024／不指定语言；公开语料成绩 | 精确 split／版本／筛选、中文与混语规范化、逐样本预测和赛事 baseline | 可先完成公开语料开发评测，但不能将模型卡整表视为比赛固定子集成绩 |
| Qwen3-ForcedAligner-0.6B | 实际对齐实现、中英文音频／文本 demo、AAS 表 | MFA／人工标注集合、拼接生成规则、评分脚本、赛事接口与负载 | 小模型并不等于验收资料最齐；先补评测定义更划算 |
| MiMo-V2.6-Distill-Qwen-9B | 9B 模型卡、agent benchmark 结果、SGLang 示例与 chat template | 该 9B 的赛事 T01 数据／baseline／思考开关；完整通用 agent harness | 旧 MiMo-7B 仓库与成绩不能替代本题 |
| Kimi-VL-A3B-Instruct | OCRBench 867、MMMU-Val 57.0、greedy 对齐说明；benchmark 作者的代码／数据公开 | 本次赛事固定 subset、token cap、解析／预处理配置、GPU baseline 文件 | **仅按公开评测资料完整程度最接近**；工程未实测，不能据此承诺最短交付 |

## 2. Recon2Reason：没有隐藏在发布检查里的精度评测

固定模型 revision 为 `f8faf41a1d5fe392f2d1ee31884f79398da59c99`。可直接下载的文件包括 [README.md](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/README.md)、[generation_config.json](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/generation_config.json)、[verify_release.py](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/verify_release.py) 和 `SHA256SUMS`。

`verify_release.py` 检查参数总数及五个特殊 token；`--generate` 只用白色图片生成一个 token。它是发布完整性／最小生成检查，没有 benchmark 数据、语义评分或参考答案。模型卡的 Evaluation 仅说明 BF16、PyTorch 2.8.0、Transformers 4.57.1、SDPA、greedy 和 RTX PRO 6000 Blackwell；没有报告具体评测集或分数。

模型卡明确把检索增强场景重建扩展与推理模型分开，但**没有说“评测集另行发布”**；其中没有扩展仓库、评测数据或 leaderboard 的链接。其余唯一上游链接指向 Qwen3-VL 基座。不能猜测一个 Recon2Reason GitHub 地址，或把重建扩展当作本次 serving 的必需材料。

## 3. RoboBrain：公开推理协议可以取，固定赛事坐标参考未见

模型 revision 为 `7ae187cc62e45cfa1c5904903a8f017f11b2037b`，模型 API 文件清单公开，但该 HF 仓库为 gated；本轮匿名 raw 文件请求返回 401，没有尝试绕过。官方 [FlagOpen/RoboBrain2.5](https://github.com/FlagOpen/RoboBrain2.5/tree/af98c932aac9ff715d70da177088d7bb95573ff7) 固定在 `af98c932aac9ff715d70da177088d7bb95573ff7`，完整 archive 共 21 个文件，主要为 [inference.py](https://github.com/FlagOpen/RoboBrain2.5/blob/af98c932aac9ff715d70da177088d7bb95573ff7/inference.py)、README、依赖与 `assets/demo/` 五张图片。

通用、grounding、pointing、trajectory 提示和输出格式已公开；这是功能协议。默认推理采样及部分 demo 的 `do_sample=False` 不应混为同一固定评测设置。

README 推荐的 [FlagEvalMM](https://github.com/flageval-baai/FlagEvalMM/tree/fef27ec696c532d12f0db389bcbbf79eab0e4c41) 已核查，固定 revision 为 `fef27ec696c532d12f0db389bcbbf79eab0e4c41`。可取得：

- `tasks/ocrbench/evaluate.py`、`tasks/ocrbench/ocrbench_test.py`、`tasks/ocrbench/process.py`。
- `tasks/mmmu/mmmu_val.py`、`tasks/mmmu/process.py` 和 `flagevalmm/evaluator/mmmu_dataset_evaluator.py`。
- `tasks/robo_spatial_home/evaluate.py`／`evaluate_norm1k.py`、对应 task config 与 process；数据入口是 [RoboSpatial-Home](https://huggingface.co/datasets/chanhee-luke/RoboSpatial-Home)。

不过，RoboBrain README 明确说 FlagEvalMM 用于 RoboBrain 2.0；其 `model_zoo/vlm/robobrain/qwen_model_adapter.py` 使用 `Qwen2_5_VLForConditionalGeneration`，不能当作 2.5 NV 的现成基线。RoboSpatial 是相对真实标注的准确率／点落区评分，不能代替赛事所述“解析动作／坐标相对 GPU 参考输出一致率”。

## 4. ASR 与 ForcedAligner：同一官方 repo，评测不是同一回事

官方 [QwenLM/Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR/tree/7c6daf77a2421100f5fb066495372c00129d39ff) 固定 revision 为 `7c6daf77a2421100f5fb066495372c00129d39ff`，完整 archive 共 32 个文件。含推理、服务、微调、示例及论文，没有名为 eval／benchmark 的完整评分入口、固定评测 manifest、原始标注或逐样本预测文件。`finetuning/qwen3_asr_sft.py` 的 eval 文件用于训练验证损失，不等于识别质量评分器。

### 4.1 Qwen3-ASR-1.7B

原始 checkpoint revision 为 `7278e1e70fe206f11671096ffdd38061171dd6e5`。可以取得 [vLLM 示例](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_asr_vllm.py)、`qwen_asr/inference/qwen3_asr.py`、`qwen_asr/inference/utils.py` 和 [README Evaluation](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/README.md#evaluation)。发布方给出 BF16、vLLM、greedy、最多 1024 新 token、不指定语言；公开表中本模型 LibriSpeech clean／other 为 1.63／3.38，Fleurs-en／zh 为 3.35／2.41。

语料作者入口确实公开：[LibriSpeech / OpenSLR 12](https://www.openslr.org/12)、[Google FLEURS](https://huggingface.co/datasets/google/fleurs)。但“公开可下载原始语料”和“取得本次固定子集”不同；应核实 subset／split／版本／筛选及文本规范化。不能自选 dev 代替 test，也不能用任意规范化后与模型卡数值直接比门槛。官方中英 `asr_zh.wav`／`asr_en.wav` 是示例音频，只有功能价值。

### 4.2 Qwen3-ForcedAligner-0.6B

原始 checkpoint revision 为 `c7cbfc2048c462b0d63a45797104fc9db3ad62b7`；`-hf` 变体 revision 为 `c07281df297b9905d24a508279258cccf987a064`，不能静默替换。可以取得 [examples/example_qwen3_forced_aligner.py](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_forced_aligner.py) 和 [qwen_asr/inference/qwen3_forced_aligner.py](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/qwen_asr/inference/qwen3_forced_aligner.py)。demo 提供中英音频、原文、语言和多种输入形式检查；返回词／字级时间段，但未提供人工时间戳 ground truth。

README 公布 AAS（毫秒，越低越好）：MFA-Labeled Raw 平均 42.9，Concat-300s 平均 52.9，Human-Labeled 平均 32.4。对应精确标注集合、拼接规则和评分脚本在本次完整 repo 中未找到，因此不能复制 42.9 当作比赛阈值。独立对齐走 Transformers `.align()`；不能因为 ASR 支持 vLLM，就假定 aligner 本身已有相同的 OpenAI 服务接口或有效框架计件方式。

## 5. MiMo 9B 与 Kimi-VL

### 5.1 MiMo-V2.6-Distill-Qwen-9B

准确题目是 [XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/blob/2367e865d009c13ac81713a2878291d33ab28177/README.md)，revision `2367e865d009c13ac81713a2878291d33ab28177`。公开 SWE Verified 61.1（avg@3）、SWE Pro 44.6（avg@3）、Terminal Bench 2.1 37.1（avg@1）等 agent 结果，并标明数项 MiMo mini 为内部集。SGLang 示例开启思考并使用 `mimo` reasoning parser，但它没有给该模型 GSM8K／MMLU 固定结果或赛事配置。

已检查的 [XiaomiMiMo/MiMo](https://github.com/XiaomiMiMo/MiMo/tree/3a3fe65e6081c9f340ff0d24d82c4d7a96a247c5) revision `3a3fe65e6081c9f340ff0d24d82c4d7a96a247c5` 是旧 MiMo-7B 项目，不是本模型的 9B 评测包。其温度 0.6、重复次数和旧模型分数不能挪来填本题。没有据模型名称猜测新的官方 repo URL。

### 5.2 Kimi-VL-A3B-Instruct

模型 revision 为 `398eede0903cd983a2bfa0cc634e9ac1d843f375`。[模型卡](https://huggingface.co/moonshotai/Kimi-VL-A3B-Instruct/blob/398eede0903cd983a2bfa0cc634e9ac1d843f375/README.md) 公布 OCRBench 867、MMMU-Val 57.0、MathVista 68.7，明确 Instruct 可以 greedy，并称与其评测设置一致。官方 [MoonshotAI/Kimi-VL](https://github.com/MoonshotAI/Kimi-VL/tree/41d5ef072bc52a04524f94ab736ff9c29f125fda) revision `41d5ef072bc52a04524f94ab736ff9c29f125fda` 共 11 个文件，仅 README、论文、依赖、图示；没有专用 eval 代码或完整重现配置。

benchmark 作者确实提供通用代码和数据，可下载的具体入口如下。它们可以用来准备通用评测，但模型卡全量成绩与赛事子集不一定同分布。必须确认固定子集、max_tokens、图像预处理、答案抽取与 baseline 数值一致后才可正式判定。

| 官方来源 | 本轮 revision | 具体文件／入口 |
|---|---|---|
| [MMMU-Benchmark/MMMU](https://github.com/MMMU-Benchmark/MMMU/tree/268471d0d488258990025331c7528359c324aa25) | `268471d0d488258990025331c7528359c324aa25` | `mmmu/main_eval_only.py`、`mmmu/main_parse_and_eval.py`、`mmmu/utils/eval_utils.py` |
| [MMMU/MMMU 数据](https://huggingface.co/datasets/MMMU/MMMU/tree/876ce5cb130f7f7e290ce4d9984357737d4db5cf) | `876ce5cb130f7f7e290ce4d9984357737d4db5cf` | HF 文件清单公开、非 gated；本轮未拉数据 |
| [Yuliang-Liu/MultimodalOCR](https://github.com/Yuliang-Liu/MultimodalOCR/tree/4e363b3f499811b43d792ef0bb33932ef05eca27) | `4e363b3f499811b43d792ef0bb33932ef05eca27` | `OCRBench/README.md`、`OCRBench/example.py`、`OCRBench/scripts/`；勿把 OCRBench_v2 当成原 1000 分 OCRBench |
| [Google FLEURS 数据](https://huggingface.co/datasets/google/fleurs/tree/70bb2e84b976b7e960aa89f1c648e09c59f894dd) | `70bb2e84b976b7e960aa89f1c648e09c59f894dd` | HF 文件清单公开、非 gated；本轮未拉数据 |

## 6. 证据保存与检索限制

机器可读证据保存在 `evidence/research-model-eval-20261019/`。每个模型保存 HF API revision／文件列表；公开可取得的小文本另保存 URL、内容或访问失败。代码 repo 保存固定 SHA、完整文件清单及相关文本。没有下载任何模型权重、大语料或执行发布方脚本。

GitHub REST API 返回匿名速率限制 403，改用公开 Git refs／固定 SHA archive 与只取文件索引的 Git 读取；RoboBrain HF raw 返回 401，保留该访问结果。前者不妨碍固定代码树核对，后者限制了该 gated 模型卡原始文件的匿名归档。网页可读内容、既有本地配置证据与本次原始下载证据分别记录。

正式材料是否齐备，应将主审计取得的云文档附件／ModelZoo／赛题板证据补到本表，不把本次“未发现”改写成“官方没有”。在没有完整赛事映射前，六题都不应被标成已确认可正式验收；这不阻止继续把工程、公开评测接入和报告准备到可复现程度。

## 7. 集中完成顺序的判定

以下只用于安排下一轮工作，不能替代赛题板实时状态，也不是开卡指令：

1. **先把 Recon2Reason 的赛事验收映射核清。**它的服务工程已完成，若赛事附件给出该模型固定图集／指标／参考，就可优先完整收尾；若没有，不能仅因为服务成功把它列为最确定可提交题。
2. **公开评测资料候选以 Kimi-VL 与 ASR 优先核对。**Kimi 有 OCRBench／MMMU 数值和对应公开 benchmark；ASR 有明确通用解码及语料成绩。两者仍需赛事对应关系，其中 Kimi 还没有本工程的实际适配证据。
3. **RoboBrain 排在坐标图集、解析器和 GPU 参考明确之后。**已有兼容候选值得保留，但当前不应以自己的红方块／RoboSpatial 分数代替赛事 98% 一致率。
4. **ForcedAligner 先补 AAS 标注与计分／接口；MiMo 9B 先补对应 T01 baseline。**这两项当前都不因模型体量或公开生成示例而自然变成资料最齐的快题。

如果主审计取得统一官方包，顺序应据其中实际覆盖的模型、题数及当前工程差距重新排列；没有必要固守上述先后。
