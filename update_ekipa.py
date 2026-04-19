"""Jednorazowy skrypt — aktualizacja strony /ekipa na WordPress."""
import httpx, base64

auth = base64.b64encode(b"Admin:PDlm Q9wV AKvP tvlK uUEa 64zw").decode()

new_content = """
<div style="background:linear-gradient(135deg,#0077b6,#00b4d8,#90e0ef);min-height:100vh;padding:20px;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:650px;margin:0 auto;text-align:center;">

<h1 style="color:white;font-size:2.5em;text-shadow:2px 2px 8px rgba(0,0,0,0.3);margin-bottom:5px;">\U0001f3c4 Dołącz do ekipy FUN like HEL!</h1>
<p style="color:white;font-size:1.3em;text-shadow:1px 1px 4px rgba(0,0,0,0.2);">Otwieramy sezon! Zgarnij <strong style="color:#ffe66d;">-10% na zajęcia i sprzęt sportowy</strong></p>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:15px;margin:25px 0;">
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001fa81 Kite</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f3c4 Windsurf</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001fabd Wing</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f3cb Wake</span>
<span style="background:rgba(255,255,255,0.2);padding:10px 18px;border-radius:20px;color:white;font-size:1.1em;">\U0001f6f6 SUP</span>
</div>

<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:20px;margin:25px 0;">
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<div style="font-size:2em;">\U0001f1f5\U0001f1f1</div>
<h3 style="color:#0077b6;margin:8px 0;">Jastarnia</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Maj \u2014 wrzesień<br>Płytka woda Zatoki Puckiej<br>Idealnie dla początkujących i pro!</p>
</div>
<div style="background:white;border-radius:16px;padding:20px;width:260px;box-shadow:0 4px 15px rgba(0,0,0,0.15);">
<div style="font-size:2em;">\U0001f1ea\U0001f1ec</div>
<h3 style="color:#0077b6;margin:8px 0;">Hurghada</h3>
<p style="color:#555;font-size:0.95em;margin:0;">Zima<br>Ciepła woda, słońce cały rok<br>Cabrinha Test Center!</p>
</div>
</div>

<div style="background:white;border-radius:20px;padding:35px;margin:25px auto;max-width:420px;box-shadow:0 8px 30px rgba(0,0,0,0.2);">
<h2 style="color:#0077b6;margin-top:0;">Zapisz się do ekipy! \U0001f919</h2>
<p style="color:#666;margin-bottom:20px;">Wypełnij formularz i zgarnij kupon <strong style="color:#e63946;">-10%</strong></p>

<form id="ekipa-form">
<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Twoje imię</label>
<input type="text" name="name" required placeholder="np. Kasia" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Email</label>
<input type="email" name="email" required placeholder="twoj@email.pl" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Numer telefonu</label>
<input type="tel" name="phone" placeholder="690 270 032" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;transition:border-color 0.3s;outline:none;" onfocus="this.style.borderColor='#0077b6'" onblur="this.style.borderColor='#e0e0e0'">

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Jaki sport Cię interesuje?</label>
<select name="sport" style="width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:1em;box-sizing:border-box;background:white;">
<option value="">Wybierz...</option>
<option value="kitesurfing">Kitesurfing</option>
<option value="windsurfing">Windsurfing</option>
<option value="wing">Wing / Wingfoil</option>
<option value="wakeboarding">Wakeboarding</option>
<option value="sup">SUP</option>
<option value="pumpfoil">Pumpfoil</option>
<option value="nie-wiem">Nie wiem jeszcze \u2014 doradzicie!</option>
</select>

<label style="display:block;margin-top:12px;font-weight:600;color:#333;text-align:left;">Gdzie chcesz pływać?</label>
<div style="text-align:left;margin-top:5px;">
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="jastarnia" style="margin-right:8px;transform:scale(1.2);"> \U0001f1f5\U0001f1f1 Jastarnia (maj \u2014 wrzesień)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="egipt" style="margin-right:8px;transform:scale(1.2);"> \U0001f1ea\U0001f1ec Egipt / Hurghada (zima)</label>
<label style="display:block;padding:6px 0;font-size:1em;color:#444;"><input type="checkbox" name="location" value="oba" style="margin-right:8px;transform:scale(1.2);"> \U0001f30d Oba!</label>
</div>

<button type="submit" style="width:100%;margin-top:20px;padding:16px;background:linear-gradient(135deg,#0077b6,#00b4d8);color:white;border:none;border-radius:12px;font-size:1.15em;font-weight:bold;cursor:pointer;box-shadow:0 4px 15px rgba(0,119,182,0.4);transition:transform 0.2s,box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(0,119,182,0.5)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(0,119,182,0.4)'">Zapisuję się! \U0001f919</button>
</form>

<div id="ekipa-success" style="display:none;margin-top:20px;padding:25px;background:linear-gradient(135deg,#d4edda,#c3e6cb);border-radius:12px;">
<h2 style="color:#155724;margin-top:0;">Jesteś w ekipie! \U0001f389</h2>
<p style="color:#155724;font-size:1.1em;">Wysłaliśmy Ci kupon <strong>-10% na zajęcia i sprzęt sportowy</strong>.</p>
<p style="color:#155724;">Masz pytania? Zadzwoń: <a href="tel:+48690270032" style="color:#0077b6;font-weight:bold;">690 270 032</a></p>
</div>
</div>

<script>
document.getElementById('ekipa-form').addEventListener('submit', function(e) {
  e.preventDefault();
  var form = this;
  var btn = form.querySelector('button');
  btn.textContent = 'Wysyłam...';
  btn.disabled = true;
  var data = {
    name: form.querySelector('[name=name]').value,
    email: form.querySelector('[name=email]').value,
    phone: form.querySelector('[name=phone]').value,
    sport: form.querySelector('[name=sport]').value,
    locations: Array.from(form.querySelectorAll('[name=location]:checked')).map(function(cb){return cb.value;})
  };
  fetch('https://funlikehel-bot.onrender.com/api/ekipa', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }).then(function(r){return r.json();}).then(function(d){
    form.style.display='none';
    document.getElementById('ekipa-success').style.display='block';
  }).catch(function(err){
    btn.textContent = 'Zapisuję się!';
    btn.disabled = false;
    alert('Ups, coś poszło nie tak. Zadzwoń: 690 270 032');
  });
});
</script>

<div style="text-align:center;margin-top:30px;padding:20px;color:rgba(255,255,255,0.85);font-size:0.9em;">
<p style="margin:5px 0;"><strong>FUN like HEL | Szkoła Kite Wind</strong></p>
<p style="margin:5px 0;">Jastarnia \U0001f1f5\U0001f1f1 &amp; Hurghada \U0001f1ea\U0001f1ec</p>
<p style="margin:5px 0;">Tel: <a href="tel:+48690270032" style="color:white;">690 270 032</a> | <a href="mailto:funlikehelbrand@gmail.com" style="color:white;">funlikehelbrand@gmail.com</a></p>
<p style="margin:5px 0;"><a href="https://www.funlikehel.pl" style="color:white;">www.funlikehel.pl</a></p>
</div>

</div>
</div>
"""

resp = httpx.post(
    "https://funlikehel.pl/?rest_route=/wp/v2/pages/2189",
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    json={"content": new_content},
    timeout=20,
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("Strona zaktualizowana!")
else:
    print(resp.text[:300])
