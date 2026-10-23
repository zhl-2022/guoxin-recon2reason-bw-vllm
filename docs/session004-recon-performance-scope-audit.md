# Recon Session004 性能口径独立补充审计

**结论：应同时保留“8/12 个模板负载格已实际执行”和“5/8 格通过额外可见正文检查”两个事实。不能把后者直接解释成三格未完成 1024-token 性能负载，或三格已被官方判定失败。** 模板未要求随机负载的解码正文非空；原生客户端也不以正文非空作为 success 条件。现有服务端原件还包含之前未纳入推断的 `request_params_max_tokens`，其 count/sum 与实际 generation histogram 完全相同，支持有条件的逐请求生成预算饱和推断。

本审计只新增本文及[独立观察记录](../evidence/session004/recon-performance-scope-audit-20261023/audit-observations.json)，不改 session004 冻结的 analyzer、八份 native JSONL、六份报告、fields、仓库或历史结果；没有 GPU 操作。`official_performance_accepted=false`、正式精度及最终提交状态均不变。以下“生成 token”指服务端计数的 token ID，不等同于可见文本字数或用户收到的流内容。

## 1. 审计发现

### 1.1 中等：正文非空是额外开发检查，不能充作官方性能门槛

[analyze_sglang_results_004.py](../scripts/analyze_sglang_results_004.py) 第 233–234 行对 `generated_texts` 中任意空字符串加入 issue，再由第 450 行决定 `eligible_client_report`。这一检查对发现响应异常有价值，但[官方模板](../国芯国模黑客松-技术报告模板.md)第 7 节只规定 SGLang 客户端、负载、两轮、请求数和原始性能字段，没有把随机生成的正文非空列为性能验收条件。模板第 5 节的功能 smoke 应与第 7 节随机压测分开。

所以旧 analyzer 的“5/8 严格合格”应准确命名为**五格通过附加正文健全性检查**。三格的空正文需要披露和调查，但仅凭空正文，不足以认定它们没有执行规定 token 计算负载。旧报告已经保留八格运行与原报数值；本审计补充限定其中“不合格”和“输出完整”的使用范围，不给出官方验收结论。

建议方向：后续可将“原生性能执行/结构与请求错误”“服务端生成预算核对”“可见正文健全性”“逐请求 SSE/usage 直接核验”分别记录。当前冻结文件保持原样，用本文作补充解释，避免把额外门槛反向写成官方规则。

### 1.2 中等：仅凭迟启 collector 否定所有逐请求推断，遗漏了同一完成集合的上界计数

[冻结报告](report-004-recon2reason-bw-vllm.md)第 102 行以 collector 迟启、没有零基线和逐请求隔离为由，只承认聚合一致性；这一保守说明没有利用原始 `/metrics` 第 276–277 行的 `request_params_max_tokens_count/sum`。

实际原件中，**完成请求的实际 token 总和与其请求上界总和同时为 590080，两个 count 同时为 584**。在已核的上游实现中，它们来自同一个 `finished_request` 循环。若每条生成数不超过自身上界，总缺口为零就能推出每条缺口为零，不需要以 collector 开始采样时刻作为零点。这个结论有明确源码适用假设，详见第 4 节；它仍不是逐请求 raw SSE/usage 的直接保存或验证。

### 1.3 中等：生成负载成立，不会让空正文的客户端 TTFT/ITL 自动变成可信的逐 token 延迟

十二条空文本的 native 记录全部是 `TTFT=0`、`ITL=[]`、`errors=""`。SGLang sender 的 TTFT 从第一个非空 content/reasoning 字符串开始，空内容保留初始零值；TPOT 又使用该 TTFT 参与计算。因此，这三格的原生吞吐、duration 和原报延迟应保留，但应明确其**可见内容延迟口径存在局限**，不能将零值解释为生成第一个 token 不耗时。

这也是需要保留空正文问题的具体原因，不能通过删除样本、重算“正确”延迟、把服务端 TTFT 直接替换客户端 TTFT 或补造 SSE 来消除。

## 2. 官方要求与实际客户端行为

[模板第 7 节](../国芯国模黑客松-技术报告模板.md)规定 4096/16384 输入、1024 输出、并发 1/8/64，各两轮，第二轮取数；每格请求数为并发的两倍且至少八个。本轮实际 driver 只选择并发 8/64 的四种组合，共八格。完整模板仍有 c1 四格未运行，不能将历史 session003 或其他服务生命周期的校准数据直接拼成这一轮完整矩阵。

本轮固定 SGLang 0.5.12 的 `bench_serving.py` 与实际 client identity 中的 SHA 一致：`129e40b9e361be192306a9df56df41507f0397d5768696db3a9b994421daa259`。原始源码见[本地快照](../evidence/session004/sglang-backend-004g-20261023/upstream-bench_serving.py)，对应[上游固定版本](https://github.com/sgl-project/sglang/blob/v0.5.12/python/sglang/bench_serving.py)。

- 第 398–416 行构造 chat 请求，`max_completion_tokens` 取输入行的 output length；本轮额外体明确 `ignore_eos=true`、`temperature=0`、`include_usage=true`。没有设置可覆盖上限的另一输出长度或 `n>1`。
- 第 429–430 行初始化空正文和请求长度；第 469–470 行收到 usage 时可更新 output length，没收到则可能保留请求长度 fallback。
- 第 479–504 行只在非空 reasoning/content 时累加正文和内容时间；HTTP 200 的流遍历结束后设置 success，**没有要求正文非空，也没有独立要求观察到 `[DONE]` 才置 success**。
- 第 1290 行把额外 warmup 的输出上限设为 `min(request.output_len, 32)`；每个已归档命令为 `--warmup-requests 1`，因此八次 warmup 上限各 32。

以上支持“八份原生客户端运行记录存在”，不能仅凭 `output_lens=1024` 证明 usage 实际收到；后面的服务端推断使用独立原件，而非把 fallback 改名为直接认证。

## 3. 八格、请求全集和服务生命周期核对

观察记录读取的远端原始输入均逐文件比对[最终 export manifest](../evidence/session004/remote-final-001/export-manifest.json)的大小/SHA；模板、现有 analyzer 与本地上游源码快照另记自身 SHA，不假称它们也是该远端包的 payload。本轮矩阵 run ID 为 `c2277b5d03b54683a5c7ba0193e5e55b`，API server PID 为 `3218`；客户端 before/after identity、collector identity 和 runtime config 相符。

| 轮次 | 文本目标 | 并发 | 原生 completed | errors 非空数 | 空正文数 | 附加正文检查 |
|---|---|---|---|---|---|---|
| 1 | 4096 | 8 | 16 | 0 | 0 | 通过 |
| 2 | 4096 | 8 | 16 | 0 | 0 | 通过 |
| 1 | 4096 | 64 | 128 | 0 | 0 | 通过 |
| 2 | 4096 | 64 | 128 | 0 | 0 | 通过 |
| 1 | 16384 | 8 | 16 | 0 | 0 | 通过 |
| 2 | 16384 | 8 | 16 | 0 | 1 | 有空正文，单独披露 |
| 1 | 16384 | 64 | 128 | 0 | 7 | 有空正文，单独披露 |
| 2 | 16384 | 64 | 128 | 0 | 4 | 有空正文，单独披露 |

八个 client 均退出 0 且回收完成；原生 completed 合计 **576**，`output_lens` 均为 1024，客户端原报输出合计 **589824**。这是原报事实，不单靠这些字段宣布逐请求长度直接认证。原始命令/JSONL 见[run.json](../evidence/session004/remote-final-001/project/evidence/session004/recon-sglang-matrix-A-001/run.json)。

按 [server.log](../evidence/session004/remote-final-001/project/tasks/recon2reason-bw-vllm/runtime/server.log) 的 run 分隔与 PID 统计：

- 旧 run `4ecf16914a374d5ca91cee3dd11bfe3a`、PID `424` 有五条 chat POST，属于先前功能检查，不能算入新服务。
- 新 run `c227...`、PID `3218` 从启动到关闭有 **584 条 POST `/v1/chat/completions`，全部 HTTP 200**，未见该生命周期其他 POST endpoint。
- 八个 pinned client 命令给出 576 个测量请求和八次 warmup，合计恰为 584；最后服务指标也恰有 584 个完成请求，运行和等待均为零。

这使**已记录的**命令、HTTP 请求数和服务完成数形成闭集对应。HTTP access log 不包含每条请求体或 client request ID，因此仍须明确“日志完整、固定客户端源码/命令确为该请求集”的通常取证假设，不能声称已经保存每条线上请求体。

## 4. 服务端 token 上界饱和的数学推断

### 4.1 原件比只看 generation counter 更完整

[metrics-last-good.txt](../evidence/session004/remote-final-001/project/evidence/session004/recon-server-metrics-001/metrics-last-good.txt) 保存：

| 字段 | 末次有效值 | 含义和限制 |
|---|---:|---|
| `generation_tokens_total` | 590080 | 服务 generation token ID 计数，不是可见字符数 |
| `request_generation_tokens_count/sum` | 584 / 590080 | 已完成请求实际生成量的 histogram |
| `request_params_max_tokens_count/sum` | 584 / 590080 | 同一完成请求循环记录的 max_tokens 参数 |
| `request_max_num_generation_tokens_count/sum` | 584 / 590080 | 另一个请求最大生成量分布，作为交叉支持 |
| `request_success_total{finished_reason="length"}` | 584 | 这里表示 length 类终止，不代表可见正文或官方验收通过 |
| `stop/abort/error/repetition` 对应完成数 | 全部 0 | `request_success` 这个名称并不排除其他 finish reason；本轮实际为零 |
| running / waiting | 0 / 0 | 末次取样时无运行/排队请求 |

三个相关 histogram 的 bucket 也相符：`≤50` 为 8，`≤1000` 仍为 8，`≤2000` 为 584。bucket 本身只给范围，不单独证明每条恰为 32/1024；精确值来自命令上界、配对总和及下面的推断。

指标 family 创建时间为 UTC `2026-10-23T10:43:24.290646`，对应新服务开始测量之前。collector 虽在最后一格期间才启动，但读到的是这个服务生命周期的累计指标；用于配对比较时，不必假定 collector 首次样本为零。

### 4.2 计数语义与证明

上游 vLLM v0.18.1 [stats.py](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/v1/metrics/stats.py) 第 341–355 行用 `len(output.new_token_ids)` 累加 generation tokens；[loggers.py](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/v1/metrics/loggers.py) 第 1143–1181 行在同一个 finished-request 循环中观察实际生成量，并在 max_tokens 非空时观察该请求上界。本轮两个 histogram 的 count 相同且均为全部 584 条完成请求。

对这同一组请求，设实际生成量为 $g_i$，请求上界为 $m_i$。在正常受限生成语义下：

$$
0 \le g_i \le m_i.
$$

原件给出：

$$
\sum_i g_i = 590080 = \sum_i m_i,
\qquad
\sum_i(m_i-g_i)=0.
$$

每项缺口非负，总和为零，故每条请求都有 $g_i=m_i$。结合已记录的请求全集：

$$
590080=576\times1024+8\times32.
$$

**因此，在下列源码/运行适用前提下，现有证据支持 576 个测量请求各生成 1024 token、八次额外 warmup 各生成 32 token 的服务端计数推断。** 这比单独看一个总生成 counter 更强；“collector 没有零基线”不足以否定这一配对饱和推断。

### 4.3 前提与不能提升的结论

1. 实际 native 版本是 `0.18.1+das.fa71803.dtk2604`；本审计取得的是 upstream v0.18.1 源码，未取得并 hash 实际安装 fork 的全部指标实现。假定 fork 保持这些指标的已核语义；原始 HELP、字段和值一致提供支持，但不是 native 源码逐字节比对。
2. 每请求实际输出不得超过其 max_tokens；本轮 engine log 的 `speculative_config=None` 与普通受限生成路径相符。[scheduler stop 检查](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/v1/core/sched/utils.py)含 max token 截断。若 fork 存在未见的计数/超限 bug，这一数学前提需要重新审查。
3. 逐请求数学结论作用于服务端完成集合；将其中 576 条对应到 benchmark，依赖第 3 节已记录的 HTTP/命令/完成计数闭合。未保存带请求 ID 的逐条 request/response body，所以不声称逐条网络负载独立认证。
4. 服务端生成 1024 个 token ID，**不等于客户端一定收到 1024 个可见文本 token、每次 usage 原文或正确 SSE `[DONE]`**。这些直接证据仍缺失。
5. 这不认证 4096/16384 是含图像/chat 包装后的精确总输入长度，不补 c1 缺档，不改变第二轮取数要求、正式 evaluator/baseline 缺项或官方验收状态。

## 5. 空正文的可能解释与未解决问题

SGLang sender 本轮未显式传 `skip_special_tokens`；vLLM v0.18.1 [chat protocol](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/entrypoints/openai/chat_completion/protocol.py)第 199 行默认 `skip_special_tokens=True`，并将该值传入 SamplingParams。[detokenizer](https://github.com/vllm-project/vllm/blob/v0.18.1/vllm/v1/engine/detokenizer.py)保留 token ID 计数，同时以此设置处理文本解码。因此，**有生成 token 而解码后可见正文为空，在协议层面并不矛盾**；尤其 `ignore_eos=true` 只控制生成停止行为，不要求将特殊 token 显示出来。

“这些请求可能反复生成被跳过的特殊 token”只是可解释假设，**目前不能定因**。没有 token ID/raw SSE，就不能排除其他解码、流分帧、native fork 或客户端处理问题；也不能宣称已证明模型只输出了 EOS。sender 已将 reasoning/content 合并，所以不能未经证据又简单归因为“思考字段没收”。

十二条的可见正文异常、零 TTFT 和空 ITL 仍应在报告限制中保留。原生吞吐/测量时长可作为八格实测原报呈现，同时披露延迟口径，不应因为附加检查一票否定整格 token 负载，也不应反向把所有延迟字段宣传成逐生成 token 的精确测量。

## 6. 后续对外表述建议

建议采用下面的分层表述，不修改冻结原件：

> 本轮真实执行了 8/12 个模板负载格，八个原生 SGLang client 均退出 0，576 个测量请求原报完成且 errors 为空；另有八次 32-token warmup。服务端完成数、实际生成量与请求上界 histogram 配对饱和，在已核实现语义与请求闭集前提下，支持测量请求各达到 1024-token 生成预算。五格通过额外可见正文检查，另三格共十二条可见正文为空，相关客户端 TTFT/ITL 存在口径限制，原因尚未确定。c1 四格未跑；逐请求 raw SSE/usage 和官方性能验收均未完成。

这种表述既不将内部额外检查升级为官方门槛，也不把服务端 token 计算量与用户可见输出质量混为一谈。旧 5/8 结果保留为历史严格检查结果，本文补充其作用域和新读取的服务端上界证据；最终是否接受这些性能材料由评审决定。

独立观察记录包括八格明细、十二条零基索引、实际 TTFT/ITL 值、HTTP inventory、服务端配对计数、输入 SHA 和源码适用假设。第一方源码原文及 SHA 保存在[本次补充审计目录](../evidence/session004/recon-performance-scope-audit-20261023/primary-source-manifest.json)，它们未被执行，也没有覆盖实际 GPU 环境中的 native 文件。
