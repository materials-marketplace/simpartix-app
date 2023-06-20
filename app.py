"""Simple app for the SimPARTIX simulation code."""
import json
import logging

from fastapi import FastAPI, HTTPException, Response
from marketplace_standard_app_api.models.transformation import (
    TransformationCreateResponse,
    TransformationId,
    TransformationListResponse,
    TransformationStateResponse,
    TransformationUpdateModel,
    TransformationUpdateResponse,
)
from marketplace_standard_app_api.routers import object_storage

from models.transformation import TransformationInput
from simulation_controller.simulation_manager import (
    SimulationManager,
    mappings,
)

app = FastAPI()

simulation_manager = SimulationManager()


@app.get(
    "/heartbeat", operation_id="heartbeat", summary="Check if app is alive"
)
async def heartbeat():
    return "SimPARTIX app up and running"


@app.post(
    "/transformations",
    operation_id="newTransformation",
    summary="Create a new transformation",
    response_model=TransformationCreateResponse,
)
async def new_simulation(
    payload: TransformationInput,
) -> TransformationCreateResponse:
    job_id = simulation_manager.create_simulation(payload)
    return {"id": job_id}


@app.patch(
    "/transformations/{transformation_id}",
    summary="Update the state of the simulation.",
    response_model=TransformationUpdateResponse,
    operation_id="updateTransformation",
    responses={
        404: {"description": "Not Found."},
        409: {"description": "Requested state not available"},
        400: {"description": "Error executing update operation"},
    },
)
def update_simulation_state(
    transformation_id: TransformationId, payload: TransformationUpdateModel
) -> TransformationUpdateResponse:
    state = payload.state
    try:
        if state == "RUNNING":
            simulation_manager.run_simulation(str(transformation_id))
        elif state == "STOPPED":
            simulation_manager.stop_simulation(str(transformation_id))
        else:
            msg = f"{state} is not a supported state."
            raise HTTPException(status_code=400, detail=msg)
        return {"id": TransformationId(transformation_id), "state": state}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Transformation not found: {transformation_id}",
        )

    except RuntimeError as re:
        raise HTTPException(status_code=409, detail=re)
    except Exception as e:
        msg = (
            "Unexpected error while changing state of simulation "
            f"{transformation_id}. Error message: {e}"
        )
        logging.error(msg)
        raise HTTPException(status_code=400, detail=msg)


@app.get(
    "/transformations/{transformation_id}/state",
    summary="Get the state of the simulation.",
    response_model=TransformationStateResponse,
    operation_id="getTransformationState",
    responses={404: {"description": "Unknown simulation"}},
)
def get_simulation_state(
    transformation_id: TransformationId,
) -> TransformationStateResponse:
    """Get the state of a simulation.

    Args:
        transformation_id (TransformationId): ID of the simulation

    Returns:
        TransformationStateResponse: The state of the simulation.
    """
    try:
        state = simulation_manager.get_simulation_state(str(transformation_id))
        return {"id": transformation_id, "state": state}

    except KeyError:
        raise HTTPException(status_code=404, detail="Simulation not found")
    except Exception as e:
        msg = (
            "Unexpected error while querying for the status of simulation "
            f"{transformation_id}. Error message: {e}"
        )
        raise HTTPException(status_code=400, detail=msg)


@app.get(
    "/transformations",
    summary="Get all simulations.",
    response_model=TransformationListResponse,
    operation_id="getTransformationList",
)
def get_simulations():
    try:
        items: list = simulation_manager.get_simulations()

        logging.info(f"simulations: {items}")
        return {"items": items}
    except Exception as e:
        msg = (
            "Unexpected error while fetching the list of simulations. "
            f"Error message: {e}"
        )
        logging.error(msg)
        return Response(msg, status=400)


@app.delete(
    "/transformations/{transformation_id}",
    summary="Delete a transformation",
    operation_id="deleteTransformation",
)
def delete_simulation(transformation_id: TransformationId):
    try:
        simulation_manager.delete_simulation(str(transformation_id))
        return {
            "status": f"Simulation '{transformation_id}' deleted successfully!"
        }

    except KeyError as ke:
        raise HTTPException(status_code=404, detail=ke)
    except RuntimeError as re:
        raise HTTPException(status_code=400, detail=re)
    except Exception as e:
        msg = (
            "Unexpected error while deleting simulation "
            f"{transformation_id}. Error message: {e}"
        )
        raise HTTPException(status_code=400, detail=msg)


@app.get(
    "/results",
    summary="Get a simulation's result",
    operation_id="getDataset",
    responses={200: {"content": {"vnd.sintef.dlite+json"}}},
)
def get_results(
    collection_name: object_storage.CollectionName,
    dataset_name: object_storage.DatasetName,
    response: Response,
):
    json_payload = simulation_manager.get_simulation_output(str(dataset_name))
    response.headers["x-semantic-mappings"] = "SimpartixOutput"
    return json_payload


@app.get(
    "/mappings",
    summary="Get a list of the available mappings",
    operation_id="listSemanticMappings",
)
def list_mappings():
    return list(mappings.keys())


@app.get(
    "/mappings/{semantic_mapping_id}",
    summary="Get a specific mapping",
    operation_id="getSemanticMapping",
)
def get_mapping(semantic_mapping_id: str):
    mapping = json.dumps(mappings.get(semantic_mapping_id))
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping
