from enum import IntEnum, StrEnum
from typing import Final

# Active (solicited) discovery: send a broadcast then listen for replies
ACTIVE_DISCOVERY_PORT: Final[int] = 10000
ACTIVE_DISCOVERY_MESSAGE: Final[bytes] = b"AT+IGDEVICEIP"
ACTIVE_DISCOVERY_TIMEOUT: Final[float] = 5.0

# Passive (unsolicited) discovery: listen for device-initiated broadcasts
PASSIVE_DISCOVERY_PORT: Final[int] = 8099
PASSIVE_DISCOVERY_MAGIC: Final[bytes] = b"BCF-D"
PASSIVE_DISCOVERY_BIND_ADDR: Final[str] = "0.0.0.0"  # bind address for local_addr

# Internal send-to tuple used by async_discover to broadcast the discovery message
_ACTIVE_BROADCAST_ADDR: Final[tuple[str, int]] = (
    "255.255.255.255",
    PASSIVE_DISCOVERY_PORT,
)

SET_REALTIME_ACTION: Final[str] = "47015"

DEVICE_LIMITS: Final[dict[int, dict[str, int]]] = {
    1: {"max_discharge_power": 800, "max_charge_power": 1200, "minimum_soc": 5},
    2: {"max_discharge_power": 2400, "max_charge_power": 2400, "minimum_soc": 5},
}


class IndevoltRealtimeAction(IntEnum):
    """Actions for real-time control mode."""

    STOP = 0
    CHARGE = 1
    DISCHARGE = 2


class IndevoltEnergyMode(IntEnum):
    """Energy mode values for the device."""

    OUTDOOR_PORTABLE = 0
    SELF_CONSUMED_PRIORITIZED = 1
    REAL_TIME_CONTROL = 4
    CHARGE_DISCHARGE_SCHEDULE = 5


class IndevoltConfig(StrEnum):
    """Register keys for configurable device settings (read and write)."""

    WRITE_ENERGY_MODE = "47005"
    WRITE_DISCHARGE_LIMIT = "1142"
    WRITE_MAX_AC_OUTPUT_POWER = "1147"
    WRITE_INVERTER_INPUT_LIMIT = "1138"
    WRITE_FEEDIN_POWER_LIMIT = "1146"
    WRITE_GRID_CHARGING = "1143"
    WRITE_LIGHT = "7265"
    WRITE_BYPASS = "7266"

    READ_ENERGY_MODE = "7101"
    READ_DISCHARGE_LIMIT = "6105"
    READ_REALTIME_COMMAND = "6107"
    READ_REALTIME_TARGET_SOC = "6108"
    READ_REALTIME_POWER_LIMIT = "6109"
    READ_MAX_AC_OUTPUT_POWER = "11011"
    READ_INVERTER_INPUT_LIMIT = "11009"
    READ_FEEDIN_POWER_LIMIT = "11010"
    READ_GRID_CHARGING = "2618"
    READ_LIGHT = "7171"
    READ_BYPASS = "680"


class IndevoltSystem(StrEnum):
    """Register keys for system-level AC power and energy."""

    SERIAL_NUMBER = "0"
    OPERATING_MODE = "606"
    INPUT_POWER = "2101" # Deprecated, replaced with AC_TOTAL_INPUT_POWER
    OUTPUT_POWER = "2108" # Deprecated, replaced with AC_TOTAL_OUTPUT_POWER
    BYPASS_POWER = "667"
    TOTAL_INPUT_ENERGY = "2107"
    TOTAL_OUTPUT_ENERGY = "2104"
    OFF_GRID_OUTPUT_ENERGY = "2105"
    BYPASS_INPUT_ENERGY = "11034"
    HEATING_STATE = "7121"
    AC_VOLTAGE = "2083"
    AC_CURRENT = "2086"
    AC_FREQUENCY = "2095"
    AC_TOTAL_NET_POWER = "2278"
    AC_TOTAL_INPUT_POWER = "2101"
    AC_TOTAL_OUTPUT_POWER = "2108"
    AC_REACTIVE_POWER = "2097"
    AC_APPARENT_POWER = "2098"
    AC_POWER_FACTOR = "2099"


class IndevoltGrid(StrEnum):
    """Register keys for grid and utility meter data."""

    METER_POWER_GEN1 = "21028"
    METER_POWER_GEN2 = "11016"
    VOLTAGE = "2600"
    FREQUENCY = "2612"
    METER_CONNECTED = "7120"


class IndevoltBattery(StrEnum):
    """Register keys for battery system parameters."""

    POWER = "6000" # Deprecated, replaced with DC_POWER  
    CHARGE_DISCHARGE_STATE = "6001"
    SOC = "6002"
    RATED_CAPACITY = "142"
    DAILY_CHARGING_ENERGY = "6004"
    DAILY_DISCHARGING_ENERGY = "6005"
    TOTAL_CHARGING_ENERGY = "6006"
    TOTAL_DISCHARGING_ENERGY = "6007"
    RATED_CAPACITY_GEN2 = "142" # Deprecated, replaced with RATED_CAPACITY
    DC_VOLTAGE = "6100"
    DC_CURRENT = "6101"
    DC_POWER = "6000"

    GEN_1_INVERTER_TEMPERATURE = "7600"
    GEN_1_PACK_1_TEMPERATURE = "7605"
    GEN_1_PACK_2_TEMPERATURE = "7620"
    GEN_1_PACK_3_TEMPERATURE = "7621"
    GEN_1_MOS_TEMPERATURE_CHARGE = "7638"
    GEN_1_MOS_TEMPERATURE_DISCHARGE = "7639"

    GEN_2_CYCLE_COUNT = "9003"
    GEN_2_TRANSFORMER_TEMPERATURE = "11005"
    
    MAIN_SERIAL_NUMBER = "9008"
    MAIN_SOC = "9000"
    MAIN_TEMPERATURE = "9012"
    MAIN_VOLTAGE = "9004"
    MAIN_CURRENT = "9013"
    MAIN_HEATING_STATE = "9079"

    PACK_1_SERIAL_NUMBER = "9032"
    PACK_1_SOC = "9016"
    PACK_1_TEMPERATURE = "9030"
    PACK_1_VOLTAGE = "9020"
    PACK_1_CURRENT = "19173"
    PACK_1_HEATING_STATE = "9096"
    PACK_1_MOS_TEMPERATURE = "11042"

    PACK_2_SERIAL_NUMBER = "9051"
    PACK_2_SOC = "9035"
    PACK_2_TEMPERATURE = "9049"
    PACK_2_VOLTAGE = "9039"
    PACK_2_CURRENT = "19174"
    PACK_2_HEATING_STATE = "9112"
    PACK_2_MOS_TEMPERATURE = "9085"

    PACK_3_SERIAL_NUMBER = "9070"
    PACK_3_SOC = "9054"
    PACK_3_TEMPERATURE = "9068"
    PACK_3_VOLTAGE = "9058"
    PACK_3_CURRENT = "19175"
    PACK_3_HEATING_STATE = "9128"
    PACK_3_MOS_TEMPERATURE = "9101"

    PACK_4_SERIAL_NUMBER = "9165"
    PACK_4_SOC = "9149"
    PACK_4_TEMPERATURE = "9163"
    PACK_4_VOLTAGE = "9153"
    PACK_4_CURRENT = "19176"
    PACK_4_HEATING_STATE = "9144"
    PACK_4_MOS_TEMPERATURE = "9117"

    PACK_5_SERIAL_NUMBER = "9218"
    PACK_5_SOC = "9202"
    PACK_5_TEMPERATURE = "9216"
    PACK_5_VOLTAGE = "9206"
    PACK_5_CURRENT = "19177"
    PACK_5_HEATING_STATE = "9279"
    PACK_5_MOS_TEMPERATURE = "9133"


class IndevoltSolar(StrEnum):
    """Register keys for PV/solar input and output parameters."""

    DC_OUTPUT_POWER = "1501"
    DAILY_PRODUCTION = "1502"
    CUMULATIVE_PRODUCTION = "1505"

    DC_INPUT_VOLTAGE_1 = "1600"
    DC_INPUT_VOLTAGE_2 = "1601"
    DC_INPUT_VOLTAGE_3 = "1602"
    DC_INPUT_VOLTAGE_4 = "1603"

    DC_INPUT_CURRENT_1 = "1632"
    DC_INPUT_CURRENT_2 = "1633"
    DC_INPUT_CURRENT_3 = "1634"
    DC_INPUT_CURRENT_4 = "1635"

    DC_INPUT_POWER_1 = "1664"
    DC_INPUT_POWER_2 = "1665"
    DC_INPUT_POWER_3 = "1666"
    DC_INPUT_POWER_4 = "1667"
