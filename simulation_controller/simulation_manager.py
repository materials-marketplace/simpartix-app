import logging
import threading
import time

from marketplace_standard_app_api.models.transformation import (
    TransformationState,
)

from simulation_controller.simulation import Simulation

mappings = {
    "SimpartixOutput": {
        "name": "SimpartixOutput",
        "properties": {
            # TODO: Add mapping for the elapsed_time
            "elapsed_time": "tbd",
            "temperature": "http://emmo.info/emmo#EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
            "group": "http://emmo.info/emmo#EMMO_0cd58641_824c_4851_907f_f4c3be76630c",
            "state_of_matter": "http://emmo.info/emmo#EMMO_b9695e87_8261_412e_83cd_a86459426a28",
        },
    },
}


class SimulationManager:
    def __init__(self):
        self.simulations: dict[str, Simulation] = {}
        self._check_statuses_background()

    def _check_statuses_background(self):
        def _check_statuses():
            while True:
                for simulation in self.simulations.values():
                    _ = simulation.status
                    # print(f"{simulation.id}: {simulation.status}")
                time.sleep(20)

        status_thread = threading.Thread(target=_check_statuses)
        status_thread.start()

    def _get_simulation(self, id: str) -> Simulation:
        """
        Get the simulation corresponding to the id.

        Args:
            id (str): unique id of he simulation

        Raises:
            KeyError: if there is no simulation matching the id

        Returns:
            Simulation instance
        """
        try:
            simulation = self.simulations[id]
            return simulation
        except KeyError as ke:
            message = f"Simulation with id '{id}' not found"
            logging.error(message)
            raise KeyError(message) from ke

    def _add_simulation(self, simulation: Simulation) -> str:
        """Append a simulation to the internal datastructure.

        Args:
            simulation (Simulation): Object to add

        Returns:
            str: ID of the added object
        """
        id: str = simulation.id
        self.simulations[id] = simulation
        return id

    def _delete_simulation(self, id: str):
        """Remove a simulation from the internal datastructure.

        Args:
            id (str): id of the simulation to remove
        """
        del self.simulations[id]

    def create_simulation(self, request_obj: dict) -> str:
        """Create a new simulation given the arguments.

        Args:
           requestObj: dictionary containing input configuration

        Returns:
            str: unique job id
        """
        return self._add_simulation(Simulation(request_obj))

    def run_simulation(self, id: str):
        """Execute a simulation.

        Args:
            id (str): unique simulation id
        """
        self._get_simulation(id).run()

    def get_simulation_output(self, id: str) -> str:
        """Get the output a simulation.

        Args:
            id (str): unique simulation id

        Returns:
            str: json representation of the dlite object
        """
        simulation = self._get_simulation(id)
        return simulation.get_output()

    def stop_simulation(self, id: str) -> dict:
        """Force termination of a simulation.

        Args:
            id (str): unique id of the simulation
        """
        self._get_simulation(id).stop()

    def delete_simulation(self, id: str) -> dict:
        """Delete all the simulation information.

        Args:
            id (str): unique id of simulation
        """
        self._get_simulation(id).delete()
        self._delete_simulation(id)

    def get_simulation_state(self, id: str) -> TransformationState:
        """Return the status of a particular simulation.

        Args:
            id (str): id of the simulation

        Returns:
            TransformationState: status of the simulation
        """
        return self._get_simulation(id).status

    def get_simulations(self) -> dict:
        """Return unique ids of all the simulations.

        Returns:
            list: list of simulation ids
        """
        items = []
        for simulation in self.simulations.values():
            items.append(
                {
                    "id": simulation.id,
                    "parameters": simulation.parameters,
                    "state": simulation.status,
                }
            )
        return items
