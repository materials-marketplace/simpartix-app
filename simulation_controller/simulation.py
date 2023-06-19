import logging
import os
import shutil
import subprocess
import uuid
from typing import Tuple

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


class Simulation:
    """Manage a single simulation."""

    def __init__(self, simulation_input: TransformationInput):
        self.job_id: str = str(uuid.uuid4())
        self.simulationPath = os.path.join(
            SIMULATIONS_FOLDER_PATH, self.job_id
        )
        create_input_files(self.simulationPath, simulation_input)
        self.parameters = simulation_input
        self._status: TransformationState = TransformationState.CREATED
        self._process = None
        logging.info(
            f"Simulation '{self.job_id}' with "
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
                logging.info(f"Simulation '{self.job_id}' is now completed.")
                self.status = TransformationState.COMPLETED
            else:
                logging.error(f"Error occured in simulation '{self.job_id}'.")
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
            msg = f"Simulation '{self.job_id}' already in progress."
            logging.error(msg)
            raise RuntimeError(msg)
        outputPath = os.path.join(self.simulationPath, "output")
        if not os.path.isdir(outputPath):
            os.mkdir(outputPath)
        os.chdir(self.simulationPath)
        self.process = subprocess.Popen(["SimPARTIX"], stdout=subprocess.PIPE)
        self.status = TransformationState.RUNNING
        logging.info(f"Simulation '{self.job_id}' started successfully.")

    def stop(self):
        """Stop a running process.

        Raises:
            RuntimeError: if the simulation is not running
        """
        if self.process is None:
            msg = f"No process to stop. Is simulation '{self.job_id}' running?"

            logging.error(msg)
            raise RuntimeError(msg)
        self.process.terminate()
        self.status = TransformationState.STOPPED
        self.process = None
        logging.info(f"Simulation '{self.job_id}' stopped successfully.")

    def get_output(self) -> Tuple[str]:
        """Get the output of a simulation

        Raises:
            RuntimeError: If the simulation has not run

        Returns:
            Tuple[str]: data in json format
                        semantic mapping for the data
                        mimetype of the data
        """
        result = get_output_values(self.simulationPath)

        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "SimPARTIXOutput.json"
        )
        DLiteSimPARTIXOutput = dlite.classfactory(
            SimPARTIXOutput, url=f"json://{path}"
        )
        if self.status in (
            TransformationState.RUNNING,
            TransformationState.CREATED,
        ):
            msg = (
                f"Cannot download, simulation '{self.job_id}' "
                f"has status '{self.status.name}'."
            )
            logging.error(msg)
            raise RuntimeError(msg)
        simpartix_output = DLiteSimPARTIXOutput(
            temperature=result["Temperature_SPH"],
            group=result["Group"],
            state_of_matter=result["StateOfMatter_SPH"],
        )
        # Store the output as a file for posterity
        file_path = os.path.join(self.simulationPath, self.job_id)
        simpartix_output.dlite_inst.save(f"json://{file_path}.json?mode=w")
        return simpartix_output.dlite_inst.asjson()

    def delete(self):
        """
        Delete all the simulation folders and files.

        Raises:
            RuntimeError: if deleting a running simulation
        """
        if self.status == TransformationState.RUNNING:
            msg = f"Simulation '{self.job_id}' is running."
            logging.error(msg)
            raise RuntimeError(msg)
        shutil.rmtree(self.simulationPath)
        logging.info(f"Simulation '{self.job_id}' and related files deleted.")
