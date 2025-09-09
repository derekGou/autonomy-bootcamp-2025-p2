"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ):
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        try:
            receiver = cls(cls.__private_key, connection, True, local_logger)
            return [True, receiver]
        except Exception as e:
            return False, None

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        state: bool,
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"
        self.connection = connection
        self.state = state
        self.local_logger = local_logger
        # Do any intializiation here

    def run(
        self,
    ):
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """
        try:
            msg = self.connection.recv_match(type="HEARTBEAT", blocking=False)

            if msg is not None:
                self.missed_count = 0
                self.state = "Connected"
            else:
                self.missed_count += 1
                if self.missed_count >= 5:
                    self.state = False
                    self.local_logger.warning("Lost connection to drone!", True)

            # Report state every second
            self.local_logger.info(f"Current state: {self.state}", True)

        except Exception as e:
            self.local_logger.error(f"Error receiving heartbeat: {e}", True)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
