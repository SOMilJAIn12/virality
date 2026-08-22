import "dotenv/config";

import app from "./src/app.js";
import { initializeDatabase } from "./src/config/db.js";
import { startUploadCleanup } from "./src/utils/uploadCleanup.js";

const port = Number(process.env.PORT || 4000);

async function startServer() {
  try {
    await initializeDatabase();
    startUploadCleanup();

    app.listen(port, () => {
      console.log(`Express API running at http://localhost:${port}`);
      console.log("PostgreSQL connection established.");
    });
  } catch (error) {
    console.error("Failed to start Express API:", error.message);
    process.exit(1);
  }
}

startServer();
