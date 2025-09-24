"""
Decision-making logic.
"""

import math

from pymavlink import mavutil
from modules.telemetry import telemetry

from ..common.modules.logger import logger


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """
        try:
            command = cls(cls.__private_key, connection, target, local_logger)
            return [True, command]
        except (OSError, ValueError, EOFError):
            return [False, None]

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"
        self.connection = connection
        self.target = target
        self.local_logger = local_logger
        self.start = None
        self.v_x = []
        self.v_y = []
        self.v_z = []
        # Do any intializiation here

    def run(self, data: telemetry.TelemetryData) -> list:
        """
        Make a decision based on received telemetry data.
        """
        # Log average velocity for this trip so far
        telemetry_data = data

        if telemetry_data:

            if not self.start:
                self.start = Position(telemetry_data.x, telemetry_data.y, telemetry_data.z)

            self.v_x.append(telemetry_data.x_velocity)
            self.v_y.append(telemetry_data.y_velocity)
            self.v_z.append(telemetry_data.z_velocity)

            avg_v = [
                sum(self.v_x) / len(self.v_x),
                sum(self.v_y) / len(self.v_y),
                sum(self.v_z) / len(self.v_z),
            ]

            self.local_logger.info(f"Average velocity: {avg_v}")
            # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
            # The appropriate commands to use are instructed below

            # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
            # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"
            queued = []

            if abs(telemetry_data.z - self.target.z) > 0.5:
                self.connection.mav.command_long_send(
                    1,
                    0,
                    mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                    0,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    self.target.z,
                )
                queued.append(f"CHANGE_ALTITUDE: {self.target.z-telemetry_data.z}")

            # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
            # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
            delta_y = self.target.y - telemetry_data.y
            delta_x = self.target.x - telemetry_data.x
            angle = math.atan2(delta_y, delta_x)
            yaw_deg = telemetry_data.yaw

            yaw_diff = math.degrees(angle - yaw_deg)
            if yaw_diff > 180:
                yaw_diff -= 360
            elif yaw_diff < -180:
                yaw_diff += 360
            if abs(yaw_diff) > (5) and not abs(telemetry_data.z - self.target.z) > 0.5:
                self.connection.mav.command_long_send(
                    1,
                    0,
                    mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                    0,
                    yaw_diff,
                    5,
                    yaw_diff / abs(yaw_diff),
                    1,
                    0,
                    0,
                    0,
                )
                queued.append(f"CHANGING_YAW: {yaw_diff}")

        # Positive angle is counter-clockwise as in a right handed system
        return queued


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
