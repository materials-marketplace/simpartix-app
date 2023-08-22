import asyncio
import enum
import json
import logging
import os
import shutil
import subprocess
import threading
import time
import uuid

import dlite
from marketplace_standard_app_api.models.transformation import (
    TransformationState,
)

from models.transformation import TransformationInput
from simulation_controller.propartix_files_creation import (
    create_input_files,
    get_output_values,
)
from simulation_controller.simpartix_output import SimPARTIXOutput

SIMULATIONS_FOLDER_PATH = "/app/simulation_files"


class OutputStatus(enum.Enum):
    MISSING = 0
    COMPUTING = 1
    READY = 2


class Simulation:
    """Manage a single simulation."""

    def __init__(self, simulation_input: TransformationInput):
        self.id: str = str(uuid.uuid4())
        self.simulationPath = os.path.join(SIMULATIONS_FOLDER_PATH, self.id)
        create_input_files(self.simulationPath, simulation_input)
        self.parameters = simulation_input
        self._status: TransformationState = TransformationState.CREATED
        self._process = None
        self.output_status = OutputStatus.MISSING
        logging.info(
            f"Simulation '{self.id}' with "
            f"configuration {simulation_input} created."
        )

    @property
    def status(self) -> TransformationState:
        """Getter for the status.

        If the simulation is running, the process is checked for completion.

        Returns:
            TransformationState: status of the simulation
        """
        if self._status == TransformationState.RUNNING:
            process_status = self.process.poll()
            if process_status is None:
                return TransformationState.RUNNING
            elif process_status == 0:
                logging.info(f"Simulation '{self.id}' is completed.")
                if self.output_status == OutputStatus.MISSING:
                    logging.info(f"Preparing output for simulation {self.id}")
                    self.output_status = OutputStatus.COMPUTING
                    asyncio.run(self._prepare_output())
                elif self.output_status == OutputStatus.READY:
                    self.status = TransformationState.COMPLETED
            else:
                logging.error(f"Error occurred in simulation '{self.id}'.")
                self.status = TransformationState.FAILED
        return self._status

    @status.setter
    def status(self, value: TransformationState):
        self._status = value

    @property
    def process(self):
        return self._process

    @process.setter
    def process(self, value):
        self._process = value

    def run(self):
        """
        Start running a simulation.

        A new process that calls the SimPARTIX binary is spawned,
        and the output is stored in a separate directory

        Raises:
            RuntimeError: when the simulation is already in progress
        """
        if self.status == TransformationState.RUNNING:
            msg = f"Simulation '{self.id}' already in progress."
            logging.error(msg)
            raise RuntimeError(msg)
        outputPath = os.path.join(self.simulationPath, "output")
        if not os.path.isdir(outputPath):
            os.mkdir(outputPath)
        os.chdir(self.simulationPath)
        self.process = subprocess.Popen(["SimPARTIX"], stdout=subprocess.PIPE)
        self.status = TransformationState.RUNNING
        logging.info(f"Simulation '{self.id}' started successfully.")
        self._update_status()

    def _update_status(self) -> None:
        """Utility function that periodically triggers the status check.

        The purpose of this function is to generate the output files without
        having to wait for a request from the user. It is only relevant for
        running simulations, to know when they are done.
        """

        def _check_status():
            while self.status != TransformationState.COMPLETED:
                # print(f"{self.id}: {self.status}")
                time.sleep(10)

        status_thread = threading.Thread(target=_check_status)
        status_thread.start()

    async def _prepare_output(self) -> None:
        """
        Prepares the DLite output based on the generated vtk files.

        This method should be called once the simulation is done running.
        It will update the output_ready flag to show it is ready for the user.
        """
        logging.info(f"Preparing output for simulation '{self.id}'.")
        result = get_output_values(self.simulationPath)
        dlite_schema_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "SimPARTIXOutput.yml"
        )
        DLiteSimPARTIXOutput = dlite.classfactory(
            SimPARTIXOutput, url=f"yaml://{dlite_schema_path}"
        )
        simpartix_output = DLiteSimPARTIXOutput(
            id=self.id,
            elapsed_time=result["elapsed_time"],
            temperature=result["Temperature_SPH"],
            group=result["Group"],
            state_of_matter=result["StateOfMatter_SPH"],
        )
        output_path = os.path.join(self.simulationPath, "output")
        simpartix_output.dlite_inst.save(f"json://{output_path}.json?mode=w")
        self.output_status = OutputStatus.READY

    def get_output(self) -> str:
        """Get the output of a simulation

        Raises:
            RuntimeError: If the simulation has not finished

        Returns:
            str: data in json format
        """
        if self.output_status != OutputStatus.READY:
            msg = (
                f"Cannot download, simulation '{self.id}' "
                f"has status '{self.status.name}'."
            )
            logging.error(msg)
            raise RuntimeError(msg)

        file_path = os.path.join(self.simulationPath, "output.json")
        with open(file_path) as f:
            output = json.load(f)
            return output

    def stop(self):
        """Stop a running process.

        Raises:
            RuntimeError: if the simulation is not running
        """
        if self.process is None:
            msg = f"No process to stop. Is simulation '{self.id}' running?"

            logging.error(msg)
            raise RuntimeError(msg)
        self.process.terminate()
        self.status = TransformationState.STOPPED
        self.process = None
        logging.info(f"Simulation '{self.id}' stopped successfully.")

    def delete(self):
        """
        Delete all the simulation folders and files.

        Raises:
            RuntimeError: if deleting a running simulation
        """
        if self.status == TransformationState.RUNNING:
            msg = f"Simulation '{self.id}' is running."
            logging.error(msg)
            raise RuntimeError(msg)
        shutil.rmtree(self.simulationPath)
        logging.info(f"Simulation '{self.id}' and related files deleted.")
