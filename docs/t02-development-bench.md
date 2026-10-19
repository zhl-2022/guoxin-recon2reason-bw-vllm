# T02 开发压测驱动：vLLM 0.18.1 random-mm

本驱动是显式的开发测试工具，不是尚未取得的赛事正式 benchmark。默认只打印计划，不导入 Torch/vLLM、不联网、不创建文件；只有 `--run` 才调用本机 vLLM CLI。GPU 服务的启动、计费和停机由调用方单独管理。

## 已核实的官方接口

代码依据 vLLM 固定版本 [serve.py](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/benchmarks/serve.py) 与 [datasets.py](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/benchmarks/datasets.py)。国产镜像含厂商改动，实际执行前仍需保存本机 `vllm bench serve --help`，核对同名选项。

`random-mm` 要求 `openai-chat`，使用 `/v1/chat/completions`。本驱动让原生客户端构造文本和图片；不加 `--enable-multimodal-chat`，该转换不是 serve 的使用路径。图片数固定为 1、图片数范围比为 0，视频限制为 0；桶配置固定为 `(H,W,1)`。v0.18.1 的长度范围比为 0 时固定，旧模板的范围比 1 不适用于这里。

## 负载与边界

完整计划共 12 条命令，每档连续两轮，第二轮仅标作开发计分轮：

| 文本目标 | 输出目标 | 并发 | 每轮请求 | 两轮请求 |
|---|---|---|---|---|
| 4096 | 1024 | 1 | 8 | 16 |
| 4096 | 1024 | 8 | 16 | 32 |
| 4096 | 1024 | 64 | 128 | 256 |
| 16384 | 1024 | 1 | 8 | 16 |
| 16384 | 1024 | 8 | 16 | 32 |
| 16384 | 1024 | 64 | 128 | 256 |
| 合计 | | | 304 | 608 |

默认图片为明确的开发选择 **1024×1024**，不是已确认的赛事负载。原生 `random-mm` 的输入长度描述随机文本目标；图片与 chat template 的 token 另计，文本解码重编码也可能有误差。因此不能把该工具跑出的记录称为“服务器总输入精确等于 4096/16384”。第一档需结合服务端实际 usage/日志校准；在正式口径取得前保留这种差异。

客户端显式使用 greedy、ignore-EOS、输出目标 1024、seed=1、请求率 inf，并禁用额外 readiness/warmup 请求。两轮采用相同 seed；服务端前缀缓存等配置会影响第二轮，必须与实际服务配置一并记录。随机图片不用于质量评测。

## 用法

```bash
# 只读计划：本地模型路径不必已挂载；不产生任何结果文件。
python3 scripts/t02_development_bench.py \
  --model-path /实际模型目录 --served-model-name recon2reason-reasoning-4b \
  --output-dir /本轮全新结果目录

# 显式校准子集：只有第一档第一轮；不称完整矩阵。
python3 scripts/t02_development_bench.py \
  --model-path /实际模型目录 --served-model-name recon2reason-reasoning-4b \
  --output-dir /全新校准目录 --load 4096:1 --round 1 --run

# 完整六档两轮。需服务已启动且生命周期足够长。
python3 scripts/t02_development_bench.py \
  --model-path /实际模型目录 --served-model-name recon2reason-reasoning-4b \
  --port 30000 --image-size 1024 --timeout-seconds 1800 \
  --total-timeout-seconds 7200 --output-dir /全新完整结果目录 --run
```

RoboBrain 可改为对应模型路径、服务名与端口 30001。实际运行要求模型和 tokenizer 是本地目录，避免请求远程模型下载。`--host` 仅接受数值 loopback 地址，拒绝外部地址和域名；客户端环境中的 HTTP 代理会移除。

默认调用 `vllm bench serve`。如原生 CLI 位于特定环境，使用 `--vllm-command-json '["/实际环境/bin/vllm"]'`。这是显式 argv 前缀，不经 shell eval，也不允许另加参数改变固定负载。CPU 测试通过此接口换成临时 mock，不运行模型。

## 原始产物与失败

`--run` 拒绝已存在的输出目录，保护旧日志。新目录包含：

- `run.json`：计划、每条命令、状态、退出码、起止时间、客户端 wall time、日志/结果哈希和实际 vLLM 版本/源码哈希。
- `native/roundN_INPUT_1024_cCONCURRENCY.json`：vLLM 原生 JSON，启用 `--save-detailed` 保留逐请求错误与响应；驱动不改其内容。
- 十二份同名 `.log`：各条客户端 stdout/stderr；失败、超时同样保留。
- `round1.jsonl`、`round2.jsonl`：每档状态和提取的原生指标，失败行不删除。
- `summary.md`：两轮全部档位的状态、请求完成数、原生 duration、吞吐、TTFT、TPOT、E2EL 和客户端 wall time；完整细节保存在原生 JSON 与两轮 JSONL 中。

只有命令退出 0、原生 JSON 显示 completed 等于目标请求数且 failed=0，单档才标为 `complete`。缺结果、部分失败、无效 JSON、超时、启动失败分别记录；单档失败默认继续后续档位。总时限或中断后未尝试的档位仍列出，不删掉。Linux 清理独立客户端进程组；它不停止另行启动的模型服务。

`official_acceptance` 始终为 false；`full_matrix=false` 明确标识校准子集。工具不会从成功运行推导正式成绩、精度或可提交状态。

## CPU 验证

```bash
python3 -B -m unittest discover -s tests -p test_t02_development_bench.py -v
```

测试使用临时 mock CLI，覆盖 12 档计数、608 请求、纯计划无副作用、loopback 限制、不覆盖旧目录、失败保留、部分请求失败、超时与总时限和显式校准子集。正式 GPU 负载需另行保存真实环境与运行证据。

本轮 Windows 与 WSL 各实际执行 8 项 CPU 测试，均通过；未调用实际 vLLM、未启动模型或 GPU。
