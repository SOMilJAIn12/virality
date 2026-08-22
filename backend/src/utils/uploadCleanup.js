import fs from "node:fs/promises";
import path from "node:path";

const uploadDirectory = path.resolve(process.cwd(), "uploads");

const maxAgeHours = Number(process.env.UPLOAD_MAX_AGE_HOURS || 1);

const cleanupIntervalMinutes = Number(
  process.env.UPLOAD_CLEANUP_INTERVAL_MINUTES || 15,
);

export async function cleanupExpiredUploads() {
  try {
    await fs.mkdir(uploadDirectory, { recursive: true });

    const files = await fs.readdir(uploadDirectory, {
      withFileTypes: true,
    });

    const expirationTime = Date.now() - maxAgeHours * 60 * 60 * 1000;

    await Promise.all(
      files
        .filter((file) => file.isFile())
        .map(async (file) => {
          const filePath = path.join(uploadDirectory, file.name);
          const metadata = await fs.stat(filePath);

          if (metadata.mtimeMs < expirationTime) {
            await fs.unlink(filePath);
            console.log(`Removed expired upload: ${file.name}`);
          }
        }),
    );
  } catch (error) {
    console.error("Upload cleanup failed:", error.message);
  }
}

export function startUploadCleanup() {
  cleanupExpiredUploads();

  const interval = setInterval(
    cleanupExpiredUploads,
    cleanupIntervalMinutes * 60 * 1000,
  );

  interval.unref();
}
