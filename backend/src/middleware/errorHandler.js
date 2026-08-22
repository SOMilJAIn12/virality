import multer from "multer";

export function errorHandler(error, req, res, next) {
  if (error instanceof multer.MulterError && error.code === "LIMIT_FILE_SIZE") {
    const maxUploadMb = Number(process.env.MAX_UPLOAD_MB || 100);

    return res.status(413).json({
      success: false,
      error: {
        code: "FILE_TOO_LARGE",
        message: `Video must not exceed ${maxUploadMb}MB.`,
        status: 413,
      },
    });
  }

  if (error.code === "UNSUPPORTED_FORMAT") {
    return res.status(400).json({
      success: false,
      error: {
        code: "UNSUPPORTED_FORMAT",
        message: error.message,
        status: 400,
      },
    });
  }

  if (error.code === "PYTHON_SERVICE_UNAVAILABLE") {
    return res.status(502).json({
      success: false,
      error: {
        code: error.code,
        message: error.message,
        status: 502,
      },
    });
  }

  if (error.code === "PYTHON_SERVICE_ERROR") {
    return res.status(502).json({
      success: false,
      error: {
        code: error.code,
        message: error.message,
        status: 502,
      },
    });
  }

  if (error.code === "SIMULATION_NOT_FOUND") {
    return res.status(404).json({
      success: false,
      error: {
        code: error.code,
        message: error.message,
        status: 404,
      },
    });
  }

  if (error.code === "DATABASE_ERROR") {
    return res.status(500).json({
      success: false,
      error: {
        code: error.code,
        message: "A database error occurred.",
        status: 500,
      },
    });
  }

  console.error(error);

  return res.status(500).json({
    success: false,
    error: {
      code: "INTERNAL_SERVER_ERROR",
      message: "An unexpected server error occurred.",
      status: 500,
    },
  });
}
