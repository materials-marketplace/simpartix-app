import os

import numpy as np
import propartix as px

from models.transformation import TransformationInput


def create_input_files(foldername: str, simulation_input: TransformationInput):
    """
    Function to create the start configuration for the MarketPlace simulation.

    simulation_input : TransformationInput
        instance with the specific configuration values for a run
    """
    if not os.path.isdir(foldername):
        os.mkdir(foldername)
    inputPath = os.path.join(foldername, "input")
    if not os.path.isdir(inputPath):
        os.mkdir(inputPath)
    particlesSPH = px.Particles("SPH")

    # particle spacing
    dp = 3.0e-6
    radiusScaling = 1.1
    substrateLayer = 30e-6

    PowderBedLength = 500e-6

    medianRadius = 0.5 * simulation_input.sphereDiameter
    sigma = 0.2

    centers, radii = px.createRandomFortran(
        lowerCorner=[-0.5 * PowderBedLength, -0.5 * PowderBedLength, 0.0],
        upperCorner=[
            0.5 * PowderBedLength,
            0.5 * PowderBedLength,
            PowderBedLength,
        ],
        volumeFraction=simulation_input.phi,
        distributionType="lognormal",
        mean=medianRadius,
        width=sigma,
        is2d=True,
        isPeriodic=False,
        tryLimit=1000000,
    )

    # bounding box for creating SPH particles
    lowerCorner = [-0.5 * PowderBedLength + 0.5 * dp, 0.0, 0.0]
    upperCorner = [
        0.5 * PowderBedLength,
        0.0,
        simulation_input.powderLayerHeight,
    ]

    centersInBox = px.cutBoxByMinMax(
        data=centers,
        positions=centers,
        lowerCorner=np.array(lowerCorner) + np.array([0.0, 0.0, 0.5 * dp]),
        upperCorner=upperCorner,
    )

    radiiInBox = px.cutBoxByMinMax(
        data=radii,
        positions=centers,
        lowerCorner=np.array(lowerCorner) + np.array([0.0, 0.0, 0.5 * dp]),
        upperCorner=upperCorner,
    )

    positions = px.createLattice(
        lowerCorner=[-0.5 * PowderBedLength, 0.0, 0.5 * dp],
        upperCorner=[
            0.5 * PowderBedLength,
            0.0,
            simulation_input.powderLayerHeight
            + simulation_input.sphereDiameter * 3,
        ],
        particleSpacing=dp,
        is2d=True,
    )

    positions, group = px.cutSpheres(
        data=positions,
        positions=positions,
        radius=radiiInBox * radiusScaling,
        centers=centersInBox,
        shell=0.0,
        inner=True,
        sphereIndex=True,
    )

    particlesSPH = px.Particles("SPH")
    particlesSPH.activate(whichQuantity=px.quantity["group"])

    particlesSPH.addParticles(newPosition=positions, newType=0)

    particlesSPH.write(
        data=group, whichQuantity=px.quantity["group"], which=px.select["ALL"]
    )

    px.numberConsecutively(particlesSPH.group)
    particlesSPH.group += 1

    # create solidified layer
    pos2 = px.createLattice(
        lowerCorner=[-0.5 * PowderBedLength - 3 * dp, 0.0, -substrateLayer],
        upperCorner=[0.5 * PowderBedLength + 3 * dp, 0.0, 0.0],
        particleSpacing=dp,
        is2d=True,
        latticeType=px.lattice["SIMPLE"],
    )

    particlesSPH.addParticles(newPosition=pos2, newType=0)

    # create ground
    particlesSPH.setType(
        particleType=1,
        which=particlesSPH.position[:, 2] < -substrateLayer + 3 * dp,
    )

    particlesSPH.setType(
        particleType=1,
        which=particlesSPH.position[:, 0] < -0.5 * PowderBedLength,
    )

    particlesSPH.setType(
        particleType=1,
        which=particlesSPH.position[:, 0] > 0.5 * PowderBedLength,
    )

    particlesSPH.centerPosition()

    px.writeH5Part(foldername + "/input/startconf.h5part", particlesSPH)

    # compute intermediate variables
    simulationTime = PowderBedLength / simulation_input.laserSpeed

    spread = particlesSPH.getSpread()

    templateDirPath = os.path.relpath(
        "/app/simulation_controller/templates", start=os.curdir
    )

    # Create simulation.conf
    fout = open(foldername + "/input/simulation.conf", "w")
    with open(
        os.path.join(templateDirPath, "simulation.template")
    ) as simulationContent:
        fout.write(
            f"{simulationContent.read()}".format(
                simulationTime=simulationTime,
                outputInterval=simulationTime / 60.0,
                spreadX=spread[0],
                spreadZ=spread[2] * 1.1,
            )
        )
    fout.close()

    # Create sph.conf
    fout = open(foldername + "/input/sph.conf", "w")
    with open(os.path.join(templateDirPath, "sph.template")) as sphConfContent:
        fout.write(sphConfContent.read())
    fout.close()

    # Create sphMaterialProperties.csv
    fout = open(foldername + "/input/sphMaterialProperties.csv", "w")
    with open(
        os.path.join(templateDirPath, "sphMaterialProperties.template")
    ) as sphMaterialPropertiesContent:
        fout.write(sphMaterialPropertiesContent.read())
    fout.close()

    # Create laser.dat
    fout = open(foldername + "/input/laser.dat", "w")
    with open(os.path.join(templateDirPath, "laser.template")) as laserContent:
        fout.write(
            f"{laserContent.read()}".format(
                laserPower=simulation_input.laserPower * 0.2,
                simulationTime=simulationTime,
                varianceLaser=1.0e-5,
                laserTravelDistance=(PowderBedLength - 4 * (1.0e-5))
                / 2.0,  # reduced by standard deviation of the laser
            )
        )
    fout.close()

    # Create surfaceTension.dat
    fout = open(foldername + "/input/surfaceTension.dat", "w")
    with open(
        os.path.join(templateDirPath, "surfaceTension.template")
    ) as surfaceTensionContent:
        fout.write(surfaceTensionContent.read())
    fout.close()


def get_output_values(basePath: str) -> dict:
    vtk_path = create_micress_files(basePath)

    elapsed_time = px.getH5PartTime(
        filename=os.path.join(basePath, "output", "output.h5part"),
        allFrames=True,
    )
    result = {"elapsed_time": elapsed_time}
    for i in range(len(elapsed_time)):
        px.vtkToDlite(os.path.join(vtk_path, f"frame_{i:04d}.vtk"), result)
    return result


def create_micress_files(basePath: str) -> list:
    micress_path = os.path.join(basePath, "micress")
    output_path = os.path.join(basePath, "output", "output.h5part")
    vtk_path = os.path.join(micress_path, "frame_%04d.vtk")
    # frame = px.getH5PartFrames(output_path) - 1
    if not os.path.isdir(micress_path):
        os.mkdir(micress_path)

    # default of the conversion window should be extracted from the simulation
    lowerCorner = px.getH5PartBoxDimensions(output_path, frame=0)[0]
    upperCorner = px.getH5PartBoxDimensions(output_path, frame=0)[1]

    # Micress asked for a single slice, so reduce the conversion windows
    # xRange = (upperCorner[0] - lowerCorner[0]) / 8.0
    # lowerCorner[0] = -xRange
    # upperCorner[0] = xRange

    # initiate conversion from h5part to vtk
    px.h5partToVtk(
        h5partFilename=output_path,
        vtkPattern=vtk_path,
        isVtkTypeCellData=True,
        # frames=[0, 1],
        lowerCorner=lowerCorner,
        upperCorner=upperCorner,
        makeAverage=False,
        smoothingLength=None,
        particleSpacing=None,
        density=None,
        resolution=3.9e-6,
        isEnforceEqualSpacing=True,
        isShepardFilter=True,
        quantitiesToBeMapped=["Group", "Temperature_SPH", "StateOfMatter_SPH"],
        quantitiesToBeMappedByClosestNeighbor=["Group", "StateOfMatter_SPH"],
        defaultInCaseOfAbsenceOfClosestNeighbor=[1],
        isBinaryVtk=False,
        isApplyMicressConvention=True,
        micressSubstrateThreshold=0,
        micressLiquidThreshold=1,
    )
    return micress_path


def generate_preview(basepath: str):
    path = os.path.join(basepath, "pic")
    if not os.path.isdir(path):
        os.mkdir(path)
    os.chdir(path)

    px.h5partToVtk(
        h5partFilename="output/output.h5part",
        vtkPattern="output/converted-%04d.vtk",
        quantitiesToBeMapped=["Temperature_SPH"],
    )

    px.vtkToPng(
        vtkRegExPattern=r"output/converted-\d*.vtk",
        pngPattern="pic/output-%04d.png",
        quantityName="Temperature_SPH",
    )

    os.system(
        r"mencoder -of avi -ovc x264 -fps 8 -nosound -o movie.avi mf://pic/\*.png"
    )
