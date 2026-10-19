# ASR 离线开发评分与下一轮准备

## 当前可用范围

`scripts/asr_development_eval.py` 仅处理用户明确提供的本地 JSONL、参考文本、预测文本和可选短 WAV。它不请求服务、不加载模型、不检测 GPU、不下载数据，也不安装依赖。评分结果固定带 `scope=development_only`、`official_evaluation=false` 和 `threshold_applied=false`，不会生成官方 baseline 或验收 PASS。

本轮新增工具的 CPU 测试与既有 GPU 转写证据分别保留。2026-10-19 的两条合成音仍只能证明短音频功能；新增工具不把这些证据升级成正式准确率。

## 输入格式与完整性

参考和预测均为 UTF-8 JSONL，每行必须恰好包含字符串 `id` 和 `text`：

```jsonl
{"id":"sample-en-001","text":"A local development sample."}
{"id":"sample-zh-001","text":"这是本地开发样本。"}
```

两份文件必须具有完全相同的样本 ID 集，文件顺序可以不同。拒绝缺失、额外或重复 ID、空白 ID、空或纯空白参考、非字符串文本、未知字段、重复 JSON key、NaN/Infinity、空行、BOM 和非法 UTF-8。预测文本可以为空，这将计入删除错误，不能通过丢弃失败样本提高分数。HTTP 事件日志不是预测 JSONL；必须先人工确认实际转写字段、运行与样本对应关系，再显式整理成上述格式。

可选 manifest 也是 JSONL，每行必须恰好包含 `id`、`audio`、`sha256`。`sha256` 为实际文件的 64 位小写十六进制 SHA256；不能使用示例占位值作为证据。`audio` 只允许本地路径，拒绝 URL 和 UNC 网络位置。相对路径按 manifest 所在目录解释。manifest 的 ID 集也必须与参考完全一致。

输入单文件最多 16 MiB、最多 10,000 条记录，单文本最多 16,384 个 Unicode code point。单条 DP 矩阵最多 4,000,000 个字符或词对、整批最多 50,000,000 个词与字符对；超过时明确拒绝，不自动截断、抽样或分割。它适用于有意选择的小规模开发检查，大规模正式评测应使用指定官方工具。

## 原始 WER/CER 策略

[NIST 的 WER 定义](https://trec.nist.gov/pubs/trec9/sdrt9_slides/tsld017.htm) 使用替换、删除和插入数量之和除以参考词数；[NIST OpenASR21 论文 §2.4](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=934557) 同时说明 CER 将对应单位改为字符。这里只据此实现透明的开发编辑距离，没有声称复现 SCTK 的全部对齐、特殊符号或赛事配置。

本工具只接受显式命名的 `identity` 规范化：

| 项目 | 实际处理 |
|---|---|
| 文本规范化 | 不改写原文，不去标点、不替换数字、不转大小写、不做繁简转换或 Unicode NFC/NFKC |
| WER token | Python `str.split()` 按 Unicode 空白划词；连续空白作为词边界，未做中文分词 |
| CER token | 原文 Unicode code point；保留空格、换行、标点、组合字符；不是字节，也不是可视 grapheme |
| 对齐代价 | 插入、删除、替换各 1；相同 token 代价 0 |
| 最短路径并列 | 固定优先 diagonal、deletion、insertion；错误总数相同的 S/D/I 划分可能与其他工具不同 |
| 聚合 | 逐样本统计 S/D/I，再以整批错误数除以整批参考单位数；不是各样本错误率的简单平均 |
| 数值单位 | `error_rate` 为比例，乘 100 才是百分数；允许大于 1，不裁剪到 100% |

例如，无空格的中文句子在此 WER 中通常只有一个 token，改一个字就可能得到 WER=1；应同时查看 CER，不能称它为官方中文分词结果。`é` 和 `e` 加组合重音也不会被暗中合并。参考有空格而预测没有空格时，CER 会计算这些差异。

报告保留两输入文件的原始字节 SHA256、大小和记录数，以及逐样本参考/预测文本 SHA256、S/D/I/C、参考单位数和错误率。默认不把原始参考或转写文本写进报告。程序退出 0 只说明文件校验与离线计算完成，不表示精度达标。

## 本地用法

仓库根目录执行，不需要音频依赖或模型：

```bash
python scripts/asr_development_eval.py score \
  --references /本地/reference.jsonl \
  --predictions /本地/prediction.jsonl \
  --normalization identity \
  --output /本地/新的development-score.json
```

有 manifest 时加 `--manifest /本地/manifest.jsonl`，只检查其 schema、哈希格式及 ID 完整对应，不会打开音频。输出文件必须尚不存在，工具不会建父目录或覆盖历史结果；坏输入不产生半份结果。

manifest 子命令默认只读 JSONL 并打印计划，不打开音频。只有 `--check-audio` 才读取列出的本地 WAV：

```bash
python scripts/asr_development_eval.py manifest --manifest /本地/manifest.jsonl
python scripts/asr_development_eval.py manifest --manifest /本地/manifest.jsonl --check-audio
```

显式音频检查复用现有短 WAV smoke 的边界：单声道、16 kHz、PCM16、时长大于 0 且不超过 30 秒、文件不超过 2 MiB，检查实际 SHA256 和声明帧数是否完整。不重采样、不裁剪；这是本地客户端范围，不是模型最大音频长度，也不是 T04 官方上限。超过 30 秒的长音频需要单独的明确测试路径，不能为了通过而偷偷分割后仍当作整段结果。

## 下一轮小样本来源与待办

| 用途 | 已核查主来源 | 范围与状态 |
|---|---|---|
| 中英单文件功能 | Qwen 原作者的 [中文 WAV](https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_zh.wav)、[英文 WAV](https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-ASR-Repo/asr_en.wav)，被 [固定 revision 示例](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_asr_vllm.py) 引用 | 本轮未下载；需实际检查编码、时长、出处和转写，不能仅因来自官方示例就称自然录音或标准评测集 |
| 少量真人朗读 | [Google FLEURS 数据卡](https://huggingface.co/datasets/google/fleurs) | 原作者提供 read speech，支持 `streaming=True` 逐样本读取，并列出 16 kHz 音频及 raw_transcription / transcription；应固定 revision、配置、split、原始 ID、样本选择与文本字段；保留 CC-BY-4.0 归属 |
| 单条 FLEURS 下载入口 | HF datasets-server 的 en_us、cmn_hans_cn test `/rows` 请求 | 2026-10-20 本轮元数据请求均返回 HTTP 500，不能当成已可用下载链；未下载音频。逐样本 streaming 也是待实际验证方案，不能在原生框架中临时安装 datasets/codec 链 |
| 长输入与流式 | [Qwen 固定 revision 流式示例](https://github.com/QwenLM/Qwen3-ASR/blob/7c6daf77a2421100f5fb066495372c00129d39ff/examples/example_qwen3_asr_vllm_streaming.py) | SDK 分块示例不自动证明当前 native HTTP `/audio/transcriptions` 具有同样流式协议；需单独核对接口。若先拼接短样本检查长度，必须标记人工拼接功能输入，不能称自然连续长录音 |

优先用中英原作者单文件确认非本地 TTS 的接口表现；若要做自然语音开发评分，再在独立数据准备环境取固定 FLEURS 的极小子集，明确选择 `raw_transcription` 或已有规范化的 `transcription`，不能混用后同模型卡数值比较。参考文本只留在本地评分文件，不放进推理请求。大语料和官方固定集尚未下载。

正式 T04 音频清单、对应 GPU baseline、原版判分器、文本规范化、解码配置、流式范围和性能计分口径仍缺；本工具不能填补这些材料。最终赛事提交仍按用户后续通知执行。
