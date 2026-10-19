# 国芯国模：评测材料与提交就绪核查

核查时段：北京时间 2026-10-19 晚至 2026-10-20 凌晨。仅浏览公开网页、读取提交表、下载官方报告附件和公开小型源码；未开卡、未运行模型、未修改算力平台、未填写或提交表单、未发布仓库或镜像。

## 1. 结论

**题目、主要验收指标、报告模板和正式提交入口已经明确；公开的模型推理、适配及部分开发评测代码也确实存在。六个候选题的赛事专属固定数据、GPU baseline 文件及正式评测入口，仍未从本轮核查的公开入口取得。**这不等于主办方没有公开材料，更不等于必须等待报名或认领确认才能开发。

用户本轮进一步说明：“目前别人都没有提交任务”，因此将其称为尚无认领。后续按这一信息和先到先得原则，集中推进完整有效提交，不再追认领回执。本轮未找到独立的实时认领／提交／验收状态表 URL；不将用户提供的状态冒充本次独立查证结果，也不让这个入口缺失阻断工程。

当前最接近工程收尾的是 **Recon2Reason × BW × vLLM × BF16**；能够复用更多精确官方部署资料的是 **Qwen3-ASR × BW × vLLM × BF16**。两者都还需要确定赛事验收包，不能只因已跑通服务就称为完整可交题。仅按公开通用评测资料的完整程度，Kimi-VL 更具体，但它尚没有本工程的运行证据，不能直接推断交付最快。

## 2. 已经实际查到什么

| 入口 | 本轮实际操作与结果 | 边界 |
|---|---|---|
| [赛事云文档](https://bvjoh3z2qoz.feishu.cn/wiki/OkLBws6uWiG1Q0kpHLKcxXLmnif) | 读取参赛流程、T01–T04、模型清单、官方材料清单、提交说明、脚本模板和分题材料说明；页面显示 10 月 19 日修改 | 这份文档明确列材料类别，不代表每类已经附有下载包 |
| 官方报告附件 | 从文档内真实下载 `国芯国模黑客松-技术报告模板.md`，原样保存为 [report-template.md](../evidence/official-materials/20261019/report-template.md) | 14.09 KB；SHA256 `b151143f6fa38c87e301cfc9335a94d17fcd49c7113a53fe05f89c04b45f349f`；不是基线／评测压缩包 |
| 赛题清单／状态入口 | 云文档的“四、模型清单”列模型、类型、权重大小和许可；材料清单提及公示认领、提交、验收状态 | 所查章节未提供独立状态表链接；模型清单本身没有这些实时状态列 |
| [技术报告登记表](https://bvjoh3z2qoz.feishu.cn/share/base/form/shrcnLIas6FqdBnaJ9sDLUUNXnc) | 实际读取全部必填字段及帮助文字 | 未填写个人资料、未上传报告、未提交 |
| [光合 ModelZoo](https://developer.sourcefind.cn/codes/modelzoo) | 匿名 GitLab API 分页遍历 **626 个公开项目**，读取候选项目目录、README、源码和提交时间 | 不是全站源码内容搜索；大型 EvalScope 仓库没有逐个下载全部深层文件 |
| 模型发布方与 HYGON 官方仓库 | 对六模型固定 revision，读取公开文件清单、推理源码、评测说明、部分评分器及压测脚本 | 未下载权重／大语料，未执行下载代码；gated 文件未绕过访问限制 |

云文档附件第 289 行明确：T02–T04 的评测器、数据集与判定口径随分题材料下发；第 332 行明确：生成／语音性能测法后续随分题材料提供。正文里的 T01 GSM8K/MMLU 样例和占位 baseline 不能填成其他模型的官方结果。

## 3. 六个候选题：可取得与还缺的材料

| 候选题 | 已核实可取得的材料 | 正式验收仍未取得／未确定 | 当前工程差距 |
|---|---|---|---|
| **Recon2Reason-Reasoning-4B / T02** | [发布方模型卡与文件](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/tree/f8faf41a1d5fe392f2d1ee31884f79398da59c99)、生成配置、`SHA256SUMS`、`verify_release.py`；BF16/SDPA/greedy 环境说明 | 本模型按 OCRBench/MMMU、对应 VQA 还是空间推理图集验收；固定样本、GPU 分数／输出、判分／解析器、输出限制、思考开关、压测图像分辨率 | 已有原生 vLLM 服务；仍须正式评测、六档两轮、成功参数固化、完整交付镜像及干净环境复跑 |
| **RoboBrain2.5-8B-NV / T02** | [FlagOpen 官方推理与五张 demo](https://github.com/FlagOpen/RoboBrain2.5/tree/af98c932aac9ff715d70da177088d7bb95573ff7)，四类 prompt；FlagEvalMM 的通用评分器 | 本模型适用的具身／VL口径、固定图像／深度图、GPU 动作／坐标参考、解析器、解码、参考一致率或分数基线 | 分块 math 候选已通过数值和新尺寸图；还缺正式精度、大图性能、统一成功入口及完整复跑 |
| **Qwen3-ASR-1.7B / T04** | [光合精确 vLLM 项目](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch)、初始化顺序修复；[Qwen 评测设置](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/README.md#evaluation)；LibriSpeech/FLEURS 数据源；HYGON ASR 开发压测 | 赛事指定数据 revision/split/题数／过滤、参考转写、中文和混语规范化、WER/CER 实现、GPU baseline、音频性能负载及计量范围 | 两条短合成音通过；尚缺流式范围核验、自然／长音频、质量评测、音频性能、依赖和兼容改动的一键封装 |
| **Qwen3-ForcedAligner-0.6B / T04** | [Qwen 对齐实现与示例](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_forced_aligner.py)、AAS 结果表、HYGON pooling 启动配方 | 精确音频＋文本＋人工／MFA时间戳标注、拼接规则、词／字边界处理、AAS计算／聚合、GPU baseline、框架服务计件和性能口径 | 本工程未跑；HYGON 配方也只验证启动，对齐请求、time-bin后处理和时间戳精度未完成 |
| **MiMo-V2.6-Distill-Qwen-9B / T01** | [精确 9B 模型卡](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B/tree/2367e865d009c13ac81713a2878291d33ab28177)、SGLang示例、agent基准成绩 | 该9B的赛事GSM8K/MMLU固定子集、GPU baseline、思考开关、greedy/max_tokens、判分器 | 尚未实测服务与正式测评；旧MiMo-7B仓库和分数不能替代 |
| **Kimi-VL-A3B-Instruct / T02** | [模型卡](https://huggingface.co/moonshotai/Kimi-VL-A3B-Instruct/tree/398eede0903cd983a2bfa0cc634e9ac1d843f375) 有OCRBench867/MMMU-Val57.0及greedy说明；[MMMU作者代码](https://github.com/MMMU-Benchmark/MMMU/tree/268471d0d488258990025331c7528359c324aa25)和[OCRBench作者代码](https://github.com/Yuliang-Liu/MultimodalOCR/tree/4e363b3f499811b43d792ef0bb33932ef05eca27)可取；有光合旧部署例程 | 赛事固定子集、对应数字基线、token cap、图像预处理、答案抽取、思考变体和负载 | 本工程未实测；公开全量模型卡成绩不自动等于赛事子集成绩 |

逐模型 revision、文件和指标细节见 [发布方评测审计](audit-model-evaluation.md)；光合项目和框架来源见 [公开仓库审计](audit-public-repos.md)。

### 3.1 三个容易误认的文件／仓库

1. Recon 的 `verify_release.py` 只验证参数／特殊 token 和可选白图单 token 生成，不计算精度。模型卡“重建扩展另行发布”不等于“评测集另行发布”。
2. 光合 `robobrain_pytorch` 是旧 `BAAI/RoboBrain`、Qwen2.5、vLLM0.8.5；FlagEvalMM 中的 RoboBrain adapter 也不是2.5-NV。通用RoboSpatial准确率不等于赛事对GPU参考坐标的一致率。
3. ModelZoo Qwen3-ASR 的[固定 README](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch/-/blob/baae2d0d52e4d4aac2476d0960bb62f0d0076609/README.md)及[修复脚本](https://developer.sourcefind.cn/codes/modelzoo/qwen3-asr_pytorch/-/blob/baae2d0d52e4d4aac2476d0960bb62f0d0076609/fix_qwen3asr_vllm_init_order.sh)在 **2026-07-16** 已公开，版本栈与本轮相近。应该复用和引用，不重复当作从零的新发现；但仓库存在不能证明赛事已经提交／验收／占奖。该仓库数据集写“暂无”，没有赛事 `baselines/`、`data/`、`verify.py`、`bench.sh`。

### 3.2 现在能直接复用的开发评测

- [HYGON ASR benchmark](https://github.com/HYGON-AI/sglang-das/tree/f89209aa84a4fd0619d0662f6adf6980740efc78/benchmark/asr)：真实取得 README 与 `bench_sglang.py`，支持Qwen3-ASR的WER、延迟、吞吐。默认earnings22 tiny、过滤超过30秒音频、规范化规则固定在代码中；需要核对后才能用于赛事，不能直接冒充中文CER／长音频RTF。
- OCRBench/MMMU作者代码、数据入口和FlagEvalMM评分器可以先接成开发对照测试；须保留具体revision、样本manifest、参数及结果，不生成伪“官方baseline”。
- [ForcedAligner官方配方](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/vllm/qwen3-forcedaligner.md)仅服务启动完成，不能直接当完整对齐题解；配方版本也不是当前vLLM0.18.1。

## 4. 提交要求已经确认

### 4.1 登记表必填字段

实际[技术报告登记表](https://bvjoh3z2qoz.feishu.cn/share/base/form/shrcnLIas6FqdBnaJ9sDLUUNXnc)要求：

1. 姓名。
2. 超算互联网账号。
3. 赛道 T01/T02/T03/T04。
4. 适配模型。
5. 按官方模板上传完整技术报告附件。
6. 代码仓库链接字段；帮助文字明确要求同时提供 **SCNet镜像链接＋光合代码仓库链接**。

“添加企微了解细则”为非必填项。这里没有单独的认领确认号或镜像digest必填项。卡型、框架版本、精度和完整复现身份仍须写在报告／仓库中；不能因表单没单列而省略。姓名等提交身份资料在最终填表前确认，本轮不收集、不填入研究报告。

### 4.2 技术交付集合

| 类别 | 提交前必须实际准备 |
|---|---|
| 报告 | 官方八章README；最终配置与真实环境、精度、性能日志一致，清除占位符和相互冲突的开发状态 |
| 环境／镜像 | 评审可获取的完整镜像地址与tag、真实版本和平台证据；新依赖逐项锁定，使用`--no-deps`避免替换原生Torch |
| 入口／改动 | `env.sh`、`env_check.sh`、`run.sh`、`smoke.sh`；可重放的兼容改动、安装和清晰唯一的成功入口 |
| 精度 | 对应官方baseline、数据和`verify.py`，先`--selfcheck`，再保存`verify_result.json`和原始输出 |
| 理解类性能 | 4096/16384输入×1024输出×并发1/8/64；六档各两轮，第二轮计分，请求数为并发两倍且至少8；保留两轮JSONL、档位日志和汇总 |
| 语音性能 | 依T04分题方法，不能用文本六档代替；需确认时长分布、并发、预热、RTF／吞吐／延迟及原始产物 |
| 复现／发布 | 从干净环境一键复跑，报告数字一致；镜像上传SCNet、代码按实际指定方式托管光合，再交登记表 |

[ModelZoo通用入库规范](https://developer.sourcefind.cn/codes/modelzoo/template/-/blob/88a5074ab8b2c88bbf24de306ffcab97ee9e87a4/ModelZooStd.md)另列`model.properties`、真实Project ID、LICENSE、图标、依赖、迷你数据和`README_origin.md`等；若按ModelZoo入库，应一并遵守。社区通用示例的较宽要求不能降低本赛事精度／性能要求。

## 5. 需要补齐的最小外部材料清单

优先只针对第一件Recon索取／定位一个完整版本包，避免同时追六件的所有细节：

- [ ] **Recon验收映射**：明确按OCRBench/MMMU、其他VQA／空间推理，还是动作／坐标对GPU参考一致率验收。
- [ ] **该模型评测包的实际URL**：baseline JSON、原版`verify.py`及自检、固定数据／样本ID与版本、GPU分数或逐样本参考输出、答案／坐标解析器。
- [ ] **固定推理参数**：模型revision、chat template、greedy／思考开关、max_tokens、图像预处理和多图规则。
- [ ] **T02性能细节**：图像分辨率／取图集，失败档位如何接受，数据格式与是否必须完全使用下发bench版本。
- [ ] **T04包（若ASR先齐可切换）**：固定音频manifest与转写、WER/CER规范化、GPU baseline，流式范围，以及音频性能方法。
- [ ] **公开状态与提交方式**：实时提交／验收状态表入口（如有）、已有公开适配是否影响首件，光合个人仓库／fork／MR或指定命名空间的提交方式，镜像访问权限要求。

文档提及先到先得，登记表提交成功仍不等于精度／复现验收通过。没有发现“必须先取得一份单独认领确认才能开发”的具体限制，也未以此要求用户再等。

以上为精确的待确认项，尚未向外部联系人发送消息。它们用于取得缺失文件与消除歧义，不是新增竞赛条件。

## 6. 我们自己的工程缺口：不能全归因于官方材料

- 三题没有完整正式精度实现与结果；Recon/Robo只是外部评测脚本桥，ASR verify/bench入口直接返回待集成。
- 三题没有完整规定性能、最终交付镜像、已发布代码地址或从干净镜像的一键复跑。当前开发ZIP不是已完成的参赛提交件。
- Recon应固化实际成功参数；Robo应统一成功兼容入口并验证大图性能；ASR应把音频依赖锁、venv及插件集成到干净环境入口，补流式／自然语音／长音频。
- 当前CLI把“认领确认”和“digest”列为硬门禁，且外部桥自拟了baseline字段schema。这些是我们加的保守实现约束，**不是已查明的官方全部前置条件**。后续应改为按真实规则和实际官方文件校验，不能让官方文件迁就脚手架。
- digest、固定SHA可以保留为复现增强证据；官方明示要求的是可获取的完整镜像地址和tag，缺digest不能单独阻止提交。

逐文件差距见 [附件与本地交付审计](audit-template-gap.md)。

## 7. 集中完成的选择与下一步边界

1. **第一工程候选仍为Recon。**现有原生服务路径最简单；先确认第5节的本模型验收包／映射，不再为了整理或搜索材料开卡。
2. **ASR作为可切换备选。**官方部署和通用开发压测可复用，已有运行基础；如果T04正式材料先齐，可优先把它完整收尾，但必须补流式、音频方法和一键环境。
3. **Kimi-VL作为评测资料备选。**通用OCR/MMMU材料更明确，但尚需新工程验证。Robo暂后，ForcedAligner和MiMo9B目前不适合仅因模型较小就抢先开卡。
4. 公开文件、依赖锁、评测适配、报告和提交目录都可先在本地完成；一次算力会话集中执行正式精度→规定性能→干净环境复跑，随后停止。

当前尚不能将任一题标为“赛事正式评测材料全部齐备、现在只需开卡跑完即可提交”。可以确认的是，前述工程候选有明确可复用的实现和已有实测基础；一旦对应验收材料补齐，就能集中完成，而不再铺开更多只跑通功能的模型。

## 8. 本地证据与复核

- [官方附件原文](../evidence/official-materials/20261019/report-template.md)；云文档章节与外链快照 `cloud-sections.json`；`cloud-materials.jpg`、`cloud-model-list.jpg`；提交字段 `submission-fields.json`。
- `evidence/research-modelzoo-project-list-20261019.json`：626个公开项目；各项目目录、README、提交SHA和所选源码分别存档。
- `evidence/research-model-eval-20261019/index.json`：发布方、评分器、数据元信息的固定revision和文件SHA索引。
- `evidence/public-repos/qwen3-asr-baae2d0d/`：只下载未执行的公开修复、推理和依赖文件。
- 三份支持报告：`audit-public-repos.md`、`audit-model-evaluation.md`、`audit-template-gap.md`。

本轮没有再次开机检查平台或余额；上一轮已关机证据保持原样。没有把2026-10-19的余额快照冒充本轮实时余额。
