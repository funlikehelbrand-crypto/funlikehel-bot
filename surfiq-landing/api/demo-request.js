// API endpoint: receives demo request form, sends email notification, logs to stdout
import https from 'https';

const SMTP_HOST = process.env.SMTP_HOST || 'serwer2620595.home.pl';
const SMTP_USER = process.env.SMTP_USER || 'office@surfiq.eu';
const SMTP_PASS = process.env.SMTP_PASS || '';
const NOTIFY_EMAIL = 'lukasz.michalina@gmail.com';
const CC_EMAIL = 'office@surfiq.eu';

// Rate limit: max 5 demo requests per IP per hour
const demoRateMap = new Map();
function checkDemoRate(ip) {
  const now = Date.now();
  const entry = demoRateMap.get(ip) || { count: 0, reset: now + 3600000 };
  if (now > entry.reset) { entry.count = 0; entry.reset = now + 3600000; }
  entry.count++;
  demoRateMap.set(ip, entry);
  return entry.count <= 5;
}

// Escape HTML to prevent XSS in notification emails
function esc(s) { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

export default async function handler(req, res) {
  // CORS — only surfiq.eu
  const origin = req.headers.origin || "";
  const allowed = origin.includes("surfiq.eu") ? origin : "https://surfiq.eu";
  res.setHeader('Access-Control-Allow-Origin', allowed);
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const ip = (req.headers['x-forwarded-for'] || '127.0.0.1').split(',')[0].trim();
  if (!checkDemoRate(ip)) {
    return res.status(429).json({ error: 'Too many requests. Please try again later.' });
  }

  const d = req.body;
  if (!d.first_name || !d.last_name || !d.email || !d.phone || !d.company) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  // Log to Vercel stdout (always visible in Vercel Logs)
  const logLine = JSON.stringify({
    event: 'demo_request',
    ts: new Date().toISOString(),
    name: `${d.first_name} ${d.last_name}`,
    email: d.email,
    phone: d.phone,
    company: d.company,
    website: d.website || '',
    type: d.business_type || '',
    country: d.country || '',
    city: d.city || '',
    scale: d.scale || '',
    sports: d.sports || '',
    interests: d.interests || '',
    current_software: d.current_software || '',
    software_pain: d.software_pain || '',
    source: d.source || '',
    language: d.language || 'pl',
    referrer: d.referrer || '',
    ip: req.headers['x-forwarded-for'] || '?'
  });
  console.log(`[DEMO] ${logLine}`);

  // Send email notification via SMTP (nodemailer not available — use fetch to Render endpoint)
  // Fallback: use Vercel's built-in fetch to call our own server for email delivery
  try {
    // Try sending via our Render server's email endpoint
    const emailPayload = {
      to: NOTIFY_EMAIL,
      cc: CC_EMAIL,
      subject: `[SurfIQ Demo] ${d.first_name} ${d.last_name} — ${d.company}`,
      html: buildEmailHTML(d)
    };

    // Fire-and-forget to Render server
    fetch('https://funlikehel.onrender.com/api/send-notification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(emailPayload)
    }).catch(() => {});

    // Also send via simple HTTPS webhook to Gmail (backup)
    // Log is our primary source of truth
  } catch (e) {
    console.error('[DEMO] Email send error:', e.message);
  }

  // GA4 Measurement Protocol event
  const GA_API_SECRET = process.env.GA_API_SECRET || '';
  if (GA_API_SECRET) {
    fetch(`https://www.google-analytics.com/mp/collect?measurement_id=G-T4HT1DG5RW&api_secret=${GA_API_SECRET}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: `demo_${d.email}_${Date.now()}`,
        events: [{
          name: 'demo_request_server',
          params: { company: d.company, country: d.country, source: d.source, language: d.language }
        }]
      })
    }).catch(() => {});
  }

  return res.status(200).json({ ok: true, message: 'Demo request received' });
}

function buildEmailHTML(d) {
  return `
  <div style="font-family:Poppins,Arial,sans-serif;max-width:600px;margin:0 auto;background:#081D3A;color:#fff;border-radius:16px;overflow:hidden">
    <div style="background:linear-gradient(135deg,#0D47A1,#081D3A);padding:24px 32px;text-align:center">
      <h1 style="margin:0;font-size:22px;color:#14D1C9">Nowy wniosek o demo SurfIQ</h1>
    </div>
    <div style="padding:24px 32px">
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr><td style="padding:8px 0;color:#8EA4BF;width:140px">Imie i nazwisko</td><td style="padding:8px 0;font-weight:600">${esc(d.first_name)} ${esc(d.last_name)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Email</td><td style="padding:8px 0"><a href="mailto:${esc(d.email)}" style="color:#14D1C9">${esc(d.email)}</a></td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Telefon</td><td style="padding:8px 0"><a href="tel:${esc(d.phone)}" style="color:#14D1C9">${esc(d.phone)}</a></td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Firma</td><td style="padding:8px 0;font-weight:600">${esc(d.company)}</td></tr>
        ${d.website ? `<tr><td style="padding:8px 0;color:#8EA4BF">Strona www</td><td style="padding:8px 0">${esc(d.website)}</td></tr>` : ''}
        <tr><td style="padding:8px 0;color:#8EA4BF">Typ</td><td style="padding:8px 0">${esc(d.business_type)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Kraj / Miasto</td><td style="padding:8px 0">${esc(d.country)} / ${esc(d.city)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Skala</td><td style="padding:8px 0">${esc(d.scale)}</td></tr>
        <tr style="border-top:1px solid rgba(255,255,255,.1)"><td style="padding:12px 0 8px;color:#14D1C9;font-weight:600" colspan="2">Sporty i zainteresowania</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Sporty w ofercie</td><td style="padding:8px 0;font-weight:600">${esc(d.sports)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Zainteresowania</td><td style="padding:8px 0">${esc(d.interests)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Aktualny software</td><td style="padding:8px 0;font-weight:600">${esc(d.current_software)}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Problem z obecnym</td><td style="padding:8px 0;font-style:italic">${esc(d.software_pain)}</td></tr>
        <tr style="border-top:1px solid rgba(255,255,255,.1)"><td style="padding:12px 0 8px;color:#8EA4BF" colspan="2"></td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Zrodlo</td><td style="padding:8px 0">${d.source || '-'}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Jezyk</td><td style="padding:8px 0">${(d.language || 'pl').toUpperCase()}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">Data</td><td style="padding:8px 0">${d.submitted_at || new Date().toISOString()}</td></tr>
        <tr><td style="padding:8px 0;color:#8EA4BF">IP</td><td style="padding:8px 0">${d.ip || '-'}</td></tr>
      </table>
      <div style="margin-top:24px;padding:16px;background:rgba(20,209,201,.1);border:1px solid rgba(20,209,201,.3);border-radius:12px;text-align:center">
        <p style="margin:0 0 8px;font-size:13px;color:#8EA4BF">Nastepny krok:</p>
        <p style="margin:0;font-size:15px;font-weight:600;color:#14D1C9">Przygotuj demo i odpowiedz na ${d.email}</p>
      </div>
    </div>
    <div style="padding:16px 32px;text-align:center;font-size:11px;color:#5a7a9a;border-top:1px solid rgba(255,255,255,.08)">
      SurfIQ &mdash; surfiq.eu
    </div>
  </div>`;
}
