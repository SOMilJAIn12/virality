import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import multer from "multer";

const uploadDirectory = path.resolve(process.cwd(), "uploads");

fs.mkdirSync(uploadDirectory, { recursive: true });

const allowedExtensions = new Set([".mp4", ".mov", ".mkv", ".webm", ".avi"]);

const allowedMimeTypes = new Set([
  "video/mp4",
  "video/quicktime",
  "video/x-matroska",
  "video/webm",
  "video/x-msvideo",
]);

const maxUploadMb = Number(process.env.MAX_UPLOAD_MB || 100);

const storage = multer.diskStorage({
  destination: uploadDirectory,

  filename: (req, file, callback) => {
    const extension = path.extname(file.originalname).toLowerCase();

    callback(null, `${crypto.randomUUID()}${extension}`);
  },
});

function fileFilter(req, file, callback) {
  const extension = path.extname(file.originalname).toLowerCase();

  const hasValidExtension = allowedExtensions.has(extension);
  const hasValidMimeType = allowedMimeTypes.has(file.mimetype);

  if (!hasValidExtension || !hasValidMimeType) {
    const error = new Error(
      "Only MP4, MOV, MKV, WEBM, and AVI video files are allowed.",
    );

    error.code = "UNSUPPORTED_FORMAT";
    return callback(error);
  }

  callback(null, true);
}

export const uploadVideo = multer({
  storage,
  fileFilter,
  limits: {
    fileSize: maxUploadMb * 1024 * 1024,
  },
});
