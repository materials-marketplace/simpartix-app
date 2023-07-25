"""Model for the output of a SimPARTIX simulation."""


class SimPARTIXOutput:
    def __init__(self, temperature, group, state_of_matter):
        self.temperature = temperature
        self.group = group
        self.state_of_matter = state_of_matter
