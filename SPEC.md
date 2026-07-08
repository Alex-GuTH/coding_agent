# Safe Test-Repair Coding Harness SPEC

## 1. 项目概述

Safe Test-Repair Coding Harness 是一个面向 Python 小项目的 coding agent harness。它通过自己实现的 agent 主循环，把可替换的 LLM 决策层、受控工具执行、代码级治理护栏、pytest 反馈分析和运行记忆组合成一个可测试的软件系统。

本项目的核心目标不是构建一个通用大型 coding agent，而是构建一个范围清晰、机制可证明的 harness：它能在受控工作目录中读取代码、写入受控文件修改、运行测试、解析失败反馈，并在多轮循环中根据确定性反馈改变下一步动作。

本项目选择 A 类 Coding Agent Harness。项目交付的 harness 内核必须由本项目代码实现，不能依赖 LangChain AgentExecutor、AutoGen、CrewAI、LlamaIndex agent 或宿主编码智能体自带的 agent runner。

## 2. 问题陈述

LLM 能生成代码，但单独的 LLM 不等于可靠的 coding agent。真实软件开发需要确定性的工程机制：动作边界、危险操作拦截、测试反馈、失败分类、状态记录、凭据保护和可重复分发。

本项目要解决的问题是：如何把一个“只会提出下一步动作”的 LLM 包装成一个可测试、可治理、可分发的 Python test-repair harness。

目标用户包括：

- 想研究 coding agent harness 机制的学生或开发者；
- 想观察 LLM 如何在测试反馈下修复 Python 小项目的使用者；
- 想用 mock LLM 离线验证 agent loop、guardrail、feedback loop 的课程评审者；
- 想在安全边界内手动体验真实 LLM provider 的开发者。

项目值得做的原因是：它把课程要求中的“Agent = LLM + Harness”落到可执行、可测试的工程系统中，并能用 mock LLM 确定性证明核心机制存在于代码里，而不是藏在 prompt 里。

## 3. 用户故事

1. 作为课程评审者，我希望在不配置真实 LLM key 的情况下运行 mock demo，从而确定 harness 的核心机制能离线复现。
2. 作为开发者，我希望给 harness 一个 Python demo 项目和任务描述，让它运行 pytest、观察失败、执行修复，并在测试通过时停止。
3. 作为安全审查者，我希望当 LLM 提出越界写文件、删除文件或执行危险 shell 命令时，harness 用代码级 guardrail 拦截动作。
4. 作为调试者，我希望每次 agent run 都保存 action trace、工具结果、反馈分类和停止原因，以便复盘 agent 为什么这样做。
5. 作为真实 LLM 使用者，我希望可以选择配置真实 provider，但在没有 key 时 mock 测试和 CI 仍然完全可运行。
6. 作为部署者，我希望可以通过 Python 包/CLI 或 Docker 镜像运行项目，并通过 README 理解 key 配置、安全边界和已知限制。
7. 作为课程助教，我希望看到 GitHub Actions 在每次 push 后自动运行测试并通过，同时看到最终交付物中包含 `.gitlab-ci.yml`，且其中有名为 `unit-test` 的 job，并能访问一个最小 WebUI 查看 mock 机制演示 trace。

## 4. 领域与机制设计

### 4.1 动作 / 工具

本项目的 agent 不能直接执行自然语言命令。LLM 必须输出结构化 JSON action，Action Parser 校验后交给 Tool Dispatcher。

MVP 必须支持的动作如下：

- `read_file`：读取工作目录内的文本文件。
- `write_file`：写入或覆盖工作目录内的文本文件。
- `list_files`：列出工作目录内符合规则的文件。
- `run_tests`：运行配置指定的测试命令，默认 `python -m pytest`。
- `run_shell`：执行白名单 shell 命令。默认只允许测试相关命令，不允许任意 shell。
- `request_approval`：当动作需要人工确认时进入等待状态。
- `finish`：声明任务完成或无法继续。

扩展动作：

- `apply_patch`：对工作目录内文件应用受限补丁。该动作是 post-MVP 扩展，不作为核心验收前提；如果实现，必须经过与 `write_file` 相同的 guardrail、规模限制和 mock 测试。

MVP 不要求实现 `apply_patch`。MVP 中如果收到 `apply_patch` action，应返回 `unsupported_action` observation，并由 Agent Loop 回灌给下一轮。`PLAN.md` 不应把 `apply_patch` 排为核心验收 task。

所有工具动作执行前都必须经过 guardrail 检查。工具执行结果必须作为结构化 observation 回灌给 agent loop。

### 4.2 客观反馈信号

反馈信号由确定性代码产生，而不是由 LLM 自行判断。

主要反馈来源是 `run_tests` 的结果：

- 进程退出码；
- stdout/stderr；
- pytest 失败摘要；
- 超时状态；
- 是否收集到测试；
- 失败分类。

Feedback Analyzer 将测试输出分类为：

- `tests_passed`
- `assertion_failure`
- `syntax_error`
- `import_error`
- `missing_file`
- `timeout`
- `command_error`
- `no_tests_collected`
- `unknown_failure`

分类结果会作为下一轮 LLM 上下文的一部分。mock LLM 测试必须证明：当第一轮收到某类失败反馈时，第二轮会选择不同动作。

### 4.3 危险动作

危险动作必须由代码级 Guardrail Engine 拦截，而不是靠 prompt 提醒。

默认危险动作包括：

- 访问 workspace 之外的路径；
- 使用绝对路径写文件；
- 写入 `.env`、密钥文件、Git 内部文件或 CI 凭据文件；
- 删除文件或目录；
- 大范围覆盖文件；
- 执行 `rm`、`del`、`format`、`shutdown`、`curl | sh`、`sudo`、包发布、Git push、部署命令等危险 shell；
- 执行未在配置白名单中的 shell 命令；
- 尝试读取常见凭据位置。

Guardrail Engine 的输出为：

- `allowed`：动作可执行；
- `blocked`：动作被拒绝并回灌原因；
- `approval_required`：动作暂停，等待人工确认；
- `invalid`：动作格式、路径或参数不合法。

### 4.4 记忆需求

本项目的记忆不是长期向量记忆，而是轻量、可测试、可审计的运行记忆。

记忆存储内容：

- 当前任务描述；
- harness 配置快照；
- 每轮 LLM action；
- 每个工具 observation；
- guardrail 决策；
- pytest 反馈分类；
- 已读文件列表；
- 已修改文件列表；
- 当前停止原因；
- 可选的用户批准记录。

记忆存储方式：

- MVP 使用 JSONL run log；
- 每一行是一个结构化事件；
- run log 存在 workspace 内的受控目录或 harness 自己的 run 目录；
- 不保存真实 API key；
- 不保存完整敏感环境变量。

检索方式：

- Agent Loop 每轮按确定性规则选择上下文；
- 默认注入任务描述、最近 N 条事件、最近一次测试反馈、已修改文件摘要；
- 不把完整 run log 全量塞给 LLM；
- 当 run log 过长时，保留最近事件和最新测试反馈。

### 4.5 主贡献维度

本项目主贡献是反馈闭环，而不是 UI、真实 LLM 调用或复杂记忆。

反馈闭环的工程深度体现在：

- pytest 输出由代码解析；
- 失败由代码分类；
- 分类结果被结构化回灌；
- agent loop 根据反馈进入下一轮；
- stop policy 根据测试通过、连续失败、最大轮次、危险拦截等状态停机；
- mock LLM 单元测试能确定性复现失败注入和修复行为。

### 4.6 支撑机制

治理护栏是本项目的第二重点。它不追求覆盖所有安全问题，但必须能确定性展示：

- 越界路径被拦截；
- 危险 shell 被拦截；
- 未授权写入被拦截；
- 需要人工确认的动作进入暂停状态。

### 4.7 机制实现矩阵

| 机制 | 代码模块 | 不是 prompt 的原因 | mock/stub 测试方式 |
| --- | --- | --- | --- |
| 决策封装 | Agent Loop、LLM Provider、Action Parser、StopPolicy | 循环、动作解析和停机判断由本项目代码控制，LLM 只返回候选 action | 用 MockLLMProvider 脚本驱动多轮 action，断言状态迁移和停机原因 |
| 工具分发 | Tool Dispatcher、Tools、ProcessRunner | action 到工具的映射、参数校验、进程执行都由代码完成 | 构造 ParsedAction，使用 fake ProcessRunner 或临时 workspace 断言 observation |
| 反馈闭环 | Feedback Analyzer、Agent Loop、Run Log | pytest 输出由确定性规则分类，分类结果由代码写入下一轮上下文 | 固定 pytest 输出样本 + mock LLM repair-loop 测试 |
| 治理护栏 | Guardrail Engine | 危险路径、危险命令、敏感文件由代码规则拦截 | 直接构造危险 action，断言 blocked/approval_required |
| 记忆 | Memory / Run Log、Context Selector | 存储、脱敏、检索窗口由代码规则决定，不依赖 LLM 记忆 | 临时 JSONL run log，断言最近事件、反馈和脱敏结果 |
| 配置 | Config Loader、HarnessConfig | 配置 schema、默认值、危险配置拒绝由代码校验 | 临时 TOML 文件，断言合并、覆盖、拒绝危险配置 |
| 凭据 | Credential Manager | key 存储、状态查看、清除和脱敏由代码路径处理 | fake keyring/stub secret store，断言不回显明文、不写 run log |

## 5. 功能规约

### 5.1 Agent Loop

输入：

- 用户任务描述；
- workspace 路径；
- harness 配置；
- LLM provider；
- 当前 run log；
- 最大轮次限制。

行为：

1. 初始化 run 状态。
2. 组装上下文，包括任务、配置摘要、最近 observation 和最近反馈。
3. 调用 LLM provider 获取候选 action。
4. 使用 Action Parser 校验 action。
5. 使用 Guardrail Engine 检查 action。
6. 对允许动作调用 Tool Dispatcher。
7. 将工具结果、反馈分析结果和 guardrail 决策写入 run log。
8. 调用 StopPolicy 判断是否停止，否则进入下一轮。

输出：

- 最终 run status；
- action trace；
- 最后一次测试结果；
- 停止原因；
- run log 路径。

边界条件：

- LLM 输出非法 JSON；
- LLM 输出未知 action；
- 工具执行超时；
- 连续多轮无进展；
- 达到最大轮次；
- 测试命令不存在；
- workspace 不存在或不可读。

错误处理：

- 非法 action 转为 `parser_error` observation，并可回灌给下一轮；
- guardrail 拦截转为 `guardrail_blocked` observation；
- 工具异常转为 `tool_error` observation；
- 达到最大轮次时返回 `max_iterations_reached`；
- 测试通过时返回 `success`。

### 5.2 LLM Provider 抽象层

输入：

- 结构化上下文对象；
- provider 配置；
- 可选凭据引用。

行为：

- 暴露统一接口 `generate_action(context)`；
- 返回 JSON action 字符串或结构化 action；
- provider 不直接执行工具；
- provider 不绕过 guardrail。

输出：

- LLM 原始响应；
- 候选 action；
- provider 元数据，如 provider 名称、模型名、mock 脚本步骤。

边界条件：

- mock 脚本耗尽；
- 真实 LLM 无 key；
- 真实 LLM 网络失败；
- 真实 LLM 返回非 JSON；
- provider 超时。

错误处理：

- mock 脚本耗尽时返回 `finish` 或 provider error；
- 缺少真实 LLM key 时提示配置 key，但不影响 mock 测试；
- 网络失败转为 provider error；
- 非 JSON 响应交给 Action Parser 产生解析错误。

mock LLM 支持：

- `MockLLMProvider` 接收一个动作脚本；
- 脚本可以按轮次返回 action；
- 脚本也可以根据上一轮 feedback type 返回不同 action；
- 所有 mock 行为确定性，不联网、不依赖真实 key。

真实 LLM 支持：

- 真实 provider 是可选手动运行路径；
- MVP 提供 OpenAI-compatible HTTP provider 接口和手动运行入口；
- 真实 provider 只调用单次补全/响应 API；
- 单元测试、CI、机制演示均不得依赖真实 provider；
- 不使用现成 agent runner。

### 5.3 Action Parser

输入：

- LLM 原始响应；
- action schema。

行为：

- 解析 JSON；
- 校验 `type` 字段；
- 校验 action 所需参数；
- 拒绝自由文本命令；
- 标准化路径和命令字段。

输出：

- `ParsedAction`；
- 或 `ActionParseError`。

边界条件：

- 空响应；
- 非 JSON；
- JSON 字段缺失；
- 未知 action type；
- 参数类型错误；
- 路径为空或包含不可接受字符。

错误处理：

- 返回结构化解析错误；
- 错误写入 run log；
- 错误可作为下一轮反馈回灌。
- invalid JSON、缺少 action `type`、参数类型错误返回结构化 parse error；
- unknown action 和 MVP 阶段的 `apply_patch` 返回 non-executable `unsupported_action` result，不进入工具执行；
- parse error 与 `unsupported_action` 都必须可序列化写入 run log，并可作为下一轮上下文反馈。

### 5.4 Tool Dispatcher

输入：

- 已解析 action；
- guardrail 允许结果；
- workspace；
- process runner；
- timeout 配置。

行为：

- 将 action 派发到具体工具；
- 捕获工具执行结果；
- 将 stdout/stderr、文件结果或异常包装为 observation。
- 对需要启动子进程的工具，只通过 ProcessRunner 执行，不直接拼接 shell 字符串。
- 防御式处理 `unsupported_action` observation：不得执行任何文件、shell 或测试操作。

输出：

- `ToolObservation`；
- 可能附带 `FeedbackReport`。

边界条件：

- 文件不存在；
- 文件不是文本；
- 文件过大；
- 命令超时；
- 命令退出码非 0；
- patch 无法应用。

错误处理：

- 读取失败返回 `file_read_error`；
- 写入失败返回 `file_write_error`；
- 命令失败返回 `command_error`；
- patch 失败返回 `patch_error`；
- 所有错误都不得直接崩溃 agent loop。

### 5.5 `read_file`

输入：

- workspace 内相对路径；
- 可选最大读取字节数。

行为：

- 校验路径在 workspace 内；
- 读取文本文件；
- 文件过大时截断并标记。

输出：

- 文件内容；
- 文件大小；
- 是否截断。

边界条件：

- 文件不存在；
- 路径越界；
- 二进制文件；
- 读取权限不足。

错误处理：

- 返回结构化错误 observation；
- 不泄露 workspace 外路径内容。

### 5.6 `write_file`

输入：

- workspace 内相对路径；
- 新文件内容；
- 写入模式。

行为：

- 经过 guardrail 检查；
- 写入文本文件；
- 记录写入前后的摘要。

输出：

- 写入成功状态；
- 影响文件路径；
- 内容长度；
- 可选 diff 摘要。

边界条件：

- 路径越界；
- 写入敏感文件；
- 内容过大；
- 覆盖已有文件；
- 父目录不存在。

错误处理：

- 越界和敏感路径由 guardrail 拦截；
- I/O 失败返回 `file_write_error`；
- 默认不自动创建过深目录，除非配置允许。

### 5.7 `apply_patch` 扩展动作

输入：

- patch 内容；
- workspace。

行为：

- post-MVP 阶段实现；MVP 可拒绝该动作并返回 `unsupported_action`；
- 解析 patch；
- 检查受影响文件；
- 检查新增、删除、修改规模；
- 应用补丁。

输出：

- 应用状态；
- 修改文件列表；
- diff 摘要。

边界条件：

- patch 格式错误；
- patch 冲突；
- 删除文件；
- 修改文件过多；
- 修改敏感路径。

错误处理：

- 格式错误返回 `patch_parse_error`；
- 冲突返回 `patch_apply_error`；
- 删除或敏感路径由 guardrail 拦截。

### 5.8 ProcessRunner

输入：

- argv 形式的命令参数；
- workspace；
- timeout；
- 环境变量 allowlist；
- 输出截断限制。

行为：

- 只接受已经通过 Guardrail Engine 的命令；
- 使用 argv 列表执行进程，默认不使用 `shell=True`；
- 固定工作目录为 workspace；
- 捕获 exit code、stdout、stderr、duration、timeout 状态；
- 为单元测试提供 fake/stub 实现，避免测试依赖真实进程。

输出：

- `ProcessResult`。

边界条件：

- 命令不存在；
- 进程超时；
- 输出过大；
- 工作目录不存在；
- 进程返回非 0。

错误处理：

- 命令不存在返回 `command_not_found`；
- 超时返回 `timeout`；
- 输出过大时截断并标记；
- 不把完整环境变量写入 observation。

### 5.9 `run_shell`

输入：

- argv 形式的 shell 命令；
- timeout；
- workspace。

行为：

- 只执行配置白名单允许的命令；
- 白名单按精确 argv 或 argv 前缀匹配；
- 禁止管道、重定向、命令连接符和 shell expansion；
- 默认不使用 `shell=True`；
- 默认工作目录为 workspace；
- 捕获退出码、stdout、stderr、耗时。

输出：

- exit code；
- stdout；
- stderr；
- timed out；
- duration。

边界条件：

- 命令不在白名单；
- 命令超时；
- 命令不存在；
- 输出过大。

错误处理：

- 非白名单命令由 guardrail 返回 blocked；
- 超时返回 `timeout`；
- 输出过大时截断并标记。

### 5.10 `run_tests`

输入：

- test command，默认 `python -m pytest`；
- timeout；
- workspace。

行为：

- 作为受控 ProcessRunner 命令运行；
- 捕获 pytest 输出；
- 调用 Feedback Analyzer。

输出：

- 命令结果；
- `FeedbackReport`。

边界条件：

- pytest 未安装；
- 无测试被收集；
- 测试超时；
- Python 语法错误；
- import 失败；
- 测试失败。

错误处理：

- pytest 未安装归为 `command_error`；
- 超时归为 `timeout`；
- 无测试归为 `no_tests_collected`；
- 未识别输出归为 `unknown_failure`。

### 5.11 Feedback Analyzer

输入：

- exit code；
- stdout；
- stderr；
- timeout 状态；
- 测试命令元数据。

行为：

- 使用确定性规则解析 pytest 输出；
- 识别失败类别；
- 提取最小有用摘要；
- 生成面向下一轮的结构化反馈。

输出：

- feedback type；
- summary；
- failing test names；
- error location；
- raw output excerpt；
- passed flag。

边界条件：

- 输出为空；
- 输出被截断；
- pytest 格式变化；
- 多种失败同时出现；
- 非 pytest 命令输出。

错误处理：

- 无法分类时返回 `unknown_failure`；
- 保留输出摘要供 LLM 参考；
- 不抛出未处理异常。

### 5.12 StopPolicy

输入：

- 当前 run 状态；
- 最新 action；
- 最新 guardrail decision；
- 最新 tool observation；
- 最新 feedback report；
- 最大轮次；
- 连续失败阈值。

行为：

- 根据确定性规则判断 agent 是否停止；
- 将停机原因写入 run log；
- 不询问 LLM 是否真的完成，LLM 的 `finish` 只是候选信号，仍需结合状态判断。

输出：

- `StopDecision`，包含 `should_stop`、`reason_code`、`success`、`message`、`metadata`。

边界条件：

- LLM 过早返回 `finish` 但测试未通过；
- guardrail blocked；
- 达到最大轮次；
- 连续同类失败；
- 测试通过；
- provider error。

错误处理：

- 测试通过时返回 `success`；
- 达到最大轮次时返回 `max_iterations_reached`；
- 危险动作被阻塞且不可恢复时返回 `blocked_by_guardrail`；
- LLM finish 但缺少客观成功信号时返回 `incomplete_finish` 或继续要求测试。

### 5.13 Guardrail Engine

输入：

- parsed action；
- workspace；
- 配置规则；
- 当前 run 状态。

行为：

- 路径规范化；
- 判断路径是否越界；
- 检查敏感文件规则；
- 检查 shell 白名单；
- 检查写入规模；
- 判断是否 allowed、blocked 或 approval required。

输出：

- guardrail decision；
- reason code；
- human-readable reason；
- 是否需要人工确认。

边界条件：

- 路径包含 `..`；
- Windows/Unix 路径差异；
- 符号链接；
- 大小写敏感差异；
- 命令通过 shell trick 绕过规则。

错误处理：

- 无法安全判定时默认 blocked；
- 符号链接默认不跟随或按解析后路径检查；
- 未知 action 默认 invalid。
- `approval_required` 只由配置显式声明的高风险动作或明确的规模阈值触发；
- 无法安全判定时默认 `blocked`，不得随意降级为 `approval_required`。

### 5.14 Memory / Run Log

输入：

- run events；
- action；
- observation；
- feedback；
- guardrail decision。

行为：

- 以 JSONL 追加写入事件；
- 提供按最近 N 条、最近反馈、文件摘要的检索；
- 为 WebUI 和 CLI 提供 trace。
- JSONL 每行必须是可 round-trip 的 JSON object；
- 字段顺序不具有语义意义；
- 测试应断言 JSON 结构和关键字段，不依赖文本字段顺序。

输出：

- run log 文件；
- run summary；
- context slice。

边界条件：

- run log 写入失败；
- run log 过大；
- JSONL 文件损坏；
- 包含敏感字段。

错误处理：

- 写入失败时返回 run warning；
- 读取损坏日志时跳过坏行并记录 warning；
- 对 key、token、环境变量值做禁止写入或脱敏；
- 如果 path、command、stdout/stderr 摘要中疑似包含 secret，应脱敏或截断。

### 5.15 Config

输入：

- TOML 项目级配置文件；
- CLI 参数；
- 环境变量；
- 默认值。

行为：

- 合并配置；
- 校验配置；
- 为 agent loop、guardrail、tools、provider 提供约束。

输出：

- `HarnessConfig`。

配置项包括：

- workspace；
- provider 类型：mock 或 real；
- mock script；
- model 名称；
- max iterations；
- test command；
- command allowlist；
- write allowlist；
- blocked path patterns；
- patch size limit；
- timeout；
- run log path；
- approval mode。

边界条件：

- 配置文件不存在；
- 配置格式错误；
- CLI 参数覆盖配置；
- 配置允许危险命令。

错误处理：

- 格式错误时启动失败并给出配置位置；
- 危险配置需要显式确认或直接拒绝；
- 未配置 provider 时默认 mock。

### 5.16 Credential Manager

输入：

- provider 名称；
- 用户录入的 key；
- credential command，如 status、set、clear。

行为：

- 首选操作系统安全存储；
- 可选 `.env` 作为开发模式来源；
- Docker 和 Render 部署环境使用平台 secret 或环境变量注入真实 provider key；
- 查看状态时只显示是否存在，不回显明文；
- 支持更新和清除 key。

输出：

- key 存储状态；
- provider 可用性状态。

边界条件：

- 系统 keyring 不可用；
- Docker 容器内无系统 keyring；
- `.env` 文件存在；
- key 为空；
- 用户误把 key 放进配置文件。

错误处理：

- keyring 不可用时提示使用 `.env` 开发模式，并说明明文风险；
- 禁止把 key 写入 run log；
- README 明确 `.env` 必须加入 `.gitignore`。
- 单元测试使用 fake keyring/stub secret store，不读写用户真实系统 keyring。

### 5.17 CLI

输入：

- 命令行参数；
- 配置文件路径；
- workspace；
- task。

行为：

- 提供运行、demo、配置、凭据管理命令；
- 将 agent run 的结果打印为简洁摘要；
- 支持输出 JSON trace。

输出：

- 终端摘要；
- run log；
- exit code。

命令示例：

- `safe-repair run --workspace ./demo_project --task "Fix failing tests"`
- `safe-repair demo repair-loop`
- `safe-repair demo guardrail`
- `safe-repair demo feedback-classifier`
- `safe-repair credentials status`
- `safe-repair credentials set`
- `safe-repair credentials clear`

边界条件：

- 参数缺失；
- workspace 不存在；
- demo 项目缺失；
- 配置无效。

错误处理：

- CLI 返回非 0 exit code；
- 错误信息指向具体配置或参数；
- 不打印敏感值。

### 5.18 WebUI

输入：

- 用户选择 demo 类型；
- 可选 mock run 参数。

行为：

- 启动一个最小 Web 服务；
- 运行内置 mock demo；
- 展示 action trace、feedback classification、guardrail decision、final status。

输出：

- 可访问 Web 页面；
- demo run trace；
- health endpoint。

边界条件：

- 多用户同时访问；
- demo 运行失败；
- 部署环境无写权限；
- 页面刷新导致重复运行。

错误处理：

- WebUI 只运行内置 demo，不允许任意上传代码执行；
- demo 失败时展示错误 trace；
- health endpoint 不依赖真实 LLM。

## 6. 非功能性需求

### 6.1 安全

- 默认不执行任意 shell；
- 默认只允许 workspace 内路径；
- 默认不调用真实 LLM；
- 不在日志中保存 key；
- 不在 CI 中需要真实 key；
- 不读取 `.env` 内容到 run log；
- Docker 镜像运行时需要用户显式挂载 workspace。

凭据威胁模型：

- 攻击者可能通过配置文件、日志、终端输出、Git 历史、Docker 环境变量泄露 key；
- LLM 可能尝试读取敏感路径；
- LLM 可能尝试把 key 写入日志或文件；
- 用户可能误把 `.env` 提交到仓库。

对策：

- key 首选 OS keyring；
- `.env` 仅作为开发模式，并在 README 标明风险；
- credential status 不回显明文；
- run log 禁止敏感字段；
- guardrail 阻止读取和写入常见凭据路径；
- `.gitignore` 包含 `.env` 和本地 run artifacts。

### 6.2 可测试性

- 所有核心机制必须能在 mock LLM 下测试；
- CI 测试不依赖网络；
- 真实 LLM provider 的测试使用 stub，不调用真实 API；
- demo 脚本可重复运行。

### 6.3 可观测性

- 每轮 action、guardrail decision、tool observation、feedback report 都写入 run log；
- CLI 输出最终状态和 run log 路径；
- WebUI 展示 trace；
- 错误必须有 reason code。

### 6.4 可用性

- CLI 是主入口；
- README 提供 mock demo 的最短路径；
- 未配置真实 key 时仍可完整体验 mock demo；
- 错误信息应指向具体修复动作。

### 6.5 性能

- MVP 面向小型 Python 项目；
- 默认限制最大轮次；
- 默认限制文件读取大小；
- 默认限制命令超时；
- 默认限制 run log 上下文注入数量。

## 7. 系统架构

组件：

- CLI
- WebUI
- Agent Loop
- LLM Provider
- Action Parser
- Guardrail Engine
- Tool Dispatcher
- Tools
- ProcessRunner
- Feedback Analyzer
- StopPolicy
- Memory / Run Log
- Config Loader
- Credential Manager

数据流：

1. 用户通过 CLI 或 WebUI 发起 run。
2. Config Loader 读取配置。
3. Agent Loop 创建 run log。
4. Agent Loop 组装 context。
5. LLM Provider 生成 action。
6. Action Parser 校验 action。
7. Guardrail Engine 审查 action。
8. Tool Dispatcher 执行安全 action。
9. Feedback Analyzer 解析测试输出。
10. Memory / Run Log 记录事件。
11. StopPolicy 判断继续或结束。

外部依赖：

- Python 运行时；
- pytest；
- 可选 OS keyring；
- 可选真实 LLM API；
- Docker；
- GitHub Actions，用于每次 push 自动运行测试；因选择容器分发，也用于构建 Docker 镜像；
- `.gitlab-ci.yml`，作为最终交付物清单要求的 CI 配置文件；
- Render，作为最小 WebUI 的首选部署平台。

## 8. 数据模型

### 8.1 Action

字段：

- `type`: action 类型；
- `path`: 文件路径，可选；
- `content`: 文件内容，可选；
- `patch`: patch 内容，可选；
- `command`: shell 命令，可选；
- `reason`: LLM 对动作意图的简短说明；
- `metadata`: 可选扩展字段。

约束：

- `type` 是外部 JSON 和内部模型都使用的 action discriminator；
- `type` 必须是支持的 action；
- 模型层不使用 `name` 或另一个内部 discriminator 作为规范字段；
- 如需保存 raw provider text，应放在 parser result 或 `metadata` 中，不作为 `Action` 必填字段；
- 文件路径必须是 workspace 相对路径；
- shell command 必须经过白名单检查；
- action 不得包含凭据。

### 8.2 GuardrailDecision

字段：

- `status`: `allowed`、`blocked`、`approval_required`、`invalid`；
- `reason_code`;
- `message`;
- `action_type`;
- `path`;
- `command`;
- `requires_human`;
- `metadata`.

约束：

- 不使用 `reason`、`rule_id`、`approval_data` 作为规范字段；
- 无法安全判定时 status 必须是 `blocked`；
- `approval_required` 只用于配置显式声明的高风险动作或明确规模阈值；
- 序列化不得包含真实 API key、token 或完整环境变量值；
- 如果 path 或 command 疑似包含 secret，应脱敏或截断。

### 8.3 ToolObservation

字段：

- `tool`;
- `status`;
- `summary`;
- `data`;
- `error_code`;
- `feedback`;
- `metadata`.

约束：

- 如需保存 stdout/stderr、exit_code、duration_ms，应放入 `data`，或由 `ProcessResult` / `FeedbackReport` 表达；
- 不保存敏感明文；
- 序列化不得包含真实 API key、token 或完整环境变量值；
- 如果 path、command、stdout/stderr 摘要中疑似包含 secret，应脱敏或截断。

### 8.4 FeedbackReport

字段：

- `status`;
- `category`;
- `passed`;
- `summary`;
- `failing_tests`;
- `locations`;
- `raw_excerpt`;
- `timed_out`;
- `metadata`.

约束：

- `category` 必须属于固定集合：`tests_passed`、`assertion_failure`、`syntax_error`、`import_error`、`missing_file`、`timeout`、`command_error`、`no_tests_collected`、`unknown_failure`；
- 不使用 `type` 或 `confidence` 作为规范必填字段；
- 分类必须来自确定性 analyzer；
- 无法分类时使用 `unknown_failure`；
- 序列化不得包含真实 API key、token 或完整环境变量值；
- 如果 raw excerpt 或 summary 疑似包含 secret，应脱敏或截断。

### 8.5 ProcessResult

字段：

- `argv`;
- `exit_code`;
- `stdout_excerpt`;
- `stderr_excerpt`;
- `duration_ms`;
- `timed_out`;
- `truncated`;
- `error_code`.

约束：

- `argv` 必须来自通过 guardrail 的命令；
- `exit_code` 使用 integer 或 null；
- `duration_ms` 使用 non-negative integer milliseconds；
- stdout/stderr 必须可截断；
- 不保存完整环境变量。

### 8.6 StopDecision

字段：

- `should_stop`;
- `reason_code`;
- `success`;
- `message`;
- `metadata`;

约束：

- 测试通过、最大轮次、guardrail 阻塞和 provider error 必须有确定性 reason code；
- LLM 的 `finish` 不得绕过客观测试反馈。

### 8.7 RunEvent

字段：

- `timestamp`: ISO 8601 UTC string，例如 `2026-07-08T03:00:00Z`;
- `run_id`;
- `iteration`;
- `event_type`;
- `payload`;

约束：

- JSONL 每行一个可 round-trip 的 JSON object；
- 字段顺序不具有语义意义；
- 测试应断言 JSON 结构和关键字段，不依赖文本字段顺序；
- payload 不能包含真实 key、token 或完整环境变量值；
- payload 中的 path、command、stdout/stderr 摘要如疑似包含 secret，应脱敏或截断。

### 8.8 HarnessConfig

字段：

- `workspace`;
- `provider`;
- `max_iterations`;
- `test_command`;
- `allowed_tools`;
- `allowed_commands`;
- `blocked_paths`;
- `write_limit`;
- `timeout_seconds`;
- `run_log_dir`;
- `approval_mode`;
- `demo_mode`.

约束：

- 不使用 `workspace_root`、`protected_paths`、`timeout` 作为规范字段；
- 缺省 provider 为 mock；
- test command 默认 `["python", "-m", "pytest"]` 或等价 argv；
- allowed commands 默认只包含测试命令，不允许任意 shell；
- blocked paths 默认包含 `.env`、`.git`、credential/secret patterns；
- max_iterations 和 timeout_seconds 必须是安全有限正值。

## 9. 凭据与分发设计

### 9.1 凭据设计

mock LLM 不需要凭据，是测试和 CI 的主路径。

真实 LLM provider 为可选手动运行路径。用户需要通过 credential manager 设置 key。

安全存储优先级：

1. OS keyring；
2. Docker 或部署平台 secret；
3. 开发模式 `.env`。

`.env` 不是安全存储，只作为开发便利入口。README 必须说明它是明文文件，可能被进程环境读取，必须加入 `.gitignore`。

凭据命令：

- `safe-repair credentials status`：显示 provider 是否已配置 key，不显示 key 值。
- `safe-repair credentials set`：隐藏输入 key 并保存。
- `safe-repair credentials clear`：清除 key。

### 9.2 分发设计

本项目选择 Python 包 + CLI + Docker 镜像。

Python 包：

- 使用 `pyproject.toml` 定义包；
- 暴露 CLI 命令 `safe-repair`；
- README 提供本地安装命令。

Docker：

- 提供 `Dockerfile`；
- 用户通过 volume 挂载 workspace；
- 默认运行 mock demo 不需要 key；
- 真实 provider 通过 Docker secret 或环境变量注入，但不在镜像内保存。
- 镜像发布目标为 GHCR 或 Docker Hub；README 提供 `docker pull`、`docker run` 和本地 `docker build` 命令。

CI/CD：

- GitHub Actions 必须配置为每次 push 自动运行测试；
- 因项目选择容器分发，GitHub Actions 还必须构建 Docker 镜像；
- GitHub Actions 最后一次运行必须为 pass 状态；
- GitHub Actions 至少运行 mock/stub 单元测试，并运行 Docker build 或 mock demo smoke test；
- 最终交付物必须包含 `.gitlab-ci.yml`；
- `.gitlab-ci.yml` 必须包含名为 `unit-test` 的 job；
- `unit-test` 只运行 mock/stub 测试，不调用真实 LLM；
- `.gitlab-ci.yml` 不依赖真实 API key；
- GitHub Actions 不依赖真实 API key；
- 两套 CI 都不能调用真实 LLM；
- 可选部署 WebUI；

WebUI 部署：

- 部署一个最小可访问 demo 页面，首选 Render；
- 页面只运行 mock demo；
- 不允许上传任意项目执行代码；
- README 提供线上 URL 和部署说明。

## 10. 技术选型与理由

语言：Python。

理由：

- 目标项目是 Python 小项目；
- pytest 反馈稳定；
- mock LLM 和 harness 单测都可用 pytest 完成；
- CLI、Docker、WebUI 都容易实现；
- 适合单人期末项目范围。

测试框架：pytest。

理由：

- 与目标反馈信号一致；
- 容易做失败样本；
- 易于 CI。

WebUI 技术：

- 使用轻量 Python Web 框架即可；
- WebUI 只做机制演示，不作为核心产品。
- WebUI 采用 Open Design 原则进行最小界面设计：清晰展示 action trace、feedback、guardrail 和 final status，不构建完整在线 IDE。

LLM provider：

- `MockLLMProvider` 是主路径；
- OpenAI-compatible provider 是可选手动运行路径；
- 不使用 agent orchestration framework。

存储：

- run log 使用 JSONL；
- 配置使用 TOML；
- 凭据使用 OS keyring 或 secret 环境。

平台支持：

- 开发时兼容 Windows 路径处理；
- CI 和正式验收以 Linux 环境为主。

## 11. 测试策略

### 11.1 单元测试

覆盖：

- Action Parser；
- Guardrail Engine；
- Feedback Analyzer；
- StopPolicy；
- ProcessRunner fake/stub 执行路径；
- Config Loader；
- Credential Manager 的 fake keyring 与无明文回显逻辑；
- Run Log 脱敏逻辑。

### 11.2 mock LLM agent loop 测试

场景：

- mock LLM 第一轮写入错误实现；
- run_tests 返回 pytest failure；
- Feedback Analyzer 分类为 assertion failure；
- mock LLM 第二轮根据反馈返回修复 action；
- run_tests 返回 passed；
- Agent Loop 停止并返回 success。

### 11.3 guardrail 测试

场景：

- 越界路径写入被 blocked；
- `rm -rf` 类命令被 blocked；
- 未在白名单中的 shell 命令被 blocked；
- 管道、重定向、命令连接符被 blocked；
- 大规模删除返回 approval required 或 blocked。

### 11.4 feedback analyzer 测试

使用固定 pytest 输出样本测试：

- assertion failure；
- syntax error；
- import error；
- no tests collected；
- timeout；
- command error；
- tests passed；
- unknown failure。

### 11.5 CLI 测试

覆盖：

- demo 命令可运行；
- 配置错误返回非 0；
- 缺少真实 key 不影响 mock demo；
- 输出不包含敏感值。

### 11.6 ProcessRunner 测试

覆盖：

- fake ProcessRunner 返回固定 stdout/stderr/exit code；
- 超时结果被包装为 `timeout`；
- 输出过大时被截断；
- 环境变量不会写入 observation；
- `run_tests` 能基于 fake ProcessRunner 触发 Feedback Analyzer。

### 11.7 WebUI smoke test

覆盖：

- health endpoint 返回成功；
- mock demo endpoint 返回 trace；
- 不需要真实 LLM key。

### 11.8 CI 测试

GitHub Actions 至少运行：

- `unit-test`：全部 pytest；
- `docker-build`：构建 Docker 镜像；
- `web-smoke` 或 mock demo smoke test：启动 WebUI 并检查健康接口，或运行 mock demo 验证机制演示可执行。

`.gitlab-ci.yml` 至少包含名为 `unit-test` 的 job，运行 mock/stub 单元测试。两套 CI 都不能调用真实 LLM，也不能依赖真实 API key。

### 11.9 扩展动作测试

如果实现 `apply_patch`，必须补充：

- patch 格式错误测试；
- patch 越界路径测试；
- patch 删除文件测试；
- patch 修改规模限制测试；
- patch 成功应用测试。

## 12. 机制演示设计

### 12.1 Guardrail 演示

命令：

- `safe-repair demo guardrail`

行为：

- Mock LLM 返回危险 action，例如越界写文件或执行 `rm -rf`；
- Guardrail Engine 拦截；
- Agent Loop 记录 `guardrail_blocked`；
- CLI/WebUI 展示 blocked reason。

验收：

- 无真实危险动作执行；
- 输出包含 action、decision、reason code；
- 测试可确定性断言。

### 12.2 Repair Loop 演示

命令：

- `safe-repair demo repair-loop`

行为：

- demo Python 项目初始测试失败；
- Mock LLM 第一轮写入错误代码；
- run_tests 返回 pytest failure；
- Feedback Analyzer 分类失败；
- Mock LLM 第二轮读取反馈后写入修复；
- run_tests 通过；
- Agent Loop 以 success 停止。

验收：

- trace 中能看到失败注入、反馈分类、下一步动作改变、最终通过；
- 不依赖网络；
- 不依赖真实 LLM。

### 12.3 Feedback Classifier 演示

命令：

- `safe-repair demo feedback-classifier`

行为：

- 使用多组固定 pytest 输出样本；
- Feedback Analyzer 输出分类结果；
- CLI/WebUI 展示分类表。

验收：

- 每个样本分类稳定；
- 结果与单元测试一致。

## 13. CI/CD 设计

GitHub Actions workflow：

- GitHub Actions 对应通用要求 §4.8：每次 push 自动运行测试；
- 因项目选择容器分发，GitHub Actions 还必须构建 Docker 镜像；
- 最后一次 GitHub Actions 运行必须为 pass；
- 不注入真实 LLM key；
- 不调用真实 LLM；
- 不依赖真实 API key。

- `unit-test` job：
  - 安装 Python；
  - 安装项目依赖；
  - 运行 pytest；
  - 运行 mock mechanism demos 的测试形式。

- `docker-build` job：
  - 构建 Docker 镜像；
  - 运行容器内 mock demo 或 basic command。

- `web-smoke` 或 `mock-demo-smoke` job：
  - 检查 WebUI health endpoint 或运行 mock demo；
  - 不上传任意代码执行；
  - 不注入真实 LLM key。

`.gitlab-ci.yml`：

- `.gitlab-ci.yml` 对应最终交付物清单第 6 项；
- 必须包含名为 `unit-test` 的 job：
  - 安装 Python；
  - 安装项目依赖；
  - 运行 pytest；
  - 运行 mock mechanism demos 的测试形式；
  - 不注入真实 LLM key；
  - 不调用真实 LLM。

- `.gitlab-ci.yml` 至少承担课程要求的 `unit-test` job；Docker build 和 WebUI smoke 可以由 GitHub Actions 承担。

CI 禁止事项：

- 不调用真实 LLM；
- 不需要真实 API key；
- 不访问私有凭据；
- 不执行危险 shell。

## 14. 验收标准

项目完成必须满足：

1. `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`REFLECTION.md` 存在并符合课程要求。
2. harness 内核包含自己实现的 agent loop、LLM abstraction、action parser、tool dispatcher、guardrail、feedback analyzer、memory/config。
3. mock LLM 单元测试覆盖核心机制。
4. 机制演示能确定性复现：
   - guardrail 拦截危险动作；
   - 失败注入后反馈闭环改变下一步动作；
   - feedback analyzer 的主贡献行为。
5. CLI 可以运行 mock demo。
6. 真实 LLM provider 可选，缺 key 不影响测试。
7. 凭据支持安全录入、状态查看、更新和清除，状态查看不回显明文。
8. README 写清安装、运行、Docker、key 配置、安全边界和已知限制。
9. GitHub Actions workflow 存在，每次 push 自动运行测试；最后一次运行为 pass；因选择容器分发，workflow 包含 Docker build；测试和 smoke test 不调用真实 LLM、不依赖真实 API key。
10. `.gitlab-ci.yml` 存在，包含名为 `unit-test` 的 job；该 job 不调用真实 LLM、不依赖真实 API key，并运行 mock/stub 单元测试。
11. Docker 镜像可以构建，并发布到 GHCR 或 Docker Hub。
12. WebUI 有可访问 URL，并能展示 mock demo trace。

## 15. 风险与边界

### 15.1 范围膨胀

风险：同时做 CLI、真实 LLM、Docker、WebUI、CI/CD，可能导致核心 harness 变浅。

控制：核心评分路径只围绕 mock LLM、agent loop、feedback loop、guardrail。WebUI 只做展示。

### 15.2 机制被误判为 prompt

风险：如果安全和反馈靠 prompt 描述，会不符合 A 类要求。

控制：反馈分类、危险拦截、停机策略、动作解析全部由代码实现，并有单测。

### 15.3 真实 LLM 不稳定

风险：真实 provider 可能因网络、费用、输出格式导致不稳定。

控制：真实 provider 不是 CI 和机制演示路径；mock provider 是主路径。

### 15.4 pytest 输出格式复杂

风险：pytest 输出样式很多，完整解析成本高。

控制：MVP 支持典型失败类型，无法识别时归为 `unknown_failure` 并保留摘要。

### 15.5 安全护栏不可能绝对完备

风险：shell 命令和路径绕过方式复杂。

控制：默认 deny；只允许测试命令白名单；无法判断时 blocked。

### 15.6 WebUI 部署占用时间

风险：线上部署和 UI 可能分散精力。

控制：WebUI 只运行内置 mock demo，不提供任意代码执行能力。
