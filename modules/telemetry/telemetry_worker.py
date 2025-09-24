"""
Telemtry worker that gathers GPS data.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import telemetry
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def telemetry_worker(
    connection: mavutil.mavfile,
    controller: worker_controller.WorkerController,
    queue: queue_proxy_wrapper.QueueProxyWrapper,
) -> None:
    """
    Worker process.

    connection: mavutil connection for sending messages
    controller: controls start/stop of worker
    queue: message/information queue for communication
    period: telemetry timeout period
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
    # Instantiate class object (telemetry.Telemetry)
    result, telemetry_object = telemetry.Telemetry.create(connection, local_logger)
    if not result:
        local_logger.error("Failed to create telemetry object", True)
        return
    # Main loop: do work.
    local_logger.info("Telemetry worker started", True)

    while not controller.is_exit_requested():
        telemetry_data = telemetry_object.run()
        if telemetry_data:
            queue.queue.put(telemetry_data)
            local_logger.info(f"Telemetry data queued: {telemetry_data}", False)
        else:
            local_logger.info("No data received")
        time.sleep(0.1)

    local_logger.info("Telemetry worker stopped", True)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
