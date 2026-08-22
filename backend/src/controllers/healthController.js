export function getHealth(req, res) {
  res.status(200).json({
    success: true,
    data: {
      express: "ok",
      timestamp: new Date().toISOString(),
    },
  });
}
