"""
Command worker to make decisions based on Telemetry Data.
"""

import os
import pathlib

from pymavlink import mavutil

from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from . import command
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def command_worker(
    connection: mavutil.mavfile,
    target: command.Position,
    data_queue: queue_proxy_wrapper.QueueProxyWrapper,
    response_queue: queue_proxy_wrapper.QueueProxyWrapper,
    controller: worker_controller.WorkerController,
    # Add other necessary worker arguments here
) -> None:
    """
    Worker process.

    connection: mavlink connection for sending messages
    target: target position
    data_queue: queue to read test telemetry data
    response_queue: queue to pass results to
    controller: worker controller to control running/stopping of command worker
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
    # Instantiate class object (command.Command)
    result, command_worker_object = command.Command.create(
        connection,
        target,
        local_logger=local_logger,
    )
    if not result:
        local_logger.error("Failed to create CommandWorker", True)
        return
    # Main loop: do work.
    while not controller.is_exit_requested():
        controller.check_pause()
        try:
            if not data_queue.queue.empty():
                telemetry_data = data_queue.queue.get()
                if telemetry_data:
                    queues = command_worker_object.run(telemetry_data)
                for q in queues:
                    response_queue.queue.put(q)
        except (OSError, ValueError, EOFError) as e:
            local_logger.error(f"Error in command worker: {e}", True)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
