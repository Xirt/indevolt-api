# Tests

English | [简体中文](README.zh-CN.md)

These regression tests describe the SDK's current behavior, including its existing
error handling and limitations. Scenarios use the SDK's public interfaces and are
independent of any particular consuming application.

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

Run the complete suite, one file, or one parameterized scenario:

```sh
python3 -m pytest tests -q
python3 -m pytest tests/test_write_data.py -q
python3 -m pytest 'tests/test_batch_polling.py::test_initialize_then_repeat_batched_reads[one-point-tail]' -q
```

List collected cases without executing them:

```sh
python3 -m pytest tests --collect-only -q
```

## Scenario index

| File | Covered scenarios |
| --- | --- |
| [test_read_data.py](test_read_data.py) | Single and multiple points, string and enum inputs, raw response preservation, invalid identifiers, HTTP and connection errors, timeout, invalid JSON, content type, cancellation. |
| [test_write_data.py](test_write_data.py) | Scalar and list values, integer conversion, RPC payloads, acknowledgement interpretation, invalid inputs, communication and response failures, cancellation. |
| [test_config.py](test_config.py) | Model-to-generation mapping, preserved configuration fields, missing model information, clients created from discovered devices, default and custom timeouts, error handling. |
| [test_realtime_control.py](test_realtime_control.py) | Charge, discharge and stop payloads, accepted and rejected commands, commands sent without automatic limit checks. |
| [test_limits.py](test_limits.py) | Generation-specific charge and discharge power boundaries, minimum SOC, exception attributes. |
| [test_active_discovery_protocol.py](test_active_discovery_protocol.py) | Response metadata, default port, duplicate IPs, distinct devices, malformed packets, current failure for non-object JSON. |
| [test_active_discovery.py](test_active_discovery.py) | Broadcast payload and ports, reply collection, current target derivation, bind and send failures, lookup failure, transport cleanup and cancellation. |
| [test_passive_discovery.py](test_passive_discovery.py) | Matching broadcast prefixes, unrelated packets, source IP callbacks and repeated announcements. |
| [test_batch_polling.py](test_batch_polling.py) | Initialization followed by repeated reads of 49, 50, 51 or 101 points, 50-point batches, trailing batches and changing snapshots. |
| [test_polling_recovery.py](test_polling_recovery.py) | A successful batch followed by HTTP or JSON failure, then an explicit new polling cycle using the same client and session. |
| [test_shared_session.py](test_shared_session.py) | Separate probing and polling clients, concurrent requests to multiple devices, recovery after one device fails. |
| [test_control_sequence.py](test_control_sequence.py) | Configuration, limit checks, mode selection, control and status reads; explicit mode-write retry; stop after a rejected command. |
| [test_setting_readback.py](test_setting_readback.py) | Boolean, numeric and enum setting writes followed by reads of their corresponding status points. |

Batch splitting, response merging, mode selection and retries are explicit caller
sequences in these tests. The SDK does not perform those steps automatically.
The 50-point batch size is a scenario input, not a measured device capacity or an
SDK-enforced limit.

## Current behavior recorded by the tests

| Area | Current behavior |
| --- | --- |
| Reads | `fetch_data()` raises `ClientError` for HTTP and connection errors, propagates timeouts, and raises `JSONDecodeError` for malformed JSON. |
| Writes | `set_data()` returns the truth value of `result`; a missing result is `False`. HTTP, connection, timeout, JSON and content-type failures return `False`. |
| Numeric inputs | Non-numeric string identifiers or values raise `ValueError` before a request is sent. |
| Configuration | Known second-generation models map to generation 2; other model strings currently map to generation 1. Missing `device` or `type` leaves the response unchanged. Configuration timeouts are wrapped with endpoint context. |
| Real-time commands | `charge()` and `discharge()` send commands without invoking the separate limit checks. Their current docstrings claim range validation that the implementation does not perform. |
| Limit checks | Generation 1: charge up to 1200 W, discharge up to 800 W. Generation 2: both up to 10800 W. Minimum target SOC is 5%; these boundaries are inclusive. |
| Active discovery parsing | Invalid JSON or UTF-8 falls back to the source IP and port 8080. Valid JSON with a non-object root currently raises `AttributeError`. |
| Broadcast targets | Current subnet targets replace the last IPv4 octet with `255`, excluding loopback and link-local addresses. Tests record this derivation without validating it against actual interface netmasks. |
| Cancellation | HTTP operations and active discovery propagate cancellation; active discovery closes its transport. |

These expectations document the current baseline. When an approved behavior change
alters a limitation, update the relevant regression expectations with that change.

## Shared fixtures

[conftest.py](conftest.py) and [helpers.py](helpers.py) provide:

| Fixture or helper | Purpose |
| --- | --- |
| `device_factory` / `device` | Start independent local device servers and clean them up after each test. |
| `session` | Supply a real HTTP session with environment proxies disabled; fixture teardown closes it. |
| `api` / `api_without_network` | Supply a client targeting a local server or a non-networked client for synchronous limit checks. |
| `point_values` | Serve requested points from a mutable snapshot for repeated polling and recovery scenarios. |
| `MockDevice` / `RecordedRequest` | Configure responses and record request methods, paths, query parameters, headers and bodies. |

## Maintaining the suite

- Keep new cases in the file for their scenario; use a separate file for a new scenario group.
- Parameterize cases that share a test body and give each case a descriptive ID.
- Add or update regression cases when requirements change. Keep this scenario index and the Chinese document synchronized; exact assertions remain in the test code.
