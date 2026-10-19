# 三题独立代码仓库的本地组装

## 目标与当前状态

`scripts/prepare_task_repositories.py` 为下列三个目标生成可以独立保存、检查并后续初始化 Git 的源树：

| 独立源树 slug | 唯一目标 |
|---|---|
| `recon2reason-bw-vllm` | Recon2Reason-Reasoning-4B × BW × vLLM × BF16 |
| `robobrain-bw-vllm` | RoboBrain2.5-8B-NV × BW × vLLM × BF16 |
| `qwen3-asr-bw-vllm` | Qwen3-ASR-1.7B × BW × vLLM × BF16 |

每棵树的根 `README.md` 是目标题当前八章报告，根 `ROOT_TASK.json` 明确唯一目标和开发状态。源代码保留 `scripts/`、`src/`、`tests/`、`docs/` 与三个小型 canonical task 目录，以支持共享实现、交叉引用和已有测试；另外两题仅是共享开发依赖，不作为该仓库的提交目标。

工具只组装本地目录。它不初始化 Git、不 commit、不创建远端仓库、不 push、不调用服务或模型、不分配 GPU、不安装依赖，也不执行赛事提交。仓库 URL 默认为 `null`，不会猜光合地址；完整镜像地址只沿用已有 task 配置中的真实值，未知时仍为空。`formal_ready=false`、`submitted=false` 保持明确，不能把目录组装成功解释为评测通过。

## 先计划，再显式构建

默认只读取文件并打印计划，不创建输出目录：

```bash
python scripts/prepare_task_repositories.py
python scripts/prepare_task_repositories.py --task recon2reason-bw-vllm
```

检查 `missing_required_files` 为空、来源和大小符合预期后，再显式构建：

```bash
python scripts/prepare_task_repositories.py --build
```

默认输出父目录为当前源树的 `dist/repositories`。也可用 `--output-root /新的绝对父目录`，并通过重复 `--task` 只选择部分题。目标目录必须尚不存在；工具会先检查所有选中的最终目录，任何一件已存在就整体拒绝，不覆盖、清空或自动改名。重新出快照时指定一个新的输出父目录即可。

构建读取当前文件内容，原始来源保留。正式评测或 GPU 证据更新后，应再次计划并生成新的快照，而不是把旧快照当成实时状态。发生写盘异常时保留不完整的新目录供检查，工具不自动递归删除或覆盖后重试。

## 每件包含什么

- `README.md`：目标题报告的拷贝；将正文中的本地 Markdown 链接改为根目录可读路径，保留代码 fence 内的命令原文。canonical 原报告仍保留在 `tasks/<slug>/README.md`。
- 根 `env.sh`、`run.sh`、`smoke.sh`、`verify.sh`、`bench.sh`、`stop.sh` 等 wrapper：转发到该目标的 canonical 入口。ASR 的 `prepare.sh`、RoboBrain 的对照入口也随本题转发；没有复制共享运行实现。
- `ROOT_TASK.json`：模型、赛道、canonical task/报告、源 task 状态、空或真实镜像引用和未正式就绪/未提交状态。
- 三题任务小目录、共享 Python/Bash/PowerShell 源码、已有测试、文档、`pyproject.toml` 和 `.gitignore`。
- `.gitattributes`：固定 `* -text`，避免外部 `core.autocrlf` 在 Git checkout 时改变历史证据哈希或 shell 换行；工具仍不执行任何 Git 命令。
- 三题 `evidence_files` 的实际文件，以及被 Markdown 明确引用的本地证据、文档和 fixtures；历史日志保持文件名和字节，不把失败改成通过。通用 fixtures 作为小规模开发输入一并保留。
- `repository-manifest.json`：除 manifest 自身外，所有交付文件的相对路径、字节数和 SHA256；包含总字节数、唯一目标和未提交状态。CLI 另打印 manifest 自身 SHA256。

正式材料缺失时只报告缺项，不制造 baseline、样本、评测脚本、镜像地址或报告空壳。源码和证据快照每件最多 50 MiB，manifest 自身不计入源码计数。

## 来源和敏感内容保护

文件来源限当前源树；task 证据路径必须是显式仓库相对路径，拒绝绝对路径和 `..`。Markdown 中允许指向当前源树内的正常相对上级路径，但解析后必须仍在源树内；追加依赖只能来自 `evidence/`、`docs/`、`fixtures/`，或已经收集的共享源码。

不跟随 symlink；源文件、源根、输出父路径上的 symlink 和 Windows reparse point 均拒绝。排除 `.git`、`dist`、`runtime`、venv、缓存、模型目录，不包含权重或官方材料占位目录。敏感后缀及常见凭据文件名会直接报错；对文本还检查私钥头与常见硬编码凭据模式。它是打包前防误收措施，不替代发布前人工检查；账号、密码、登录 token 不应出现在源码或证据中。

## 独立目录验证

生成目录后，可进行不需要 GPU 的检查：

```bash
cd /输出父目录/recon2reason-bw-vllm
python -B -m unittest discover -s tests -p test_asr_task_prepare.py
bash run.sh --dry-run
```

ASR 的根 `prepare.sh --dry-run` 仍是纯本地计划。不要把 `env_check.sh` 当作无 GPU 的参数检查，它会检查目标运行环境；实际服务、环境准备、GPU 验证和最终提交应遵循另行授权与预算。

新增测试覆盖默认无写入、真实独立树中的 Python 检查与 Bash 参数展开、逐文件 SHA256、正文链接重定位且代码 fence 不变、输出不可覆盖、缺文件、路径穿越、symlink、敏感文件和大小拒绝。根代理负责在所有开发与运行结果更新后构建最终快照，并另行处理三个实际远端代码仓库；赛事提交等待用户通知。
