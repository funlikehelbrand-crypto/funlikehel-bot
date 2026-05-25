// Chat log storage — saves every conversation to Vercel KV or stdout
// Called internally by /api/chat after each exchange

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method !== "POST") return res.status(405).end();

  const { question, answer, ip, country, city, ua, ts } = req.body || {};

  // Log to Vercel stdout — visible in Vercel Logs and can be exported
  const logEntry = JSON.stringify({
    type: "chat_log",
    ts: ts || new Date().toISOString(),
    question: (question || "").substring(0, 500),
    answer: (answer || "").substring(0, 500),
    ip: ip || "?",
    country: country || "?",
    city: city || "?",
    ua: (ua || "").substring(0, 200),
  });

  console.log(logEntry);

  return res.status(200).json({ ok: true });
}
