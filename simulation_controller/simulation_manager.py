import logging

from marketplace_standard_app_api.models.transformation import (
    TransformationState,
)

from simulation_controller.simulation import Simulation

mappings = {
    "SimpartixOutput": {
        "name": "SimpartixOutput",
        "properties": {
            "temperature": "http://emmo.info/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "group": "http://emmo.info/emmo#EMMO_0cd58641_824c_4851_907f_f4c3be76630c",
            "state_of_matter": "http://emmo.info/emmo#EMMO_b9695e87_8261_412e_83cd_a86459426a28",
        },
    },
}


class SimulationManager:
    def __init__(self):
        self.simulations: dict = {}

    def _get_simulation(self, job_id: str) -> Simulation:
        """
        Get the simulation corresponding to the job_id.

        Args:
            job_id (str): unique id of he simulation

        Raises:
            KeyError: if there is no simulation matching the id

        Returns:
            Simulation instance
        """
        try:
            simulation = self.simulations[job_id]
            return simulation
        except KeyError as ke:
            message = f"Simulation with id '{job_id}' not found"
            logging.error(message)
            raise KeyError(message) from ke

    def _add_simulation(self, simulation: Simulation) -> str:
        """Append a simulation to the internal datastructure.

        Args:
            simulation (Simulation): Object to add

        Returns:
            str: ID of the added object
        """
        job_id: str = simulation.job_id
        self.simulations[job_id] = simulation
        return job_id

    def _delete_simulation(self, job_id: str):
        """Remove a simulation from the internal datastructure.

        Args:
            job_id (str): id of the simulation to remove
        """
        del self.simulations[job_id]

    def create_simulation(self, request_obj: dict) -> str:
        """Create a new simulation given the arguments.

        Args:
           requestObj: dictionary containing input configuration

        Returns:
            str: unique job id
        """
        return self._add_simulation(Simulation(request_obj))

    def run_simulation(self, job_id: str):
        """Execute a simulation.

        Args:
            job_id (str): unique simulation id
        """
        self._get_simulation(job_id).run()

    def get_simulation_output(self, job_id: str) -> str:
        """Get the output a simulation.

        Args:
            job_id (str): unique simulation id

        Returns:
            str: json representation of the dlite object
        """
        simulation = self._get_simulation(job_id)
        return simulation.get_output()

    def stop_simulation(self, job_id: str) -> dict:
        """Force termination of a simulation.

        Args:
            job_id (str): unique id of the simulation
        """
        self._get_simulation(job_id).stop()

    def delete_simulation(self, job_id: str) -> dict:
        """Delete all the simulation information.

        Args:
            job_id (str): unique id of simulation
        """
        self._get_simulation(job_id).delete()
        self._delete_simulation(job_id)

    def get_simulation_state(self, job_id: str) -> TransformationState:
        """Return the status of a particular simulation.

        Args:
            job_id (str): id of the simulation

        Returns:
            TransformationState: status of the simulation
        """
        return self._get_simulation(job_id).status

    def get_simulations(self) -> dict:
        """Return unique ids of all the simulations.

        Returns:
            list: list of simulation ids
        """
        items = []
        for simulation in self.simulations.values():
            items.append(
                {
                    "id": simulation.job_id,
                    "parameters": simulation.parameters,
                    "state": simulation.status,
                }
            )
        return items
