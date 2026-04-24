"""
Aktualizuje strone /ekipa/ na WordPress:
- przywraca formularz zapisu
- zmienia URL z Render na WP REST API endpoint
"""
import base64, urllib.request, json

WP_URL = "https://funlikehel.pl"
AUTH = base64.b64encode(b"Admin:PDlm Q9wV AKvP tvlK uUEa 64zw").decode()
WP_ENDPOINT = "https://funlikehel.pl/wp-json/funlikehel/v1/ekipa"

new_content = """
<div style="background:linear-gradient(135deg,#0077b6,#00b4d8,#90e0ef);min-height:100vh;padding:20px;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:650px;margin:0 auto;text-align:center;">

<h1 style="color:white;font-size:2.5em;text-shadow:2px 2px 8px rgba(0,0,0,0.3);margin-bottom:5px;">&#x1F3C4; Do&#x142;&#x105;cz do ekipy FUN like HEL!</h1>
<p style="color:white;font-size:1.3em;text-shadow:1px 1px 4px rgba(0,0,0,0.2);">Otwieramy sezon! Zgarnij <strong style="color:#ffe66d;">-10% na zaj&#x119;cia i sprz&#x119;t sportowy</strong></p>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:15px;margin:25px 0;">
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">Kite</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">Windsurf</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">Wing</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">Wake</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">SUP</span>
</div>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:20px;margin:25px 0;">
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<h3 style="color:#0077b6;margin:8px 0;">Jastarnia</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Maj &mdash; wrzesie&#x144;<br>P&#x142;ytka woda Zatoki Puckiej</p>
</div>
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<h3 style="color:#0077b6;margin:8px 0;">Hurghada</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Zima<br>Ciep&#x142;a woda, s&#x142;o&#x144;ce ca&#x142;y rok</p>
</div>
</div>

<div style="background:white;border-radius:20px;padding:35px;margin:25px auto;max-width:420px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">
<h2 style="color:#0077b6;margin-top:0;">Zapisz si&#x119; do ekipy!</h2>
<p style="color:#666;margin-bottom:20px;">Wype&#x142;nij formularz i zgarnij kupon <strong style="color:#e63946;">-10%</strong></p>

<form id="ekipa-form">
<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Twoje imi&#x119;</label>
<input type="text" name="name" required placeholder="np. Kasia" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;outline:none;">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Email</label>
<input type="email" name="email" required placeholder="twoj@email.pl" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;outline:none;">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Numer telefonu</label>
<input type="tel" name="phone" placeholder="690 270 032" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;outline:none;">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Jaki sport Ci&#x119; interesuje?</label>
<select name="sport" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;background:white;">
<option value="">Wybierz...</option>
<option value="kitesurfing">Kitesurfing</option>
<option value="windsurfing">Windsurfing</option>
<option value="wing">Wing / Wingfoil</option>
<option value="wakeboarding">Wakeboarding</option>
<option value="sup">SUP</option>
<option value="pumpfoil">Pumpfoil</option>
<option value="nie-wiem">Nie wiem jeszcze &mdash; doradzicie!</option>
</select>

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Gdzie chcesz p&#x142;ywa&#x107;?</label>
<div style="text-align:left;margin-top:5px;">
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="jastarnia" style="margin-right:8px;"> Jastarnia (maj &mdash; wrzesie&#x144;)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="egipt" style="margin-right:8px;"> Egipt / Hurghada (zima)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="oba" style="margin-right:8px;"> Oba!</label>
</div>

<button type="submit" style="width:100%;margin-top:20px;padding:16px;background:linear-gradient(135deg,#0077b6,#00b4d8);color:white;border:none;border-radius:12px;font-size:1.15em;font-weight:bold;cursor:pointer;box-shadow:0 4px 15px rgba(0,119,182,0.4);">Zapisuj&#x119; si&#x119;!</button>
</form>

<div id="ekipa-success" style="display:none;margin-top:20px;padding:25px;background:linear-gradient(135deg,#d4edda,#c3e6cb);border-radius:12px;">
<h2 style="color:#155724;margin-top:0;">Jeste&#x15B; w ekipie!</h2>
<p style="color:#155724;font-size:1.1em;">Wys&#x142;ali&#x15B;my Ci kupon <strong>-10% na zaj&#x119;cia i sprz&#x119;t sportowy</strong>.</p>
<p style="color:#155724;">Masz pytania? Zadzwo&#x144;: <a href="tel:+48690270032" style="color:#0077b6;font-weight:bold;">690 270 032</a></p>
</div>
</div>

<script>
document.getElementById("ekipa-form").addEventListener("submit", function(e) {
  e.preventDefault();
  var form = this;
  var btn = form.querySelector("button");
  btn.textContent = "Wysylam...";
  btn.disabled = true;
  var data = {
    name: form.querySelector("[name=name]").value,
    email: form.querySelector("[name=email]").value,
    phone: form.querySelector("[name=phone]").value,
    sport: form.querySelector("[name=sport]").value,
    locations: Array.from(form.querySelectorAll("[name=location]:checked")).map(function(cb){return cb.value;})
  };
  fetch("https://funlikehel.pl/wp-json/funlikehel/v1/ekipa", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  }).then(function(r){return r.json();}).then(function(d){
    if(d.status === "ok") {
      form.style.display="none";
      document.getElementById("ekipa-success").style.display="block";
    } else {
      btn.textContent = "Zapisuje sie!";
      btn.disabled = false;
      alert(d.message || "Ups, cos poszlo nie tak. Zadzwon: 690 270 032");
    }
  }).catch(function(){
    btn.textContent = "Zapisuje sie!";
    btn.disabled = false;
    alert("Ups, cos poszlo nie tak. Zadzwon: 690 270 032");
  });
});
</script>

<div style="text-align:center;margin-top:30px;padding:20px;color:rgba(255,255,255,0.85);font-size:0.9em;">
<p><strong>FUN like HEL | Szkola Kite Wind</strong></p>
<p>Jastarnia &amp; Hurghada</p>
<p>Tel: <a href="tel:+48690270032" style="color:white;">690 270 032</a> | <a href="mailto:funlikehelbrand@gmail.com" style="color:white;">funlikehelbrand@gmail.com</a></p>
</div>

</div>
</div>
"""

payload = json.dumps({"content": new_content}).encode("utf-8")
req = urllib.request.Request(
    f"{WP_URL}/wp-json/wp/v2/pages/2189",
    data=payload,
    method="POST",
    headers={
        "Authorization": f"Basic {AUTH}",
        "Content-Type": "application/json",
        "User-Agent": "Python",
    },
)
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.load(resp)
    print("Status:", result.get("status"))
    print("Modified:", result.get("modified"))
    rendered = result.get("content", {}).get("rendered", "")
    if "funlikehel/v1/ekipa" in rendered:
        print("OK: URL zmieniony na WP endpoint!")
    elif "onrender" in rendered:
        print("UWAGA: nadal stary URL Render")
    else:
        print("Sprawdz URL recznie")
