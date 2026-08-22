import pg from "pg";

const { Pool } = pg;

let pool;

export class DatabaseError extends Error {
  constructor(message) {
    super(message);

    this.name = "DatabaseError";
    this.code = "DATABASE_ERROR";
    this.status = 500;
  }
}

function getPool() {
  if (pool) {
    return pool;
  }

  const connectionString = process.env.DATABASE_URL;

  if (!connectionString) {
    throw new DatabaseError("DATABASE_URL is not configured.");
  }

  pool = new Pool({
    connectionString,
    ssl:
      process.env.DATABASE_SSL === "true"
        ? { rejectUnauthorized: false }
        : false,
  });

  return pool;
}

export async function databaseQuery(query, values = []) {
  try {
    return await getPool().query(query, values);
  } catch (error) {
    console.error("Database error:", error.message);

    throw new DatabaseError("The database operation failed.");
  }
}

export async function initializeDatabase() {
  await databaseQuery(`
    CREATE TABLE IF NOT EXISTS simulations (
      id TEXT PRIMARY KEY,
      status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')
      ),
      video_filename TEXT,
      seed INTEGER,
      virality_score NUMERIC,
      error_message TEXT,
      result JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS simulations_created_at_idx
      ON simulations (created_at DESC);
  `);
}
