// Email opens report API — reads from GA4 with country breakdown
// Usage: GET https://surfiq.eu/api/opens?key=SECRET
// Returns JSON with opens per email, country, campaign

const GA_MEASUREMENT_ID = "G-T4HT1DG5RW";
const GA_API_SECRET = process.env.GA_API_SECRET || "";
const REPORT_KEY = process.env.REPORT_KEY || "surfiq2026";
const GA_PROPERTY_ID = "521481214";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  if (req.method === "OPTIONS") return res.status(200).end();

  // Simple auth
  if (req.query.key !== REPORT_KEY) {
    return res.status(401).json({ error: "Invalid key" });
  }

  // We can't query GA4 Data API from serverless without OAuth
  // So this endpoint returns whatever we can collect from the structured logs
  // The real magic is in px.js logging JSON to stdout with country from Vercel headers

  return res.status(200).json({
    message: "Use the Python script read_opens.py to get the full report",
    hint: "px.js now logs structured JSON with country/city from Vercel geo headers",
    ga4_note: "GA4 email_open events now include country and city params",
    pixel_format: "https://surfiq.eu/api/px?e=EMAIL&c=CAMPAIGN",
  });
}
