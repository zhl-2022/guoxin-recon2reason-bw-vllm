# RoboBrain 与 ASR 本轮执行 Runbook

用途：主代理在已授权的 BW 单卡会话中执行新的开发验证。所有结果属于开发证据，`official_accuracy=false`、`official_performance=false`；不提交比赛。以下命令由主代理执行，本文件作者没有启动 GPU 或操作平台。

## 1. 共用前提

- 先确认上一模型已经停止、占用已释放。Robo 数值检查与服务、ASR 服务顺序使用同一卡；不同端口不能保证显存足够同时运行。
- 以下默认工程根为 `/root/private_data/guoxin-hackathon-20261019-vllm`；若主代理本轮使用另一个干净工程目录，只更改 `PROJECT`。保留 `scripts/`、`tasks/`、`fixtures/` 的相对布局。
- 同步当前源码与相关小型样本。Robo 核心兼容 SHA256 必须是 `083dc53f3e4f8171b774469bffa724c2269a9d289769f56a9d7a5624cd81659f`；validator 必须是 `ba6a94283fa63418948c466eac7fc8949a56cf244eb6f9c3be8dcd78ef673dd1`。
- 新报告路径不得已有。失败记录保留，重试使用新目录；不要覆盖历史 GPU 数值、heldout 或 ASR 日志。
- 监督器停止不等于 Notebook 停止计费。平台定时关机与最终关机由主代理另外执行。

## 2. Robo：24 项数值与七个图片请求

最短正确流程是：确认空卡 → 数值检查 → 启动默认兼容服务 → 七个不同尺寸图片请求 → 停止服务。数值脚本不加载模型，但会实际使用 GPU；不能与另一个模型同时执行。

```bash
(
set -euo pipefail
PROJECT=/root/private_data/guoxin-hackathon-20261019-vllm
cd "$PROJECT"
RUN="$PROJECT/evidence/robo-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN"
unset VLLM_PLUGINS
export PYTHONPATH="$PROJECT/scripts${PYTHONPATH:+:$PYTHONPATH}"

/usr/bin/python3 -B scripts/validate_robobrain_vision_math_compat.py \
  --max-length 2049 --output "$RUN/numerical.json" \
  > "$RUN/numerical-driver.log" 2>&1

export ROBOBRAIN_PYTHON_BIN=/usr/bin/python3
export ROBOBRAIN_PROFILE_WIDTH=1024 ROBOBRAIN_PROFILE_HEIGHT=1024
export ROBOBRAIN_MAX_NUM_SEQS=4
export ROBOBRAIN_LOAD_TIMEOUT=600 ROBOBRAIN_MAX_RUNTIME_SECONDS=900
trap 'bash "$PROJECT/tasks/robobrain-bw-vllm/stop.sh" > "$RUN/stop.log" 2>&1 || true' EXIT
bash tasks/robobrain-bw-vllm/run.sh > "$RUN/start.log" 2>&1
/usr/bin/python3 -B scripts/robobrain_heldout_fixtures.py \
  --output-dir "$RUN/heldout" \
  --base-url http://127.0.0.1:30001 --model robobrain2-5-8b-nv \
  --timeout 120 --run > "$RUN/heldout-driver.log" 2>&1
)
```

验读 `numerical.json` 的 `gpu_numerical_verified=true`、全部 24 case 的 `passed=true`、实际候选 SHA 及设备；新增六项广播 case 应各记录六个实际 SDPA 分块，并满足 3752 个 score 元素预算。不能拿历史 `cc6591...` 的 18 项报告顶替。

七个请求是红方块和蓝圆各自 general/grounding/pointing，以及双图比较。功能检查为非空、正确完成的响应；另外读取合成框 IoU、点落框和原始描述。它们没有真实轨迹/深度标注，也不是官方精度集。1024×1024 是已测试初始化 profiling bound，尚不能保证所有大图负载。

如要顺带重跑通用七项（含 SSE）可在上述停止前增加：

```bash
bash tasks/robobrain-bw-vllm/smoke.sh \
  --image "$RUN/heldout/heldout_red_square.png" \
  --image "$RUN/heldout/heldout_blue_circle.png" \
  --log "$RUN/generic-smoke.jsonl"
```

## 3. ASR：新 venv 与三个发布方来源 WAV

本轮样本来源已固定在 `fixtures/asr/publisher-qwen-20261020/manifest.json`。中文原件是 16 kHz PCM16，4.2039375 秒；英文原件是 **48 kHz PCM24**，15.0512291667 秒、2,172,458 字节。原版英文不能直接发送给现有严格 16 kHz PCM16 客户端；`--long-audio` 只放宽时长和文件大小，不负责格式转换。

`prepare_asr_development_fixtures.py --build` 用 CPU 显式生成中文等价 WAV、英文重采样 WAV，以及中文/英文/中文/英文之间插入 0.25 秒静音的约 39.26 秒拼接 WAV，记录变换及哈希。后者不是自然连续长录音。三个参考文本目前均为 null；不能擅自计算 WER/CER。

Windows 本机生成尝试因既有 NumPy 2.2.6 与 SciPy 二进制不兼容而失败，目标目录未创建，未安装或改动包。应在原生镜像的已锁定 NumPy 1.25.0 / SciPy 1.15.3 环境或其新 venv 中生成。该准备脚本不导入 Torch、不使用 GPU。若目标目录已经存在，应先核对 manifest 和实际文件哈希，不重复 `--build` 或覆盖。

新 venv 的 CPU 准备可在模型切换前独立完成；只安装已审核的七个缺失 wheel，保留原生框架包。下面的 venv 目录必须尚不存在；已经成功准备时改用 `prepare.sh --check-existing "$VENV"`，不要重新覆盖安装。

```bash
PROJECT=/root/private_data/guoxin-hackathon-20261019-vllm
cd "$PROJECT"
VENV="$PROJECT/tasks/qwen3-asr-bw-vllm/runtime/audio-venv-20261020"
SCNET_BASE_PYTHON=/usr/bin/python3 bash tasks/qwen3-asr-bw-vllm/prepare.sh \
  --venv "$VENV" --apply
export QWEN_ASR_PYTHON_BIN="$VENV/bin/python"
"$QWEN_ASR_PYTHON_BIN" -B scripts/prepare_asr_development_fixtures.py --build
```

真实服务与三条音频请求：

```bash
(
set -euo pipefail
PROJECT=/root/private_data/guoxin-hackathon-20261019-vllm
cd "$PROJECT"
export QWEN_ASR_PYTHON_BIN="$PROJECT/tasks/qwen3-asr-bw-vllm/runtime/audio-venv-20261020/bin/python"
export QWEN_ASR_LOAD_TIMEOUT=600 QWEN_ASR_MAX_RUNTIME_SECONDS=900
RUN="$PROJECT/evidence/asr-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN"
trap 'bash "$PROJECT/tasks/qwen3-asr-bw-vllm/stop.sh" > "$RUN/stop.log" 2>&1 || true' EXIT
bash tasks/qwen3-asr-bw-vllm/run.sh > "$RUN/start.log" 2>&1
bash tasks/qwen3-asr-bw-vllm/smoke.sh \
  --audio fixtures/asr/development-20261020/zh_16000_pcm16.wav \
  --log "$RUN/zh.jsonl" > "$RUN/zh-driver.log" 2>&1
bash tasks/qwen3-asr-bw-vllm/smoke.sh \
  --audio fixtures/asr/development-20261020/en_16000_pcm16.wav \
  --log "$RUN/en.jsonl" > "$RUN/en-driver.log" 2>&1
bash tasks/qwen3-asr-bw-vllm/smoke.sh \
  --audio fixtures/asr/development-20261020/zh_en_repeated_39s.wav --long-audio \
  --log "$RUN/long.jsonl" > "$RUN/long-driver.log" 2>&1

# SSE 输出诊断：上传完整中文 WAV 后读取增量转写。
/usr/bin/python3 -B scripts/qwen3_asr_stream_smoke.py \
  --audio fixtures/asr/development-20261020/zh_16000_pcm16.wav \
  --base-url http://127.0.0.1:30002 --model qwen3-asr-1.7b \
  --timeout 120 --run --log "$RUN/zh-stream.jsonl" \
  > "$RUN/zh-stream-driver.log" 2>&1
)
```

`run.sh` 会再次检查实际 venv，并设置 `VLLM_PLUGINS=hcu,qwen_asr_tf55_compat` 和项目内插件路径。无需激活 venv，也不要安装 `qwen-asr[vllm]` 或升级 native Torch/Transformers/vLLM。若 `--apply` 或检查失败，应保留 `asr-prepare-evidence/` 并处理具体错误，不能切到未经审核的通用 pip 安装。

非流式响应目前未必返回 finish reason，现有 smoke 不宣称已排除截断。除原始转写外还要保存 audio manifest、服务/停止状态和完整原生日志，供后来正确性核对。

## 4. 流式能力的准确范围

[vLLM v0.18.1 SpeechToText](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/entrypoints/openai/speech_to_text/speech_to_text.py) 提供 `stream=true`，按 `transcription.chunk`/choices/delta 格式输出 SSE、finish reason 和 `[DONE]`。该源码明确说 Qwen 的 `language ...<asr_text>` 前缀尚需缓冲去除，新的客户端会保留原始前缀，避免擅自改写输出。

新增 [qwen3_asr_stream_smoke.py](../scripts/qwen3_asr_stream_smoke.py) 默认只打印本地计划，不写文件、不联网；显式 `--run --log 新文件` 才请求 loopback。它拒绝错误事件、缺失 DONE、缺失/非 stop 终止原因、空文本、超限及错误模型，保留流式事件和原始增量文本。Windows 和 WSL 各 8 项 CPU 测试通过，包含真实 loopback HTTP mock；实际 BW 镜像的 SSE 支持仍需本轮运行确认。

**这里验证的是整段音频上传后的流式输出，不是分块实时音频输入。**Qwen SDK 的 streaming state 或 WebSocket realtime 路径未在当前原生镜像完成适配；不可把一次 SSE 成功写成完整实时 ASR 验收。客户端计时也只是开发观察，不是正式音频性能/RTF。

脚本 SHA256 为 `20df684b5c82ea8eb1ecb002ca12adc23c236d94d5e7ab089c434153d7114edf`。以上命令仅准备与获取开发证据，不生成官方 PASS，不触发比赛提交。
