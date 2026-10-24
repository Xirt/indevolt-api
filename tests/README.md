# Tests

English | [简体中文](README.zh-CN.md)

These regression tests describe the SDK's current behavior, including its existing
error handling and limitations. Files are organized by device behavior and caller
purpose, with successful, failed and boundary cases kept with the behavior they
exercise. Scenarios use the SDK's public interfaces and are independent of any
particular consuming application.

HTTP tests use real `aiohttp.ClientSession` instances and simulated devices on
ephemeral `127.0.0.1` ports. Discovery tests use controlled UDP transports and
datagrams. Passing these tests verifies SDK behavior under simulated conditions;
real firmware compatibility, network broadcast reachability, and physical control
effects require separate device validation.

## Setup and execution

Use Python 3.11 or newer. Run the following commands from the repository root in a
POSIX shell. Skip environment creation and activation if a suitable virtual
environment is already active.

```sh
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e . -r tests/requirements.txt
```

Run the complete suite, one business directory, one file, or one parameterized scenario:

```sh
python3 -m pytest tests -q
python3 -m pytest tests/device_monitoring -q
python3 -m pytest tests/device_control/test_settings.py -q
python3 -m pytest 'tests/device_monitoring/test_polling.py::test_initialize_then_repeat_batched_reads[one-point-tail]' -q
```

List collected cases without executing them:

```sh
python3 -m pytest tests --collect-only -q
```

## Scenario index

Tests use five business directories. `device_information/` covers device metadata
and generation identification; `device_monitoring/` covers status reads and polling.
`device_control/` groups settings and commands, including complete control sequences.

```text
tests/
├── device_discovery/
├── device_information/
├── device_monitoring/
├── device_control/
└── clients/
```

| Capability | File | Covered scenarios |
| --- | --- | --- |
| Device discovery | [device_discovery/test_active.py](device_discovery/test_active.py) | Broadcast payload and ports, reply collection, current target derivation, bind and send failures, lookup failure, transport cleanup and cancellation. |
| Device discovery | [device_discovery/test_passive.py](device_discovery/test_passive.py) | Matching broadcast prefixes, unrelated packets, source IP callbacks and repeated announcements. |
| Device discovery | [device_discovery/test_information.py](device_discovery/test_information.py) | Device metadata from discovery replies, default port, malformed packets and current failure for non-object JSON. |
| Device discovery | [device_discovery/test_deduplication.py](device_discovery/test_deduplication.py) | Duplicate IPs keep their first reply; distinct IPs remain separate devices. |
| Device information | [device_information/test_reading.py](device_information/test_reading.py) | Missing model information, HTTP and connection failures, timeout wrapping, invalid responses and cancellation. |
| Device information | [device_information/test_generation.py](device_information/test_generation.py) | Known model mappings, unknown-model fallback, replacement of an existing generation and preservation of other fields. |
| Device monitoring | [device_monitoring/test_reading.py](device_monitoring/test_reading.py) | Single and multiple points, string and enum inputs, raw response preservation, invalid identifiers, HTTP and connection errors, timeout, invalid JSON, content type and cancellation. |
| Device monitoring | [device_monitoring/test_polling.py](device_monitoring/test_polling.py) | Initialization followed by repeated reads of 49, 50, 51 or 101 points, 50-point batches, trailing batches and changing snapshots. |
| Device monitoring | [device_monitoring/test_recovery.py](device_monitoring/test_recovery.py) | A successful batch followed by HTTP or JSON failure, then an explicit new polling cycle using the same client and session. |
| Device control | [device_control/test_settings.py](device_control/test_settings.py) | Scalar and list values, integer conversion, RPC payloads, acknowledgement interpretation, invalid inputs, communication and response failures and cancellation. |
| Device control | [device_control/test_setting_readback.py](device_control/test_setting_readback.py) | Boolean, numeric and enum setting writes followed by reads of their corresponding status points. |
| Device control | [device_control/test_commands.py](device_control/test_commands.py) | Charge, discharge and stop payloads, accepted and rejected commands, commands sent without automatic limit checks. |
| Device control | [device_control/test_limits.py](device_control/test_limits.py) | Generation-specific charge and discharge power boundaries, minimum SOC and exception attributes. |
| Device control | [device_control/test_sequence.py](device_control/test_sequence.py) | Read device information, check limits, select a mode, issue a control command and read status. |
| Device control | [device_control/test_mode_retry.py](device_control/test_mode_retry.py) | Explicitly retry a rejected, unacknowledged or failed mode write before sending a control command. |
| Device control | [device_control/test_recovery.py](device_control/test_recovery.py) | Send a stop command after a charge or discharge command is rejected. |
| Clients and multiple devices | [clients/test_from_discovery.py](clients/test_from_discovery.py) | Create a usable client from a discovered address with default or custom timeout and a caller-owned session. |
| Clients and multiple devices | [clients/test_session_reuse.py](clients/test_session_reuse.py) | Separate probing and polling clients reuse one caller-owned session. |
| Clients and multiple devices | [clients/test_multi_device.py](clients/test_multi_device.py) | Concurrent requests keep device results separate; one device failure leaves other reads and subsequent recovery usable. |

Batch splitting, response merging, mode selection and retries are explicit caller
sequences in these tests. The SDK does not perform those steps automatically.
The 50-point batch size is a scenario input, not a measured device capacity or an
SDK-enforced limit.

## Current behavior recorded by the tests

| Area | Current behavior |
| --- | --- |
| Device monitoring | `fetch_data()` raises `ClientError` for HTTP and connection errors, propagates timeouts, and raises `JSONDecodeError` for malformed JSON. |
| Device settings | `set_data()` returns the truth value of `result`; a missing result is `False`. HTTP, connection, timeout, JSON and content-type failures return `False`. |
| Numeric inputs | Non-numeric string identifiers or values raise `ValueError` before a request is sent. |
| Device information | Known second-generation models map to generation 2; other model strings currently map to generation 1. Missing `device` or `type` leaves the response unchanged. Information read timeouts are wrapped with endpoint context. |
| Real-time commands | `charge()` and `discharge()` send commands without invoking the separate limit checks. Their current docstrings claim range validation that the implementation does not perform. |
| Limit checks | Generation 1: charge up to 1200 W, discharge up to 800 W. Generation 2: both up to 10800 W. Minimum target SOC is 5%; these boundaries are inclusive. |
| Active discovery parsing | Invalid JSON or UTF-8 falls back to the source IP and port 8080. Valid JSON with a non-object root currently raises `AttributeError`. |
| Broadcast targets | Current subnet targets replace the last IPv4 octet with `255`, excluding loopback and link-local addresses. Tests record this derivation without validating it against actual interface netmasks. |
| Cancellation | HTTP operations and active discovery propagate cancellation; active discovery closes its transport. |

These expectations document the current baseline. When an approved behavior change
alters a limitation, update the relevant regression expectations with that change.

## Shared fixtures

Common HTTP fixtures live at the root. Fixtures used by one business area live in
that directory's `conftest.py`.

| Location | Fixture or helper | Purpose |
| --- | --- | --- |
| [conftest.py](conftest.py) | `device_factory` / `device` | Start independent local device servers and clean them up after each test. |
| [conftest.py](conftest.py) | `session` / `api` | Supply a caller-owned HTTP session with environment proxies disabled and a client targeting a local server; teardown closes the session. |
| [helpers.py](helpers.py) | `MockDevice` / `RecordedRequest` | Configure responses and record request methods, paths, query parameters, headers and bodies. |
| [device_discovery/conftest.py](device_discovery/conftest.py) | `protocol` / `network` | Supply fresh discovery response collectors and controlled UDP communication, address resolution and wait behavior. |
| [device_discovery/helpers.py](device_discovery/helpers.py) | `DiscoveryNetwork` | Hold the controlled discovery network state. |
| [device_monitoring/conftest.py](device_monitoring/conftest.py) | `point_values` | Serve requested points from a mutable snapshot for repeated polling and recovery scenarios. |
| [device_control/conftest.py](device_control/conftest.py) | `api_without_network` | Supply a non-networked client for synchronous control limit checks. |

## Maintaining the suite

- Use one level of business directories and name files for behavior within that area. Keep successful, failed and boundary cases for that behavior together.
- Separate new behaviors into their own files in the relevant directory. Keep a complete sequence of calls together under its final purpose, such as control or polling recovery.
- Keep shared fixtures at the root and business-specific fixtures in the corresponding directory's `conftest.py`.
- Retain `__init__.py` in each business directory so repeated module names such as `test_reading.py` can be imported independently.
- Parameterize cases that share a test body and give each case a descriptive ID.
- Add or update regression cases when requirements change. Keep this scenario index and the Chinese document synchronized; exact assertions remain in the test code.
