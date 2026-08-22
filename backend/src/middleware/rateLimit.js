import rateLimit from "express-rate-limit";

const windowMs = Number(process.env.SIMULATION_RATE_LIMIT_WINDOW_MS || 900000);

const limit = Number(process.env.SIMULATION_RATE_LIMIT_MAX || 5);

export const simulationRateLimiter = rateLimit({
  windowMs,
  limit,
  standardHeaders: true,
  legacyHeaders: false,

  handler(req, res) {
    res.status(429).json({
      success: false,
      error: {
        code: "RATE_LIMIT_EXCEEDED",
        message: "Too many simulation requests. Please try again later.",
        status: 429,
      },
    });
  },
});
