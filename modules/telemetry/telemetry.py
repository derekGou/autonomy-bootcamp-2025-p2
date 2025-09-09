"""
Telemetry gathering logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


class TelemetryData:  # pylint: disable=too-many-instance-attributes
    """
    Python struct to represent Telemtry Data. Contains the most recent attitude and position reading.
    """

    def __init__(
        self,
        time_since_boot: int | None = None,  # ms
        x: float | None = None,  # m
        y: float | None = None,  # m
        z: float | None = None,  # m
        x_velocity: float | None = None,  # m/s
        y_velocity: float | None = None,  # m/s
        z_velocity: float | None = None,  # m/s
        roll: float | None = None,  # rad
        pitch: float | None = None,  # rad
        yaw: float | None = None,  # rad
        roll_speed: float | None = None,  # rad/s
        pitch_speed: float | None = None,  # rad/s
        yaw_speed: float | None = None,  # rad/s
    ) -> None:
        self.time_since_boot = time_since_boot
        self.x = x
        self.y = y
        self.z = z
        self.x_velocity = x_velocity
        self.y_velocity = y_velocity
        self.z_velocity = z_velocity
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.roll_speed = roll_speed
        self.pitch_speed = pitch_speed
        self.yaw_speed = yaw_speed

    def __str__(self) -> str:
        return f"""{{
            time_since_boot: {self.time_since_boot},
            x: {self.x},
            y: {self.y},
            z: {self.z},
            x_velocity: {self.x_velocity},
            y_velocity: {self.y_velocity},
            z_velocity: {self.z_velocity},
            roll: {self.roll},
            pitch: {self.pitch},
            yaw: {self.yaw},
            roll_speed: {self.roll_speed},
            pitch_speed: {self.pitch_speed},
            yaw_speed: {self.yaw_speed}
        }}"""


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Telemetry:
    """
    Telemetry class to read position and attitude (orientation).
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple[True, Telemetry] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Telemetry object.
        """
        try:
            telemetry = cls(cls.__private_key, connection, local_logger)
            return [True, telemetry]
        except Exception as e:
            return [False, None]

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is Telemetry.__private_key, "Use create() method"

        # Do any intializiation here
        self.local_logger = local_logger
        self.connection = connection

    def run(
        self,
    ) -> "TelemetryData | None":
        """
        Receive LOCAL_POSITION_NED and ATTITUDE messages from the drone,
        combining them together to form a single TelemetryData object.
        """
        msg = self.connection.recv_match(blocking=False)
        if msg is None:
            return None

        if msg.get_type() == "LOCAL_POSITION_NED":
            self.last_position = msg
        elif msg.get_type() == "ATTITUDE":
            self.last_attitude = msg

        # Only return if we have both types
        if hasattr(self, "last_position") and hasattr(self, "last_attitude"):
            position = self.last_position
            attitude = self.last_attitude

            telemetry_data = TelemetryData(
                time_since_boot=int(
                    max(getattr(position, "time_boot_ms", 0), getattr(attitude, "time_boot_ms", 0))
                    / 1000
                ),
                x=position.x,
                y=position.y,
                z=position.z,
                x_velocity=position.vx,
                y_velocity=position.vy,
                z_velocity=position.vz,
                roll=attitude.roll,
                pitch=attitude.pitch,
                yaw=attitude.yaw,
                roll_speed=attitude.rollspeed,
                pitch_speed=attitude.pitchspeed,
                yaw_speed=attitude.yawspeed,
            )
            return telemetry_data

        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
