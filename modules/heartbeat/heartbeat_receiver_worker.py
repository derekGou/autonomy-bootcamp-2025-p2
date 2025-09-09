"""
Heartbeat worker that sends heartbeats periodically.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import heartbeat_receiver
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_receiver_worker(
    connection: mavutil.mavfile,
    controller: worker_controller.WorkerController,
    queue: queue_proxy_wrapper.QueueProxyWrapper,
    period: int,
) -> None:
    """
    Worker process.

    connection: MAVUtil connection object that is used to send out heartbeats
    period: time period between heartbeats
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (heartbeat_receiver.HeartbeatReceiver)
    result, receiver = heartbeat_receiver.HeartbeatReceiver.create(
        connection, local_logger=local_logger
    )
    if not result:
        local_logger.error("Failed to create HeartbeatReceiver", True)
        return
    # Main loop: do work.

    while not controller.is_exit_requested():
        receiver.run()
        current_state = receiver.state
        queue.queue.put(current_state)
        local_logger.info(f"Current state: {current_state}", True)
        time.sleep(period)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
