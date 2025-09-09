"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
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
        data_queue: queue_proxy_wrapper.QueueProxyWrapper,
        response_queue: queue_proxy_wrapper.QueueProxyWrapper,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """
        try:
            command = cls(
                cls.__private_key, connection, target, local_logger, data_queue, response_queue
            )
            return [True, command]
        except (OSError, ValueError, EOFError):
            return [False, None]

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,
        local_logger: logger.Logger,
        data_queue: queue_proxy_wrapper.QueueProxyWrapper,
        response_queue: queue_proxy_wrapper.QueueProxyWrapper,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"
        self.connection = connection
        self.target = target
        self.local_logger = local_logger
        self.data_queue = data_queue
        self.response_queue = response_queue
        # Do any intializiation here

    def run(
        self,
    ) -> None:
        """
        Make a decision based on received telemetry data.
        """
        # Log average velocity for this trip so far
        telemetry_data = self.data_queue.queue.get()

        self.local_logger.info(telemetry_data)
        self.local_logger.info(self.target.z)

        if telemetry_data.time_since_boot and telemetry_data.time_since_boot > 0:
            avg_v = (
                math.sqrt(
                    telemetry_data.x_velocity**2
                    + telemetry_data.y_velocity**2
                    + telemetry_data.z_velocity**2
                )
                / telemetry_data.time_since_boot
            )
        else:
            avg_v = 0

        self.local_logger.info(f"Average velocity: {avg_v}")
        # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
        # The appropriate commands to use are instructed below

        # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
        # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"
        if abs(telemetry_data.z - self.target.z) > 0.5:
            self.response_queue.queue.put(f"CHANGE_ALTITUDE: {self.target.z-telemetry_data.z}")
        else:
            self.response_queue.queue.put("CHANGE_ALTITUDE: 0")

        # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
        # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
        delta_y = self.target.y - telemetry_data.y
        delta_x = self.target.x - telemetry_data.x
        if delta_x == 0:
            if delta_y > 0:
                angle = math.pi / 2
            else:
                angle = 3 * math.pi / 2
        else:
            angle = math.atan(delta_y / delta_x)
            if delta_y < 0:
                angle += math.pi
        if abs(telemetry_data.yaw - angle) > (math.pi / 36):
            self.response_queue.queue.put(f"CHANGING_YAW: {(angle-telemetry_data.yaw)/math.pi*180}")
        else:
            self.response_queue.queue.put("CHANGING_YAW: 0")

        if abs(telemetry_data.z - self.target.z) > 0.5 or abs(telemetry_data.yaw - angle) > (
            math.pi / 36
        ):
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                0,
                1,
                5,
                0,
                1,
                0,
                0,
                self.target.z,
            )
        # Positive angle is counter-clockwise as in a right handed system


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
