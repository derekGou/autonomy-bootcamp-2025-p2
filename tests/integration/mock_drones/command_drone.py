"""
Mock drone for testing Command.
"""

import os
import pathlib

from pymavlink import mavutil

from modules.command import command
from modules.common.modules.logger import logger


CONNECTION_STRING = "tcpin:localhost:12345"
TIMEOUT = 3.5
NUM_TRIALS = 26
FLOAT_TOLERANCE = 1e-6
TARGET = command.Position(10, 20, 30)
Z_SPEED = 1  # m/s
RELATIVE = 1  # 1 for relative angle
TURNING_SPEED = 5  # deg/s


def main() -> int:
    """
    Begin mock drone simulation to test a command worker.
    """
    # Mocked autopilot/drone
    # source_system = 1 (airside on drone)
    # source_component = 0 (autopilot)
    connection = mavutil.mavlink_connection(CONNECTION_STRING, source_system=1, source_component=0)
    connection.wait_heartbeat()

    # Instantiate logger after main starts
    drone_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{drone_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create drone logger")
        return -1

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized")

    # Task is to read NUM_TRIALS COMMAND_LONG messages
    for _ in range(NUM_TRIALS):
        msg = connection.recv_match(type="COMMAND_LONG", blocking=True, timeout=TIMEOUT)
        if not msg or msg.get_type() != "COMMAND_LONG":
            local_logger.error("Sent incorrect message type or timed out, still expecting mesages")
            return -2
        if msg.command not in (
            mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
            mavutil.mavlink.MAV_CMD_CONDITION_YAW,
        ):
            local_logger.error("Sent incorrect command within COMMAND_LONG message.")
            return -3
        if msg.confirmation != 0:
            local_logger.error("Confirmation should be 0")
            return -4
        if msg.command == mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT:
            if abs(msg.param7 - TARGET.z) > FLOAT_TOLERANCE:
                local_logger.error(f"Altitude target is not the desired value: {msg.param7}")
                return -5
            if abs(msg.param1 - Z_SPEED) > FLOAT_TOLERANCE:
                local_logger.error(f"Ascent/descnet speed is not the desired value: {msg.param1}")
                return -6
        else:  # msg.command == mavutil.mavlink.MAV_CMD_CONDITION_YAW
            if abs(msg.param4 - RELATIVE) > FLOAT_TOLERANCE:
                local_logger.error(f"Not using relative angle: {msg.param4}")
                return -7
            if abs(msg.param2 - TURNING_SPEED) > FLOAT_TOLERANCE:
                local_logger.error(f"Turning speed is not the desired value: {msg.param2}")
                return -8
        local_logger.info("Received a valid command")

    msg = connection.recv_match(type="COMMAND_LONG", blocking=True, timeout=TIMEOUT)
    if msg and msg.get_type() == "COMMAND_LONG":
        local_logger.error(msg)
        return -9

    local_logger.info("Passed!")
    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Drone: Failed with return code {result_main}")
    else:
        print("Drone: Success!")
