// Unsubscribe endpoint — logs opt-out requests
// POST /api/unsubscribe { email: "...", ts: "..." }

export default async function handler(req, res) {
  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  const { email, ts } = req.body || {};

  if (!email) return res.status(400).json({ error: "Email required" });

  // Log to Vercel stdout (visible in Vercel Logs dashboard)
  console.log(`[UNSUBSCRIBE] email=${email} ts=${ts || new Date().toISOString()} ip=${req.headers["x-forwarded-for"] || "?"}`);

  return res.status(200).json({ ok: true, email, message: "Unsubscribed successfully" });
}
