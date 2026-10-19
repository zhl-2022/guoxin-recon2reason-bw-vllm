# vLLM 0.18 HCU 的 Qwen3-VL 启动依据

核查日期：2026-10-19。范围限定为 Recon2Reason 的 Qwen3-VL 架构、HCU/DAS 0.18 附近的文本/视觉 attention 与预处理兼容性。本文没有安装组件、改代码或运行远端服务。

## 当前可用结论

HYGON-AI 官方 cookbook 存在 Qwen3-VL-4B / BW1000、BW1100 / 单卡的 0.18 配方，且普通版与 hotfix 的后端选择方式不同。当前私有镜像已完成真实探针：[vllm-probe-001.json](../evidence/vllm-probe-001.json) 中四项隔离导入全部通过，HCU 平台插件已激活，设备为单卡 BW / `gfx936:sramecc+:xnack-`。当前 HCU 打包接口与 cookbook 中的开关名称不同，本轮采用原生默认后端，不添加未经本机源码确认的 cookbook 开关。

服务的语言解码 attention 和视觉编码器 attention 是两条选择链。显式指定解码后端不保证同时更换视觉内核；视觉选择 `TORCH_SDPA` 也不等于强制 PyTorch math。此前 Transformers 自动 SDPA 缺少 `flash_attn_2_cuda*.so` 的失败需要保留，不能直接推断完整 vLLM 镜像具有相同缺失。

## 官方 HCU 配方的版本边界

固定依据为 HYGON-AI cookbook 提交 `0a5aa29b5720c36d2e033e220834edfe7ed6a6ce` 的 [Qwen3-VL 文档](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/vllm/qwen3-vl.md)。其中 4B Instruct 配置为：

| 硬件与版本 | 官方配方中出现的开关 | attention CLI | 当前用途 |
|---|---|---|---|
| BW1000 / BW1100，普通 0.18，1 卡 | `VLLM_HCU_USE_PD_SPLIT=1`；`VLLM_HCU_USE_CUSTOM_FLASH_ATTN=1` | 未显式指定 | 当前打包源码未确认这些变量，不用于本轮 |
| BW1000，0.18-hotfix，1 卡 | `VLLM_HCU_USE_PD_SPLIT=1` | `FLASH_ATTN_CUSTOM` | 仅确认 hotfix 及参数支持后采用 |
| BW1100，0.18-hotfix，1 卡 | 同上 | `FLASH_ATTN_CUSTOM`，另含 FP8 KV | 当前 BF16 初始验收不照搬 FP8 KV |
| K100_AI，普通/hotfix 0.18，1 卡 | `VLLM_HCU_USE_CUSTOM_OPS=0`；`VLLM_HCU_USE_CUSTOM_QUANTIZATION_GEMM=0` | 未显式指定 | 不能把另一硬件的关闭优化配方直接套到 BW |

示例中的 `VLLM_USE_MODELSCOPE=1` 用于模型来源；本任务使用已挂载本地模型目录时无需为它切换下载源。官方通用示例包含 `--trust-remote-code`，但 Recon2Reason 使用标准架构；不需要因此引入远程模型代码。

`VLLM_HCU_USE_PD_SPLIT` 的名字不能证明需要创建两个服务；官方上述条目本身标注单卡 IFB。本次 probe 已读取当前 HCU 的 `platforms/envs.py` 和 `platforms/hcu.py`，符号清单中未出现它和 `VLLM_HCU_USE_CUSTOM_FLASH_ATTN`，而是存在 `VLLM_HCU_USE_FLASH_ATTN`。这是当前打包分支与该 cookbook 配方接口不同的直接证据；没有取得对应 cookbook 构建的完整实现，不能把变量改名后假定语义相同。

同一 cookbook 的 [镜像表](https://github.com/HYGON-AI/inference-cookbook-das/blob/0a5aa29b5720c36d2e033e220834edfe7ed6a6ce/docs/model-deployment/docker_images.md) 列出普通 `vllm:0.18.1-ubuntu22.04-dtk26.04-py3.10` 及独立的 `custom:vllm0.18.1-hotfix-ubuntu22.04-dtk2604-py3.10`，两者不能仅凭大版本合并处理。

### 官方 0.18.1 镜像的只读元数据参照

本次仅获取官方注册表的 manifest 和 config，没有下载镜像层。

| 项目 | 2026-10-19 观察值 |
|---|---|
| 镜像 | `harbor.sourcefind.cn:5443/hcu/admin/base/vllm:0.18.1-ubuntu22.04-dtk26.04-py3.10` |
| Manifest digest | `sha256:164afad43171dd431f0344d9808e42777ccfd1af2264e2409a8326ca4da509f4` |
| Config digest | `sha256:60acc1e53e735fed09e701b40cf7a74ac74c3e22bc7ed9b9f0572820445220f2` |
| 创建时间 | `2026-06-22T01:18:48.330034903Z` |
| 构建记录 | 指定 Torch 2.10.0、vLLM/vLLM-HCU 0.18.1、Transformers 5.5.0、Triton 3.6.0 |
| 算子记录 | 安装过原生索引提供的 flash-attn、lightop、aiter 等；完整本地构建后缀须运行时核实 |

一手端点：[Manifest](https://harbor.sourcefind.cn:5443/v2/hcu/admin/base/vllm/manifests/0.18.1-ubuntu22.04-dtk26.04-py3.10)、[Config](https://harbor.sourcefind.cn:5443/v2/hcu/admin/base/vllm/blobs/sha256:60acc1e53e735fed09e701b40cf7a74ac74c3e22bc7ed9b9f0572820445220f2)。

当前私有 Jupyter 镜像名称带有 2026-04-23，创建页曾称 Torch 2.9，但实际包元数据为原生 Torch 2.10。实际采集优先于镜像说明。当前构建与上述 6 月官方镜像的 digest 等价性没有证据，不能仅因主版本相同就混用开关或升级组件。

| 当前私有镜像组件 | 已采集版本 |
|---|---|
| Python / executable | `3.10.12` / `/usr/bin/python3` |
| Torch | `2.10.0+das.opt1.dtk2604.20260325.g6b060a` |
| torchvision | `0.25.0+das.opt1.dtk2604.torch2100.20260325.g860505` |
| Transformers | `5.5.0` |
| vLLM | `0.18.1+das.fa71803.dtk2604` |
| vLLM-HCU | `0.18.1+das.dtk2604` |
| Triton | `3.6.0+gitc73250c4.staging` |
| FlashAttention | `2.8.3+das.opt1.dtk2604.torch2100.20260330.g3f0061` |
| LightOp | `0.6.0+das.dtk2604.torch2100.2604101656.g193111` |
| AITER | `0.1.2+das.opt1.dtk2604.torch2100.2604212021.gd52133` |

完整版本来自 distribution metadata；部分模块的 `__version__` 只显示主版本，不能据此误判为通用 PyPI 构建。probe 记录 `torch`、`torchvision`、`flash_attn`、`vllm` 均从 `/usr/local/lib/python3.10/dist-packages/` 导入，原生 HIP 版本为 `6.3.26093`。导入通过证明了这一层兼容性，仍不能代替 attention 内核真实执行、服务健康与多模态请求验证。

## 视觉后端的可核查代码链

下列是上游固定 `v0.18.0` 的代码证据，用于解释参数和定位问题；HCU 下游可能覆盖它们，不能替代本地源码检查。

| 代码位置 | 已证实行为 | 对启动的意义 |
|---|---|---|
| [arg_utils.py](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/engine/arg_utils.py) | 声明 `--mm-encoder-attn-backend`、`--mm-processor-kwargs`、`--limit-mm-per-prompt` | 本机帮助也需存在，才可使用 |
| [vision.py](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/model_executor/models/vision.py) | `get_vit_attn_backend` 读取 multimodal 配置并调用平台选择器 | 视觉 override 独立于普通语言 attention 参数 |
| [rocm.py](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/platforms/rocm.py) | 支持视觉 `FLASH_ATTN`、`ROCM_AITER_FA`、`TRITON_ATTN`、`TORCH_SDPA`；自动选择依赖芯片和可用包 | 不仅取决于是否安装了一个包名 |
| [mm_encoder_attention.py](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/model_executor/layers/attention/mm_encoder_attention.py) | 多模态编码器按所选后端分派不同 forward | 应读取启动日志实际选用了什么 |
| [vit_attn_wrappers.py](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/v1/attention/ops/vit_attn_wrappers.py) | Torch 路径直接调用 `F.scaled_dot_product_attention`；Triton 路径调用 prefill 内核 | `TORCH_SDPA` 仍可触发原生 Torch 的二次分派；Triton 需要匹配编译器与设备 |

该上游 ROCm 自动选择器优先考虑可用的 AITER/Flash 路径，条件不满足时可选择 Torch SDPA。当前真实平台是 `vllm_hcu.platforms.hcu.HCUPlatform`，其 `device_type="cuda"`、`device_name="hip"`、`dispatch_key="CUDA"`；这些接口名不表示正在使用 NVIDIA。应优先解释当前 HCU 下游的实现，而不能把通用 ROCm 自动选择顺序直接当成本轮行为。

实际 probe 中可定位的源码证据如下，远端路径前缀为 `/usr/local/lib/python3.10/dist-packages/`，对应片段保存在同一 JSON：

| 当前打包源码位置 | 已确认信息 | 不能据此推出的结论 |
|---|---|---|
| `vllm_hcu/platforms/envs.py:8`、`:39`、`:40`；`platforms/hcu.py:82` | 存在 `VLLM_HCU_USE_FLASH_ATTN` 声明/读取与平台引用 | probe 未采集该变量值和完整条件，不能断言当前启用状态 |
| `vllm_hcu/platforms/hcu.py:94`、`:95` | `TRITON_ATTN` 注册为 `HcuTritonAttentionBackend` | 不证明自动选择一定落到此后端 |
| `vllm_hcu/platforms/hcu.py:243`、`:244`、`:248`、`:270` | 视觉支持列表包含 Triton、Torch SDPA；HCU 有自己的视觉选择方法，存在 Torch SDPA 返回路径 | 片段不包含完整条件，不能断言当前 vision 默认选了哪一项 |
| `vllm/model_executor/models/vision.py:115` | 视觉选择读取 `mm_encoder_attn_backend` | 不等同于普通解码后端选项 |
| `vllm/model_executor/layers/attention/mm_encoder_attention.py:401`、`:407` | 对 Triton 和 Torch SDPA 分派不同 forward | 导入成功不证明所有 forward 的内核都已运行 |

probe 定向读取范围中未发现适用于本构建的 `VLLM_HCU_*VISION*` / `VLLM_HCU_*VIT*` 专用变量，也未见上述 PD_SPLIT / CUSTOM_FLASH_ATTN 名称。此结论限于已读取的文件，不扩张为对整个包所有代码的排除证明。

随后真实 [启动日志](../evidence/vllm-server-start-001.log) 在 22:33:35 明确记录视觉 `MMEncoderAttention` 使用 `TORCH_SDPA`。权重加载后，`vit_attn_wrappers.py:202` 的原生 SDPA 又报告采用新的 FlashAttention 接口。这两条日志兼容：vLLM 选择 Torch SDPA 这一层，随后原生 Torch 再选择底层执行实现。完整镜像已能继续执行并完成图像请求，此前简化环境缺少 FlashAttention 动态库的错误不能继续套用到本镜像。

同一时刻 `activation.py:643` 记录原生 ROCm 栈把 GELU 的 `tanh` 近似改为 `approximate="none"`。这是框架自己的数值兼容行为，未修改模型权重或 BF16 参数精度；但激活函数计算方式确有变化，不能仅凭生成文本正常就宣称与发布方的精度基线完全一致。[上游 v0.18.1 activation.py](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/model_executor/layers/activation.py) 也包含 ROCm 对 GELU tanh 路径的兼容处理。当前下游实现和日志应一并保留，正式精度复现时记录此偏差、使用指定数据与解码配置评测，不静默修改 GELU 或强制全局 attention 后端。

上游 [Qwen3-VL 模型实现](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/model_executor/models/qwen3_vl.py) 使用自己的模型执行与视觉路径，并导入 Transformers 的快速 image/video processor。此前功能参考脚本的纯图像 processor 扩展不应被当成 vLLM 服务补丁。当前完整镜像已通过 torchvision 导入，服务实际加载原生 processor 与模型仍由启动过程验证。

## 实例可访问后的最小只读检查

此阶段已由 [scnet_vllm_probe.py](../scripts/scnet_vllm_probe.py) 执行，结果为 `completed`，全部隔离导入及 `api_server --help` 通过。下面保留最小元数据复核命令，用于后续换镜像时对照，不安装组件：

```bash
python - <<'PY'
import importlib.metadata as m
import sys
for name in ("torch", "torchvision", "transformers", "vllm", "vllm-hcu", "triton", "flash-attn", "lightop", "aiter"):
    try:
        print(name, m.version(name))
    except m.PackageNotFoundError:
        print(name, "MISSING")
print("python", sys.version, sys.executable)
for name in ("vllm", "vllm-hcu"):
    try:
        print(name, "distribution root", m.distribution(name).locate_file(""))
    except m.PackageNotFoundError:
        pass
PY
```

本轮已读取明确列出的非密钥开关、完整包版本、模块路径、平台类型和 CLI 帮助；已采集开关均未设置。注意 probe 的变量白名单不包含本次从源码发现的 `VLLM_HCU_USE_FLASH_ATTN`，因此不能用该白名单报告判断它的值。后续如需诊断，只在已确定的包目录继续定向查找：

```text
VLLM_HCU_USE_PD_SPLIT
VLLM_HCU_USE_CUSTOM_FLASH_ATTN
VLLM_HCU_USE_FLASH_ATTN
FLASH_ATTN_CUSTOM
mm_encoder_attn_backend
get_vit_attn_backend
MMEncoderAttention
VLLM_HCU.*(VISION|VIT|FLASH)
```

本轮四项隔离导入已全部通过，CLI 已确认存在 attention、vision attention、eager、图像数量、processor kwargs、dtype、TP、上下文、并发和显存比例参数。帮助没有列出 `FLASH_ATTN_CUSTOM`、`TORCH_SDPA`、`TRITON_ATTN` 值，不能把名称未出现误判为参数值不受支持；具体值仍以当前枚举和平台实现为准。

## 启动参数采用边界

本轮选择当前 HCU 插件原生默认后端，不显式设置 PD_SPLIT、CUSTOM_FLASH_ATTN 或新发现但未核实完整行为的 FLASH_ATTN 开关；保持 TP=1、本地模型和 BF16。已选择 eager、`max-num-seqs=4`、`limit-mm-per-prompt={"image":2,"video":0}`、显存比例 0.85、上下文 32,768。它们是本轮受控启动配置，不是官方吞吐成绩；实际视觉后端已由日志确认，语言侧后端仍不应由视觉日志推断。

| 候选项 | 采用前提或限制 |
|---|---|
| `--mm-encoder-attn-backend TORCH_SDPA` | 本机 CLI/下游源码确实支持；不能保证避开缺失的 flash 动态库 |
| `--mm-encoder-attn-backend TRITON_ATTN` | 本机平台声明支持且原生 Triton 编译器、设备架构及内核测试通过；不是通用安全回退 |
| `--enforce-eager` | 可用于减少图/编译变量；不会替代 attention kernel 或修复 ABI |
| `--limit-mm-per-prompt` | 限制本次图片/视频数量，避免初始化按大量视频进行 profiling；不是删除 processor 依赖 |
| `--mm-processor-kwargs` | 只根据当前模型配置限定像素；不要改变 tokenizer、chat template 或模型架构 |
| `--skip-mm-profiling` | 初始验收不采用；它转移多模态峰值内存估算责任，可能隐藏真实启动问题 |

以下内容在本次证据下不能默认设置：把新版本的 `VLLM_USE_V2_MODEL_RUNNER` / KV layout 搬到旧镜像；把 K100 的关闭优化开关整体复制到 BW；使用 FP8 权重或 KV；强制 NVIDIA FlashInfer；把 PyTorch 的 Python 上下文当成会跨 vLLM worker 生效的全局设置；为修复扩展错误升级通用 PyPI Torch、torchvision、FlashAttention 或 Triton。

本轮 [状态快照](../evidence/vllm-state-001.json) 显示服务于上海时间 22:33:59 达到 ready；[功能检查](../evidence/vllm-smoke-001.jsonl) 的健康、模型列表、单图、双图、多轮首问/追问和图像流式输出七项全部通过，并显式记录 `official_accuracy=false`。该状态快照只说明当时状态，不能证明服务之后仍在运行。正式成绩仍需固定模型、预处理、生成参数和指定评测数据；GELU 数值兼容行为也必须纳入记录。
