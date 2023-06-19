"""Definition of the additional required data models."""

from pydantic import BaseModel, validator


class TransformationInput(BaseModel):
    laserPower: float = 150
    laserSpeed: float = 3.0
    sphereDiameter: float = 30e-6
    phi: float = 0.7
    powderLayerHeight: float = 60e-6

    @validator("sphereDiameter")
    def check_diameter(cls, v):
        if v <= 5e-6:
            raise ValueError("Sphere diameter value too small.")
        return v

    @validator("phi")
    def check_phi(cls, v):
        if v >= 1 or v < 0:
            raise ValueError("Phi must be between 0 and 1.")
        return v

    @validator("powderLayerHeight")
    def check_powderLayerHeight(cls, v, values):
        if v < values["sphereDiameter"]:
            raise ValueError(
                "Powder layer height must be at least the sphere diameter."
            )
        return v
