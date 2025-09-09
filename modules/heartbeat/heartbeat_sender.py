"""
Heartbeat sending logic.
"""

from pymavlink import mavutil


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatSender:
    """
    HeartbeatSender class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
    ) -> "tuple[True, HeartbeatSender] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatSender object.
        """
        try:
            sender = cls(
                cls.__private_key,
                connection,
            )
            return [True, sender]
        except Exception as e:
            return [False, None]

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
    ):
        assert key is HeartbeatSender.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection

    def run(
        self,
        logger,
    ):
        """
        Attempt to send a heartbeat message.
        """
        try:
            self.connection.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0
            )
            logger.info("Heartbeat Sent")
        except Exception as e:
            logger.error(e)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
