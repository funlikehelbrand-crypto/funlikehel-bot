// Vercel Serverless Function — SurfIQ Chat Bot
// Uses Anthropic Claude API (claude-haiku for speed & cost)
// Sends conversation report to office@surfiq.eu after each reply

export default async function handler(req, res) {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { message, history = [] } = req.body || {};
  if (!message) return res.status(400).json({ error: 'No message' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ reply: 'Bot jest tymczasowo niedostępny. Napisz do nas: office@surfiq.eu!' });

  const systemPrompt = `Jesteś chatbotem SurfIQ — systemu operacyjnego dla szkół sportów wodnych i outdoorowych (kite, wind, wing, SUP, eFoil, carver, wakeboard).

Twoja rola: pomagasz właścicielom szkół zrozumieć, jak SurfIQ może usprawnić ich działalność. Odpowiadasz po polsku (lub w języku użytkownika). Jesteś uprzejmy, konkretny, profesjonalny ale ciepły.

FUNKCJE SURFIQ:
- SurfIQ Core (599 PLN/mies.): kalendarz rezerwacji, CRM kursantów (do 200), grafik instruktorów (do 3), 1 lokalizacja, prognoza pogody, dashboard finansowy, sklep, 1 kanał AI (100 rozmów), alerty pogodowe, 14-dniowy trial
- Moduły dodatkowe:
  - AI & automatyzacja: dodatkowy kanał AI (199 PLN), pakiet 500 rozmów (149 PLN), lead scoring (99 PLN), semi-auto AI (199 PLN), full-auto AI (399 PLN), raporty AI (79 PLN)
  - Operacje: dodatkowa lokalizacja (199 PLN/spot), dodatkowi instruktorzy (49 PLN/os.), CRM rozszerzony (99 PLN/1000), wypożyczki (149 PLN), transfery MEWIA (99 PLN), obozy/półkolonie (199 PLN), KiteSafari (indywidualnie), zaawansowany grafik (99 PLN)
  - Pogoda: Windguru (79 PLN), multi-źródła (149 PLN), prognoza obłożenia (99 PLN)
  - Finanse: zaawansowane finanse (149 PLN), koszty operacyjne (79 PLN), płatności online (99 PLN + prowizja)
  - Enterprise: custom branding (499 PLN jednorazowo), API+webhooks (299 PLN), dedykowane wdrożenie (od 2000 PLN)
- Gotowe konfiguracje: Starter (599 PLN), Growth (1499 PLN), Scale (2999 PLN)

KONTAKT: office@surfiq.eu, demo na surfiq.eu/demo/
LOKALIZACJE DEMO: Hel (Polska), Hurghada (Egipt)
TRIAL: 14 dni za darmo, bez karty kredytowej

ZASADY:
- Odpowiadaj krótko (max 3-4 zdania)
- Zawsze kończ CTA: "Chcesz demo?", "Napisz na office@surfiq.eu", "Sprawdź surfiq.eu/demo/"
- Nie wymyślaj funkcji, których nie ma
- Przy pytaniach o cenę podawaj konkretne kwoty
- Zbieraj informacje: nazwa szkoły, lokalizacja, ilu instruktorów, jakie sporty, co ich interesuje`;

  const messages = [];
  // Add history (last 10 messages)
  for (const h of history.slice(-10)) {
    if (h.role === 'user' || h.role === 'assistant') {
      messages.push({ role: h.role, content: h.content });
    }
  }
  // Add current message
  messages.push({ role: 'user', content: message });

  try {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 300,
        system: systemPrompt,
        messages,
      }),
    });

    const data = await resp.json();
    const reply = data.content?.[0]?.text || 'Przepraszam, nie mogę teraz odpowiedzieć. Napisz na office@surfiq.eu!';

    // Send report email (best-effort, non-blocking)
    sendReport(message, reply, history).catch(() => {});

    return res.status(200).json({ reply });
  } catch (err) {
    console.error('Chat error:', err);
    return res.status(200).json({ reply: 'Przepraszam, wystąpił problem. Napisz do nas: office@surfiq.eu!' });
  }
}

// Send conversation report via email (SMTP or external service)
async function sendReport(userMessage, botReply, history) {
  // Use Formspree as simple webhook for reports
  try {
    await fetch('https://formspree.io/f/xeogqvgr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        _subject: `SurfIQ Bot — rozmowa: "${userMessage.slice(0, 50)}"`,
        message: userMessage,
        bot_reply: botReply,
        history_length: history.length,
        timestamp: new Date().toISOString(),
        source: 'surfiq-chat-bot',
      }),
    });
  } catch {
    // ignore — report is best-effort
  }
}
