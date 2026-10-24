# 测试说明

[English](README.md) | 简体中文

这些回归测试记录 SDK 的当前行为，包括现有的异常处理方式和局限。文件按设备业务行为和调用方目的组织，同一行为的成功、失败和边界情况放在一起。用例通过 SDK 的公开接口执行，独立于具体调用方应用。

HTTP 测试使用真实的 `aiohttp.ClientSession`，访问运行在 `127.0.0.1` 随机端口上的模拟设备。发现测试使用受控的 UDP transport 和报文。测试通过说明 SDK 在模拟条件下的行为符合断言；真实固件兼容性、网络广播可达性和实际控制效果需要单独进行真机验证。

## 环境准备与运行

使用 Python 3.11 或更高版本。以下命令在仓库根目录、POSIX shell 中执行。已有合适的虚拟环境时，可跳过环境创建和激活步骤。

```sh
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e . -r tests/requirements.txt
```

运行全部测试、某个业务目录、单个文件或某个参数化场景：

```sh
python3 -m pytest tests -q
python3 -m pytest tests/device_monitoring -q
python3 -m pytest tests/device_control/test_settings.py -q
python3 -m pytest 'tests/device_monitoring/test_polling.py::test_initialize_then_repeat_batched_reads[one-point-tail]' -q
```

只列出收集到的用例，不执行测试：

```sh
python3 -m pytest tests --collect-only -q
```

## 场景索引

测试按五个业务目录组织。`device_information/` 覆盖设备信息与代数识别，`device_monitoring/` 覆盖运行状态读取与轮询；`device_control/` 统一收纳设置写入、动作命令和完整控制流程。

```text
tests/
├── device_discovery/
├── device_information/
├── device_monitoring/
├── device_control/
└── clients/
```

| 业务分类 | 文件 | 覆盖场景 |
| --- | --- | --- |
| 设备发现 | [device_discovery/test_active.py](device_discovery/test_active.py) | 广播内容与端口、收集响应、当前广播目标推导方式、绑定和发送失败、地址解析失败、transport 释放与取消。 |
| 设备发现 | [device_discovery/test_passive.py](device_discovery/test_passive.py) | 广播前缀匹配、无关报文、来源 IP 回调、重复广播。 |
| 设备发现 | [device_discovery/test_information.py](device_discovery/test_information.py) | 发现响应中的设备信息、默认端口、异常报文，以及非对象 JSON 当前会报错的行为。 |
| 设备发现 | [device_discovery/test_deduplication.py](device_discovery/test_deduplication.py) | 同 IP 保留首次响应，不同 IP 作为不同设备收集。 |
| 设备信息 | [device_information/test_reading.py](device_information/test_reading.py) | 缺少型号信息、HTTP 和连接失败、超时包装、无效响应、取消读取。 |
| 设备信息 | [device_information/test_generation.py](device_information/test_generation.py) | 已知型号映射、未知型号回退、覆盖已有代数、保留其他信息字段。 |
| 设备监测 | [device_monitoring/test_reading.py](device_monitoring/test_reading.py) | 单点、多点、字符串和枚举输入、原始响应保留、非法点位、HTTP 和连接错误、超时、无效 JSON、内容类型、取消。 |
| 设备监测 | [device_monitoring/test_polling.py](device_monitoring/test_polling.py) | 初始化后重复读取 49、50、51 或 101 个点位，每批 50 点、尾批处理、变化的数据快照。 |
| 设备监测 | [device_monitoring/test_recovery.py](device_monitoring/test_recovery.py) | 前一批成功、后一批发生 HTTP 或 JSON 错误，再由调用方使用同一客户端和 session 显式开始新一轮读取。 |
| 设备控制 | [device_control/test_settings.py](device_control/test_settings.py) | 单值和列表、整数转换、RPC 参数、设备确认结果、非法输入、通信和响应失败、取消。 |
| 设备控制 | [device_control/test_setting_readback.py](device_control/test_setting_readback.py) | 写入布尔、数值和枚举设置，再读取对应的状态点位。 |
| 设备控制 | [device_control/test_commands.py](device_control/test_commands.py) | 充电、放电、停止的命令参数，设备接受和拒绝命令，以及发送命令时不自动检查限值的当前行为。 |
| 设备控制 | [device_control/test_limits.py](device_control/test_limits.py) | 不同代数的充放电功率边界、最低 SOC、异常携带的属性。 |
| 设备控制 | [device_control/test_sequence.py](device_control/test_sequence.py) | 读取设备信息、检查限值、切换模式、执行控制和读取状态的完整流程。 |
| 设备控制 | [device_control/test_mode_retry.py](device_control/test_mode_retry.py) | 模式写入被拒绝、缺少确认或发生 HTTP 错误后，显式重试，再发送控制命令。 |
| 设备控制 | [device_control/test_recovery.py](device_control/test_recovery.py) | 充电或放电命令被拒绝后，再发送停止命令。 |
| 客户端与多设备使用 | [clients/test_from_discovery.py](clients/test_from_discovery.py) | 根据发现地址创建可用客户端，使用默认或自定义超时，以及调用方提供的 session。 |
| 客户端与多设备使用 | [clients/test_session_reuse.py](clients/test_session_reuse.py) | 探测和轮询分别使用不同客户端，复用调用方提供的同一个 session。 |
| 客户端与多设备使用 | [clients/test_multi_device.py](clients/test_multi_device.py) | 多设备并发读取时结果独立，单设备失败后其他设备仍可读取，故障设备也可恢复读取。 |

分批、合并响应、选择模式和重试都由测试中的调用方代码显式执行，SDK 不会自动完成这些步骤。每批 50 点是场景输入，不代表实测设备容量或 SDK 强制限制。

## 测试记录的当前行为

| 范围 | 当前行为 |
| --- | --- |
| 设备监测 | `fetch_data()` 遇到 HTTP 和连接错误时抛出 `ClientError`，超时直接向上传递，无效 JSON 抛出 `JSONDecodeError`。 |
| 设备设置 | `set_data()` 返回 `result` 的布尔值，缺少该字段时为 `False`。HTTP、连接、超时、JSON 和内容类型错误返回 `False`。 |
| 数字输入 | 点位或数值为非数字字符串时，在发送请求前抛出 `ValueError`。 |
| 设备信息 | 已知二代型号映射为代数 2，其他型号字符串当前映射为代数 1。缺少 `device` 或 `type` 时原样返回。读取信息超时会包装为包含接口信息的异常。 |
| 实时控制 | `charge()`、`discharge()` 直接发送命令，不调用独立的限值检查。当前函数文档声称会校验范围，但实现没有执行该校验。 |
| 限值检查 | 一代最大充电功率 1200 W、最大放电功率 800 W；二代均为 10800 W。最低目标 SOC 为 5%，边界值允许通过。 |
| 主动发现解析 | 无效 JSON 或 UTF-8 回退为来源 IP、端口 8080；合法 JSON 的根值不是对象时，当前抛出 `AttributeError`。 |
| 广播目标 | 当前通过将 IPv4 最后一个段替换为 `255` 推导子网广播目标，并排除回环和链路本地地址。测试记录该推导方式，未验证其与实际网卡掩码是否一致。 |
| 取消 | HTTP 操作和主动发现会向上传递取消异常；主动发现同时关闭 transport。 |

这些断言记录当前基线。后续经确认的行为调整涉及上述局限时，应随变更更新对应的回归断言。

## 共享 fixture

通用 HTTP fixture 放在根目录；仅供某类业务使用的 fixture 放在对应目录的 `conftest.py`。

| 位置 | fixture 或辅助对象 | 用途 |
| --- | --- | --- |
| [conftest.py](conftest.py) | `device_factory` / `device` | 启动相互独立的本地模拟设备，并在每个用例结束后清理服务器。 |
| [conftest.py](conftest.py) | `session` / `api` | 提供禁用环境代理的调用方 HTTP session，以及指向本地服务器的客户端；清理阶段关闭 session。 |
| [helpers.py](helpers.py) | `MockDevice` / `RecordedRequest` | 配置模拟响应，记录请求方法、路径、查询参数、请求头和请求体。 |
| [device_discovery/conftest.py](device_discovery/conftest.py) | `protocol` / `network` | 提供独立的发现响应收集器，以及受控的 UDP 通信、地址解析和等待行为。 |
| [device_discovery/helpers.py](device_discovery/helpers.py) | `DiscoveryNetwork` | 保存受控的发现网络状态。 |
| [device_monitoring/conftest.py](device_monitoring/conftest.py) | `point_values` | 从可变快照中返回请求的点位，用于重复轮询和失败恢复场景。 |
| [device_control/conftest.py](device_control/conftest.py) | `api_without_network` | 提供供同步控制限值检查使用的无网络客户端。 |

## 维护约定

- 使用一层业务目录，文件按目录内的具体行为命名；同一行为的成功、失败和边界情况放在一起。
- 新的业务行为在对应目录中使用独立文件；完整调用流程按最终目的归类，例如设备控制或轮询恢复。
- 共享 fixture 留在根目录，业务专用 fixture 放在对应目录的 `conftest.py`。
- 各业务目录保留 `__init__.py`，确保 `test_reading.py` 等同名测试模块可独立导入。
- 相同测试流程使用参数化，为每个场景设置清晰的 ID。
- 需求变化时新增或调整回归用例，同步维护场景索引和英文文档；精确断言以测试代码为准。
