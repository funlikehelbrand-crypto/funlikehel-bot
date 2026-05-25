// Unsubscribe endpoint — logs opt-out and sends notification email
// GET /api/unsubscribe?e=EMAIL (from email link click)
// POST /api/unsubscribe { email: "..." } (from form)

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "https://surfiq.eu");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();

  // Support both GET (email link) and POST (form)
  let email;
  if (req.method === "GET") {
    email = req.query.e || req.query.email || "";
  } else if (req.method === "POST") {
    email = (req.body || {}).email || "";
  } else {
    return res.status(405).json({ error: "Method not allowed" });
  }

  if (!email || !email.includes("@")) {
    return res.status(400).json({ error: "Valid email required" });
  }

  email = email.toLowerCase().trim();

  // Log to Vercel stdout with structured JSON
  console.log(JSON.stringify({
    event: "unsubscribe",
    email,
    ip: (req.headers["x-forwarded-for"] || "").split(",")[0].trim(),
    country: req.headers["x-vercel-ip-country"] || "",
    ts: new Date().toISOString(),
  }));

  // Send notification to admin so they can update the local unsub file
  const NOTIFY_URL = process.env.UNSUB_NOTIFY_URL || "";
  if (NOTIFY_URL) {
    fetch(NOTIFY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, ts: new Date().toISOString() }),
    }).catch(() => {});
  }

  // For GET requests (email link click), redirect to confirmation page
  if (req.method === "GET") {
    return res.redirect(302, `/unsubscribe.html?done=1&e=${encodeURIComponent(email)}`);
  }

  return res.status(200).json({ ok: true, email, message: "Unsubscribed successfully" });
}
