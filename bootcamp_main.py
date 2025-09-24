"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
TELEMETRY_QUEUE_MAXSIZE = 100
COMMAND_QUEUE_MAXSIZE = 50
HEARTBEAT_QUEUE_MAXSIZE = 10

# Set worker counts
NUM_HEARTBEAT_SENDERS = 1
NUM_HEARTBEAT_RECEIVERS = 1
NUM_TELEMETRY_WORKERS = 1
NUM_COMMAND_WORKERS = 1

# Any other constants
TELEMETRY_PERIOD = 1
HEARTBEAT_PERIOD = 1
TARGET = (10, 20, 30)

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues
    manager = mp.Manager()

    # Create queues
    receiver_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, TELEMETRY_QUEUE_MAXSIZE)
    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, TELEMETRY_QUEUE_MAXSIZE)
    command_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, COMMAND_QUEUE_MAXSIZE)
    heartbeat_queue = queue_proxy_wrapper.QueueProxyWrapper(manager, HEARTBEAT_QUEUE_MAXSIZE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    workers = []

    # Heartbeat sender
    result, hb_send_props = worker_manager.WorkerProperties.create(
        count=NUM_HEARTBEAT_SENDERS,
        target=heartbeat_sender_worker.heartbeat_sender_worker,
        work_arguments=(connection, HEARTBEAT_PERIOD),
        input_queues=[],
        output_queues=[],
        controller=controller,
        local_logger=main_logger,
    )
    if result:
        result, hb_send_manager = worker_manager.WorkerManager.create(hb_send_props, main_logger)
        if result:
            workers.append(hb_send_manager)

    # Heartbeat receiver
    result, hb_receive_props = worker_manager.WorkerProperties.create(
        count=NUM_HEARTBEAT_RECEIVERS,
        target=heartbeat_receiver_worker.heartbeat_receiver_worker,
        work_arguments=(
            connection,
            HEARTBEAT_PERIOD,
        ),
        input_queues=[],
        output_queues=[receiver_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if result:
        result, hb_receiver_manager = worker_manager.WorkerManager.create(
            hb_receive_props, main_logger
        )
        if result:
            workers.append(hb_receiver_manager)

    # Telemetry
    result, telemetry_props = worker_manager.WorkerProperties.create(
        count=NUM_TELEMETRY_WORKERS,
        target=telemetry_worker.telemetry_worker,
        work_arguments=(connection),
        input_queues=[],
        output_queues=[telemetry_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if result:
        result, telemetry_manager = worker_manager.WorkerManager.create(
            telemetry_props, main_logger
        )
        if result:
            workers.append(telemetry_manager)

    # Command
    result, command_props = worker_manager.WorkerProperties.create(
        count=NUM_COMMAND_WORKERS,
        target=command_worker.command_worker,
        work_arguments=(
            connection,
            TARGET,
            TELEMETRY_PERIOD,
        ),
        input_queues=[telemetry_queue],
        output_queues=[command_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if result:
        result, command_manager = worker_manager.WorkerManager.create(command_props, main_logger)
        if result:
            workers.append(command_manager)

    # Create the workers (processes) and obtain their managers

    # Start worker processes
    for manager in workers:
        manager.start_workers()
    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    # Continue running for 100 seconds or until the drone disconnects
    curr_time = time.time()
    while (time.time() - curr_time) <= 100:
        for q in (command_queue, telemetry_queue, heartbeat_queue):
            try:
                res = q.queue.get_nowait()  # non-blocking
                if res:
                    if res == "Disconnected":
                        break
                    main_logger.info(f"Main received: {res}", False)
            except queue.Empty:
                continue
    # Stop the processes
    controller.request_exit()
    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START
    for q in (command_queue, telemetry_queue, heartbeat_queue):
        q.fill_and_drain_queue()
    main_logger.info("Queues cleared")

    # Clean up worker processes
    for manager in workers:
        manager.join_workers()
    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
