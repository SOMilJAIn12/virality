import fs from "node:fs/promises";

import { getSimulation, startSimulation } from "../services/pythonClient.js";
import {
  createSimulationRecord,
  listSimulationRecords,
  saveSimulationStatus,
} from "../services/simulationService.js";

function parseSeed(value) {
  if (value === undefined || value === "") {
    return undefined;
  }

  const seed = Number(value);

  if (!Number.isInteger(seed)) {
    return null;
  }

  return seed;
}

export async function createSimulation(req, res, next) {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      error: {
        code: "NO_FILE",
        message: "Upload a video using the multipart field named 'video'.",
        status: 400,
      },
    });
  }

  const seed = parseSeed(req.body.seed);

  if (seed === null) {
    await fs.unlink(req.file.path).catch(() => {});

    return res.status(400).json({
      success: false,
      error: {
        code: "INVALID_SEED",
        message: "Seed must be an integer.",
        status: 400,
      },
    });
  }

  try {
    const simulation = await startSimulation(req.file, seed);

    await createSimulationRecord({
      simulationId: simulation.simulationId,
      videoFilename: req.file.originalname,
      seed,
    });

    return res.status(202).json({
      success: true,
      data: simulation,
    });
  } catch (error) {
    return next(error);
  } finally {
    await fs.unlink(req.file.path).catch(() => {});
  }
}

export async function getSimulationStatus(req, res, next) {
  try {
    const simulation = await getSimulation(req.params.simulationId);

    await saveSimulationStatus(simulation);

    return res.status(200).json({
      success: true,
      data: simulation,
    });
  } catch (error) {
    return next(error);
  }
}

export async function listSimulations(req, res, next) {
  try {
    const simulations = await listSimulationRecords();

    return res.status(200).json({
      success: true,
      data: simulations,
    });
  } catch (error) {
    return next(error);
  }
}
