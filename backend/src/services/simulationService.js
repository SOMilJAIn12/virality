import { databaseQuery } from "../config/db.js";

export async function createSimulationRecord({
  simulationId,
  videoFilename,
  seed,
}) {
  await databaseQuery(
    `
      INSERT INTO simulations (id, status, video_filename, seed)
      VALUES ($1, 'PENDING', $2, $3)
    `,
    [simulationId, videoFilename, seed ?? null],
  );
}

export async function findSimulationRecord(simulationId) {
  const result = await databaseQuery(
    `
      SELECT
        id,
        status,
        video_filename,
        seed,
        virality_score,
        error_message,
        result,
        created_at,
        updated_at
      FROM simulations
      WHERE id = $1
    `,
    [simulationId],
  );

  return result.rows[0] ?? null;
}

export async function saveSimulationStatus(simulation) {
  const isCompleted = simulation.status === "COMPLETED";
  const isFailed = simulation.status === "FAILED";

  if (!isCompleted && !isFailed) {
    return;
  }

  const viralityScore = isCompleted
    ? (simulation.result?.virality_score ?? null)
    : null;

  await databaseQuery(
    `
      UPDATE simulations
      SET
        status = $2,
        virality_score = $3,
        error_message = $4,
        result = $5::jsonb,
        updated_at = NOW()
      WHERE id = $1
    `,
    [
      simulation.simulationId,
      simulation.status,
      viralityScore,
      simulation.error ?? null,
      simulation.result ? JSON.stringify(simulation.result) : null,
    ],
  );
}

export async function listSimulationRecords() {
  const result = await databaseQuery(
    `
      SELECT
        id,
        status,
        virality_score,
        created_at,
        updated_at
      FROM simulations
      ORDER BY created_at DESC
      LIMIT 50
    `,
  );

  return result.rows.map((row) => ({
    simulationId: row.id,
    status: row.status,
    viralityScore: row.virality_score,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }));
}
