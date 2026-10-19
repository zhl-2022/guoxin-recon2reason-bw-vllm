# Recon2Reason 上游与海光部署依据

核查日期：2026-10-19。本文记录公开一手来源和只读核查结果；尚未验证目标模型在当前超算实例上的推理、精度或吞吐量。

## 当前结论

优先在平台原生 PyTorch 环境中完成 Transformers 单图正确性基线。当前实例已观察到 Python 3.11.9、`torch 2.9.0+das.opt1.dtk2604`、`transformers 4.57.6`，没有预装 SGLang、vLLM、Triton。此状态来自本次平台检查，不能由公开模型说明替代。

若进入服务引擎优化，使用完整、版本相互匹配的 HCU/DAS 镜像作为独立实验环境。已找到 HYGON-AI 官方 cookbook 推荐的 SGLang 0.5.12 / DTK 26.04 / Python 3.10 镜像，并只读验证其注册表元数据。没有找到可证明兼容当前 Python 3.11 / 原生 Torch 2.9 的具体 SGLang 或 vLLM HCU wheel。不要将通用 PyPI 安装命令直接用于平台原生环境。

CPU 无卡实例适合源码、依赖清单和数据检查；卡端正确性与性能验证需要实际分配到 DCU，并以 `torch.cuda.is_available()`、设备名称和一次设备运算确认。

## 模型身份和可复现版本

| 项目 | 已确认信息 | 一手依据 |
|---|---|---|
| 发布方及模型 | `BAAI/Recon2Reason-Reasoning-4B`；Qwen3-VL-4B-Instruct 的空间推理微调模型 | [BAAI 模型卡](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B) |
| 固定模型修订 | `f8faf41a1d5fe392f2d1ee31884f79398da59c99` | [Hugging Face 模型 API](https://huggingface.co/api/models/BAAI/Recon2Reason-Reasoning-4B)；核查时读取 API 的 `sha` |
| 架构 | `Qwen3VLForConditionalGeneration`，`model_type=qwen3_vl`；无需自定义模型代码 | [固定修订 config.json](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/config.json) |
| 权重 | BF16；2 个 Safetensors 分片；4,437,815,808 个参数；张量总字节数 8,875,631,616 | [固定修订权重索引](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/model.safetensors.index.json) |
| 官方正确性基线 | Transformers 4.57.1、PyTorch 2.8.0、SDPA、greedy；发布方在 NVIDIA 设备上评测 | [固定修订模型卡](https://huggingface.co/BAAI/Recon2Reason-Reasoning-4B/blob/f8faf41a1d5fe392f2d1ee31884f79398da59c99/README.md) |
| 当前 Transformers 类存在 | 4.57.6 上游已包含该模型类及 SDPA/eager 路径 | [Transformers 4.57.6 模型源码](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_vl/modeling_qwen3_vl.py) |

张量总字节数不等于推理显存占用。激活值、图像 token、KV cache、服务引擎预分配和并发请求都需要额外显存。

Hugging Face 模型页中自动生成的 vLLM/SGLang 使用示例不是海光硬件验证报告。平台模型入口为 [SCNet 模型页](https://www.scnet.cn/ui/aihub/models/sugon_scnet/Recon2Reason-Reasoning-4B)；平台快照与 BAAI 固定修订是否完全一致，仍需要比对配置、文件清单或发布方提供的校验值。

## 海光原生服务引擎来源

### SGLang

官方下游仓库为 [HYGON-AI/sglang-das](https://github.com/HYGON-AI/sglang-das)。

HYGON-AI cookbook 的固定提交 `0a5aa29b5720c36d2e033e220834edfe7ed6a6ce` 提供以下完整镜像，支持矩阵列出了 BW1100、BW1000、K100_AI：[镜像表](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/docker_images.md)。

```text
harbor.sourcefind.cn:5443/hcu/admin/base/sglang:0.5.12-ubuntu22.04-dtk2604-py3.10
```

本次通过公开注册表的标准匿名 pull token 流程，仅获取 manifest 和 32 KB 左右的 image config，没有拉取镜像层：

| 元数据 | 2026-10-19 观察值 |
|---|---|
| Manifest digest | `sha256:878d317dfa18efae70516a59cc836efc77b251efbe4ca85de67171bc2c3aca68` |
| Config digest | `sha256:caeff0e9e6efef918a31359c4764b18bf2d428f2b76e3580c788f4cc8b0e93ad` |
| 平台 | `linux/amd64` |
| 创建时间 | `2026-08-17T12:31:01.906182739Z` |
| 压缩层总大小 | 9,006,297,435 字节 |
| Python / DTK | 构建记录使用 Python 3.10；环境含 `DTK_VERSION=2604`、`ROCM_PATH=/opt/dtk` |

注册表一手端点为 [Manifest](https://harbor.sourcefind.cn:5443/v2/hcu/admin/base/sglang/manifests/0.5.12-ubuntu22.04-dtk2604-py3.10) 和 [Config blob](https://harbor.sourcefind.cn:5443/v2/hcu/admin/base/sglang/blobs/sha256:caeff0e9e6efef918a31359c4764b18bf2d428f2b76e3580c788f4cc8b0e93ad)。浏览器直接打开可能先返回标准 401 challenge；本次使用注册表返回的匿名 token 服务成功读取。

构建历史中明确安装过以下配套版本：

| 包 | 构建历史中的版本 |
|---|---|
| `torch` | `2.10.0+das.opt1.dtk2604.2608131652.g28498c` |
| `sglang` | `0.5.12+das185.dtk2604.torch2100.2608121934.gcbf025` |
| `sglang-kernel` | `0.4.2.post2+das185.dtk2604.torch2100.2608121934.gcbf025` |
| `transformers` | `5.6.0` |
| `triton` | `3.6.0+das185.dtk2604.torch2100.2608131719.gb796b1` |
| `vllm` | `0.21.0+das.dtk2604.torch2100.2606111143.g8c979d` |
| `vllm-hcu` | `0.21.0+das.dtk2604.torch2100.2608132222.g386d02` |

构建历史后续还有安装 `torchaudio==2.11.0` 的步骤，未指定 `--no-deps`。因此上表仅证明构建中曾指定这些包版本，不能证明最终运行时 `torch` 版本；启动镜像后必须重新读取包元数据，并确认原生 `+das` Torch 未被替换。

平台社区镜像 `jsyadmin/sglang-0.5.12-ubuntu22.04-dtk26.04-py3.10` 的名称与官方镜像相近。本次没有公开一手证据证明 `jsyadmin` 的官方发布身份，也没有证据证明其 digest 与上述官方镜像一致。创建实验前应查看平台镜像来源和启动后的真实包版本，不能仅凭标题断言等价。

官方 [Qwen3-VL 部署页](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/sglang/qwen3-vl.md) 存在 Qwen3-VL-4B 的 SGLang 0.5.12 配置，例子使用 4 卡。它是同架构部署依据，没有直接证明本模型、BW64GB 单卡或当前镜像组合已经验证通过；不应照搬其 4 卡拓扑、NUMA 和系统参数。

当前主分支 [README_HCU](https://github.com/HYGON-AI/sglang-das/blob/f89209aa84a4fd0619d0662f6adf6980740efc78/README_HCU.md) 已转向 0.5.18 / Python 3.10 / Torch 2.11 / DTK 26.04；0.5.12 开发分支 README 仍提到 Torch 2.5.1。两者都不能充当当前 Python 3.11 / Torch 2.9 实例可直接安装的兼容性证据。

### vLLM DAS 插件

官方仓库为 [HYGON-AI/vllm-plugin-das](https://github.com/HYGON-AI/vllm-plugin-das)。[固定修订安装说明](https://github.com/HYGON-AI/vllm-plugin-das/blob/c15b21bcc12df4bb83b2aba2c8a94f04590b2139/README.zh-CN.md) 明确要求相互匹配的 HCU/OpenDAS 运行栈；插件版本检查通过不能证明 Torch、DTK 和原生算子 ABI 兼容。

核查时默认分支为 `v0.28.1-dev`，固定提交 `c15b21bcc12df4bb83b2aba2c8a94f04590b2139`。其 [CI 环境配置](https://github.com/HYGON-AI/vllm-plugin-das/blob/c15b21bcc12df4bb83b2aba2c8a94f04590b2139/.github/workflows/configs/hcu-runner-environment.json) 要求原生 Torch 2.11 发布线，以及 Python 3.10.12 或 3.12.12；不能把这个分支直接套入现有 Torch 2.9 / Python 3.11 环境。

官方 [Qwen3-VL-8B 验证配置](https://github.com/HYGON-AI/vllm-plugin-das/blob/c15b21bcc12df4bb83b2aba2c8a94f04590b2139/tests/models/qwen3_vl_8b_mmmu_evalscope.yaml) 提供 eager、小批量、受限上下文的验收方式。它不等于 Recon2Reason-4B 在当前设备上已验证。

## 保留原生 Torch 的下一步

1. 在无卡实例完成包清单、模型配置、图像处理和下载路径检查，记录 `torch.__version__`、`torch.__file__`、`torch.version.hip`，并测试 `from transformers import Qwen3VLForConditionalGeneration, AutoProcessor`。此阶段不安装任何服务引擎。
2. 用平台已下载或挂载的模型目录检查 `config.json`、两个分片、索引、processor、tokenizer 和 chat template。仅下载了配置不算权重已准备好。
3. 在真实分配到 1 张 DCU 后，先验证小张量 BF16 设备运算，再使用本地模型和本地图像运行 Transformers greedy 单请求，`attn_implementation="sdpa"`，`max_new_tokens=32`。如果 SDPA 原生路径失败，保留错误证据，再以小输入尝试 `eager` 正确性对照；不自动替换 Torch。
4. 保存输入图像大小、processor 输出形状、prompt token 数、生成 token 数、设备峰值显存和实际输出。模型成功加载、设备运算成功、有效图像问答、目标评测精度达标是不同验收层。
5. 正确性基线通过后，再建立完整 HCU SGLang 镜像的独立实验；先运行包清单和设备预检，再迁移同一固定模型快照。同样的输入、精度和生成参数通过后，才比较吞吐、TTFT 和 TPOT。

HIP 版 PyTorch 仍使用 `torch.cuda` / `cuda:0` 接口；接口名称本身不证明正在使用 NVIDIA，参见 [PyTorch 2.9 HIP 语义说明](https://docs.pytorch.org/docs/2.9/notes/hip.html)。

## 本次核查范围

- 已读取：BAAI 固定模型配置、索引和模型卡；Transformers 4.57.6 源码；HYGON-AI cookbook、README、版本与 CI 配置；官方注册表的 manifest 和 config。
- 未执行：模型权重或镜像层下载、远端安装、镜像创建、作业提交、卡端推理或基准测试。
- 待验证：SCNet 模型快照对应修订、BW64GB 实际芯片/架构、社区镜像来源与包状态、完整镜像最终原生 Torch 版本、单卡多模态正确性及性能。

## 原生 Transformers 参考检查脚本

`scripts/recon2reason_reference.py` 不安装依赖、不修改环境、不下载模型。`--model` 必须指向本地模型目录，`--output` 必须是尚不存在的 JSON 文件，父目录需要预先存在。脚本记录包版本、原生 Torch 路径、模型配置哈希、输入图片哈希、模板、图像网格、token 长度和失败阶段。

在无卡实例中先检查导入、AutoProcessor、逐张单图及前两张双图的模板和 tokenization：

```bash
python scripts/recon2reason_reference.py \
  --model /absolute/path/Recon2Reason-Reasoning-4B \
  --image /absolute/path/scene1.png \
  --image /absolute/path/scene2.png \
  --output /absolute/path/reference-cpu-001.json \
  --preflight-only
```

没有现成图片时，可在模型目录之外的全新独立目录创建两张简单的 Pillow 形状/文字图。它们仅用于检查输入链路，不提供模型精度证据：

```bash
python scripts/recon2reason_reference.py \
  --model /absolute/path/Recon2Reason-Reasoning-4B \
  --create-fixtures /absolute/path/new-functional-fixtures \
  --output /absolute/path/reference-fixtures-cpu-001.json \
  --preflight-only
```

CPU 模式不会加载权重或检查 CUDA。默认每张处理图片最多 262,144 像素；原始文件最多 20 MiB、16,777,216 像素。脚本限制图片数量和 processor 输出 tensor 大小；`--max-image-pixels` 可显式调整到 1,024 至 1,048,576。

分配到实际 DCU 后，复用前面两张图片，并去掉 `--preflight-only`、更换输出 JSON 文件名，即会先执行同样的 CPU 检查，再检查设备和 BF16 运算，使用 BF16 / SDPA / greedy 加载本地权重，顺序执行每张单图和前两张双图请求，默认每次最多生成 32 个 token。`--max-new-tokens` 可显式修改。GPU 模式不回退精度、设备或注意力实现；失败时在新 JSON 中保留阶段、错误与 traceback。

GPU 结果保存完整生成 token、包含特殊 token 的原始文本、解码答案、同步后的 `generate` 耗时和峰值分配/保留显存。耗时不包括加载、processor 和输入传输，没有预热；这些短请求仅是功能检查，不构成正式服务、官方精度通过或比赛性能结论。

### 缺少 torchvision 时的显式纯图像路径

本次平台 CPU 运行发现：默认 `AutoProcessor.from_pretrained` 在加载未使用的视频组件时要求 torchvision；失败报告已保留。直接给原始 `Qwen3VLProcessor` 传入 `video_processor=None` 也不能解决，因为 [4.57.6 ProcessorMixin](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/processing_utils.py) 根据 `attributes` 逐项加载和检查组件类型，原始 [Qwen3VLProcessor](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3_vl/processing_qwen3_vl.py) 声明了三个组件。

脚本新增可选的 `--image-only-processor`，仅支持本次核验过的 Transformers 4.57.6。它使用局部子类只声明图片 processor 和 tokenizer 两个组件，禁止视频，继承原始 Qwen3VL 图像处理和模板调用；显式选择 `AutoImageProcessor(use_fast=False)`，并保留原始默认的 `Qwen2TokenizerFast`。组件均从同一本地目录读取；模板仍走原始 `from_pretrained` / `get_processor_dict` 路径，并强制验证其内容与本地 `chat_template.jinja` 逐字一致，记录模板及 tokenizer、processor 配置哈希。默认路径保持 AutoProcessor，失败后不会自动切换。

使用已有的两张 fixture，选择新输出文件重跑：

```bash
python scripts/recon2reason_reference.py \
  --model /absolute/path/Recon2Reason-Reasoning-4B \
  --image /absolute/path/new-functional-fixtures/functional_fixture_1.png \
  --image /absolute/path/new-functional-fixtures/functional_fixture_2.png \
  --output /absolute/path/reference-image-only-cpu-002.json \
  --image-only-processor --preflight-only
```

此路径不安装 torchvision、不修改原生 Torch 或 Transformers 全局类；慢速与快速图片实现可能存在数值差异，不能将该功能检查视为精度等价证明。GPU 权重加载不使用 `device_map`，也不依赖 Accelerate 自动分发；该版本源码已忽略 `low_cpu_mem_usage`，脚本移除了这个无效参数，见 [4.57.6 模型加载实现](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/modeling_utils.py)。

### 显式选择 SDPA math 后端

首轮真实 GPU 报告 `evidence/reference-gpu-001.json` 记录设备 `BW`、单卡 68,702,699,520 字节显存、BF16 运算检查通过，权重加载用时 24.53 秒；生成阶段报错 `No matching libraries found for flash_attn_2_cuda*.so`。这说明当时原生 Torch 的 SDPA 自动分派进入了缺少对应动态库的路径，不能据此宣称单图问答已成功。

脚本新增 `--sdpa-backend {auto,math}`，默认仍为 `auto`。显式选择 `math` 时，只在 `generate` 调用周围使用 `torch.nn.attention.sdpa_kernel([SDPBackend.MATH])`，保留模型 BF16 参数、输入 dtype、Transformers `sdpa` 实现和 greedy 配置；退出后由上下文管理器恢复原有后端开关，没有失败重试或自动切换。API 依据 [PyTorch 2.9 sdpa_kernel 文档](https://docs.pytorch.org/docs/2.9/generated/torch.nn.attention.sdpa_kernel.html)、[SDPBackend 枚举](https://docs.pytorch.org/docs/2.9/generated/torch.nn.attention.SDPBackend.html) 和 [v2.9.0 实现](https://github.com/pytorch/pytorch/blob/v2.9.0/torch/nn/attention/__init__.py)。

下一轮 GPU 命令保留原有参数，增加 `--sdpa-backend math` 并选择新的 JSON 文件名。报告顶层保存脚本 SHA-256 和请求的后端，每个完成的生成 case 也保存后端选择。原始失败报告继续保留，用于区分自动分派失败与显式 math 实验；不同后端的数值和性能仍需分别验证，不能把功能结果当成完整框架的性能成绩。
