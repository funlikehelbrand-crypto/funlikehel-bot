// Tracking pixel — logs email opens to GA4 with country/city from Vercel geo headers
// Usage: <img src="https://surfiq.eu/api/px?e=EMAIL&c=CAMPAIGN" width="1" height="1">

const GA_MEASUREMENT_ID = "G-T4HT1DG5RW";
const GA_API_SECRET = process.env.GA_API_SECRET || "";

// 1x1 transparent GIF
const PIXEL = Buffer.from(
  "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
  "base64"
);

export default async function handler(req, res) {
  const email = req.query.e || "";
  const campaign = req.query.c || "";
  const legacyId = req.query.id || "";
  const recipientId = email || legacyId || "unknown";
  const campaignName = campaign || "unknown";
  const ip = (req.headers["x-forwarded-for"] || "").split(",")[0].trim();
  const ua = req.headers["user-agent"] || "";
  const country = req.headers["x-vercel-ip-country"] || "";
  const city = decodeURIComponent(req.headers["x-vercel-ip-city"] || "");
  const region = req.headers["x-vercel-ip-country-region"] || "";
  const ts = Date.now();

  // Fire GA4 event with country/city
  if (GA_API_SECRET) {
    fetch(
      `https://www.google-analytics.com/mp/collect?measurement_id=${GA_MEASUREMENT_ID}&api_secret=${GA_API_SECRET}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: `email_${recipientId}_${ts}`,
          events: [
            {
              name: "email_open",
              params: {
                recipient_id: recipientId,
                recipient_email: email,
                campaign: campaignName,
                country: country,
                city: city,
                engagement_time_msec: 1,
              },
            },
          ],
        }),
      }
    ).catch(() => {});
  }

  // Structured JSON log (Vercel stdout)
  console.log(
    JSON.stringify({
      event: "email_open",
      email,
      campaign: campaignName,
      country,
      city,
      region,
      ip,
      ts: new Date().toISOString(),
    })
  );

  // Return 1x1 transparent GIF
  res.setHeader("Content-Type", "image/gif");
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  res.status(200).send(PIXEL);
}
