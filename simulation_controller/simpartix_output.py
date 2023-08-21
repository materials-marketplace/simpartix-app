"""Model for the output of a SimPARTIX simulation."""


class SimPARTIXOutput:
    def __init__(self, id, elapsed_time, temperature, group, state_of_matter):
        self.id = id
        self.elapsed_time = elapsed_time
        self.temperature = temperature
        self.group = group
        self.state_of_matter = state_of_matter
