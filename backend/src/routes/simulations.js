import { Router } from "express";

import {
  createSimulation,
  getSimulationStatus,
  listSimulations,
} from "../controllers/simulationsController.js";
import { simulationRateLimiter } from "../middleware/rateLimit.js";
import { uploadVideo } from "../middleware/upload.js";

const router = Router();

router.post(
  "/",
  simulationRateLimiter,
  uploadVideo.single("video"),
  createSimulation,
);

router.get("/", listSimulations);
router.get("/:simulationId", getSimulationStatus);

export default router;
