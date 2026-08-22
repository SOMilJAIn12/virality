import fs from "node:fs";

import axios from "axios";
import FormData from "form-data";

const pythonServiceUrl = (
  process.env.PYTHON_SERVICE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

const client = axios.create({
  baseURL: pythonServiceUrl,
  timeout: 15000,
});

export class PythonServiceError extends Error {
  constructor(code, message, status = 502) {
    super(message);

    this.name = "PythonServiceError";
    this.code = code;
    this.status = status;
  }
}

export async function startSimulation(file, seed) {
  const form = new FormData();

  form.append("video", fs.createReadStream(file.path), {
    filename: file.originalname,
    contentType: file.mimetype,
  });

  if (seed !== undefined) {
    form.append("seed", String(seed));
  }

  try {
    const response = await client.post("/simulate", form, {
      headers: form.getHeaders(),
    });

    return response.data;
  } catch (error) {
    throw toPythonServiceError(error);
  }
}

export async function getSimulation(simulationId) {
  try {
    const response = await client.get(`/simulate/${simulationId}`);

    return response.data;
  } catch (error) {
    throw toPythonServiceError(error);
  }
}

function toPythonServiceError(error) {
  if (!error.response) {
    return new PythonServiceError(
      "PYTHON_SERVICE_UNAVAILABLE",
      "The Python simulation service is unavailable.",
    );
  }

  if (error.response.status === 404) {
    return new PythonServiceError(
      "SIMULATION_NOT_FOUND",
      "Simulation not found.",
      404,
    );
  }

  return new PythonServiceError(
    "PYTHON_SERVICE_ERROR",
    "The Python simulation service returned an error.",
  );
}
