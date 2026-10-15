# 测试说明

[English](README.md) | 简体中文

这些回归测试记录 SDK 的当前行为，包括现有的异常处理方式和局限。用例通过 SDK 的公开接口执行，以通用使用场景组织，独立于具体调用方应用。

HTTP 测试使用真实的 `aiohttp.ClientSession`，访问运行在 `127.0.0.1` 随机端口上的模拟设备。发现测试使用受控的 UDP transport 和报文。测试通过说明 SDK 在模拟条件下的行为符合断言；真实固件兼容性、网络广播可达性和实际控制效果需要单独进行真机验证。

## 环境准备与运行

使用 Python 3.11 或更高版本。以下命令在仓库根目录、POSIX shell 中执行。已有合适的虚拟环境时，可跳过环境创建和激活步骤。

```sh
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e . -r tests/requirements.txt
```

运行全部测试、单个文件或某个参数化场景：

```sh
python3 -m pytest tests -q
python3 -m pytest tests/test_write_data.py -q
python3 -m pytest 'tests/test_batch_polling.py::test_initialize_then_repeat_batched_reads[one-point-tail]' -q
```

只列出收集到的用例，不执行测试：

```sh
python3 -m pytest tests --collect-only -q
```

## 场景索引

| 文件 | 覆盖场景 |
| --- | --- |
| [test_read_data.py](test_read_data.py) | 单点、多点、字符串和枚举输入、原始响应保留、非法点位、HTTP 和连接错误、超时、无效 JSON、内容类型、取消。 |
| [test_write_data.py](test_write_data.py) | 单值和列表、整数转换、RPC 参数、设备确认结果、非法输入、通信和响应失败、取消。 |
| [test_config.py](test_config.py) | 型号与代数映射、配置字段保留、缺少型号信息、根据发现结果创建客户端、默认和自定义超时、异常处理。 |
| [test_realtime_control.py](test_realtime_control.py) | 充电、放电、停止的命令参数，设备接受和拒绝命令，以及发送命令时不自动检查限值的当前行为。 |
| [test_limits.py](test_limits.py) | 不同代数的充放电功率边界、最低 SOC、异常携带的属性。 |
| [test_active_discovery_protocol.py](test_active_discovery_protocol.py) | 响应元数据、默认端口、同 IP 去重、不同设备、异常报文，以及非对象 JSON 当前会报错的行为。 |
| [test_active_discovery.py](test_active_discovery.py) | 广播内容与端口、收集响应、当前广播目标推导方式、绑定和发送失败、地址解析失败、transport 释放与取消。 |
| [test_passive_discovery.py](test_passive_discovery.py) | 广播前缀匹配、无关报文、来源 IP 回调、重复广播。 |
| [test_batch_polling.py](test_batch_polling.py) | 初始化后重复读取 49、50、51 或 101 个点位，每批 50 点、尾批处理、变化的数据快照。 |
| [test_polling_recovery.py](test_polling_recovery.py) | 前一批成功、后一批发生 HTTP 或 JSON 错误，再由调用方使用同一客户端和 session 显式开始新一轮读取。 |
| [test_shared_session.py](test_shared_session.py) | 探测与轮询分别使用不同客户端，多设备并发请求，单设备失败后的恢复。 |
| [test_control_sequence.py](test_control_sequence.py) | 获取配置、检查限值、切换模式、执行控制和读取状态；显式重试模式写入；命令被拒绝后发送停止命令。 |
| [test_setting_readback.py](test_setting_readback.py) | 写入布尔、数值和枚举设置，再读取对应的状态点位。 |

分批、合并响应、选择模式和重试都由测试中的调用方代码显式执行，SDK 不会自动完成这些步骤。每批 50 点是场景输入，不代表实测设备容量或 SDK 强制限制。

## 测试记录的当前行为

| 范围 | 当前行为 |
| --- | --- |
| 读取 | `fetch_data()` 遇到 HTTP 和连接错误时抛出 `ClientError`，超时直接向上传递，无效 JSON 抛出 `JSONDecodeError`。 |
| 写入 | `set_data()` 返回 `result` 的布尔值，缺少该字段时为 `False`。HTTP、连接、超时、JSON 和内容类型错误返回 `False`。 |
| 数字输入 | 点位或数值为非数字字符串时，在发送请求前抛出 `ValueError`。 |
| 配置 | 已知二代型号映射为代数 2，其他型号字符串当前映射为代数 1。缺少 `device` 或 `type` 时原样返回。配置请求超时会包装为包含接口信息的异常。 |
| 实时控制 | `charge()`、`discharge()` 直接发送命令，不调用独立的限值检查。当前函数文档声称会校验范围，但实现没有执行该校验。 |
| 限值检查 | 一代最大充电功率 1200 W、最大放电功率 800 W；二代均为 10800 W。最低目标 SOC 为 5%，边界值允许通过。 |
| 主动发现解析 | 无效 JSON 或 UTF-8 回退为来源 IP、端口 8080；合法 JSON 的根值不是对象时，当前抛出 `AttributeError`。 |
| 广播目标 | 当前通过将 IPv4 最后一个段替换为 `255` 推导子网广播目标，并排除回环和链路本地地址。测试记录该推导方式，未验证其与实际网卡掩码是否一致。 |
| 取消 | HTTP 操作和主动发现会向上传递取消异常；主动发现同时关闭 transport。 |

这些断言记录当前基线。后续经确认的行为调整涉及上述局限时，应随变更更新对应的回归断言。

## 共享 fixture

[conftest.py](conftest.py) 和 [helpers.py](helpers.py) 提供：

| fixture 或辅助对象 | 用途 |
| --- | --- |
| `device_factory` / `device` | 启动相互独立的本地模拟设备，并在每个用例结束后清理服务器。 |
| `session` | 提供禁用环境代理的真实 HTTP session，由 fixture 在清理阶段关闭。 |
| `api` / `api_without_network` | 提供指向本地服务器的客户端，或供同步限值检查使用的无网络客户端。 |
| `point_values` | 从可变快照中返回请求的点位，用于重复轮询和失败恢复场景。 |
| `MockDevice` / `RecordedRequest` | 配置模拟响应，记录请求方法、路径、查询参数、请求头和请求体。 |

## 维护约定

- 在对应场景文件中补充用例；新的场景组使用独立文件。
- 相同测试流程使用参数化，为每个场景设置清晰的 ID。
- 需求变化时新增或调整回归用例，同步维护场景索引和英文文档；精确断言以测试代码为准。
