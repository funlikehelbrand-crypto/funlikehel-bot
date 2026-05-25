# SurfIQ — Wycena wartości aplikacji

## Metoda 1: Koszt odtworzenia (Development Cost)

### Frontend (React Native + Expo)
| Moduł | Estymacja godzin | Stawka (PLN/h) | Koszt |
|-------|-----------------|----------------|-------|
| Auth (login, register, role-based) | 40h | 200 | 8 000 |
| Dashboard | 60h | 200 | 12 000 |
| Kalendarz (drag&drop, filtry, pogoda) | 120h | 200 | 24 000 |
| Rezerwacje (CRUD, 4-step form, edycja) | 100h | 200 | 20 000 |
| Obecność (attendance, IKO tracking) | 30h | 200 | 6 000 |
| CRM kursantów (profil, historia, waivers) | 80h | 200 | 16 000 |
| Instruktorzy (profil, grafik, certyfikaty) | 60h | 200 | 12 000 |
| Finanse (revenue, rentowność, zaległości) | 80h | 200 | 16 000 |
| Pogoda (3 źródła, róża wiatrów) | 40h | 200 | 8 000 |
| Transfer 2nd Spot (transfer, koszty, pojemność) | 40h | 200 | 8 000 |
| Sprzęt (inwentarz, serwis, alerty) | 40h | 200 | 8 000 |
| Pakiety sesji | 30h | 200 | 6 000 |
| Płatności (rejestracja, statusy) | 30h | 200 | 6 000 |
| Usługi (katalog, edycja) | 30h | 200 | 6 000 |
| Obozy/Półkolonie (turnusy, uczestnicy) | 60h | 200 | 12 000 |
| Raporty wizualne (wykresy, export) | 40h | 200 | 8 000 |
| HR/Payroll (wynagrodzenia, wydatki) | 40h | 200 | 8 000 |
| Analytics/Usage tracking | 30h | 200 | 6 000 |
| Sklep/Katalog produktów | 20h | 200 | 4 000 |
| Ustawienia (motyw, hasło, preferencje) | 20h | 200 | 4 000 |
| Design system (kolory, ciemny/jasny motyw) | 40h | 200 | 8 000 |
| Responsive (mobile + desktop layout) | 60h | 200 | 12 000 |
| **Frontend łącznie** | **1 090h** | | **218 000 PLN** |

### Backend (Supabase)
| Element | Estymacja godzin | Stawka | Koszt |
|---------|-----------------|--------|-------|
| Schema design (17 tabel, 10 enumów) | 40h | 250 | 10 000 |
| RLS policies (row-level security) | 30h | 250 | 7 500 |
| Migrations & seed data | 20h | 250 | 5 000 |
| Auth configuration | 15h | 250 | 3 750 |
| Import danych z poprzedniego systemu (1111 kursantów) | 20h | 250 | 5 000 |
| Open-Meteo integration | 10h | 250 | 2 500 |
| Audit logging | 10h | 250 | 2 500 |
| **Backend łącznie** | **145h** | | **36 250 PLN** |

### AI & Automatyzacja (system agentów)
| Element | Estymacja godzin | Stawka | Koszt |
|---------|-----------------|--------|-------|
| Agent Instagram (DM + komentarze) | 80h | 250 | 20 000 |
| Agent Facebook (strona + grupy + lead scoring) | 60h | 250 | 15 000 |
| Agent WhatsApp (Cloud API) | 40h | 250 | 10 000 |
| Agent Gmail (polling, anti-loop) | 40h | 250 | 10 000 |
| Agent YouTube (komentarze, upload) | 30h | 250 | 7 500 |
| Agent TikTok (publikacja, hashtagi) | 30h | 250 | 7 500 |
| Agent SMS (kampanie, tracking) | 30h | 250 | 7 500 |
| Content Agent (6-fazowy) | 40h | 250 | 10 000 |
| Video Agent (Pillow + ffmpeg) | 30h | 250 | 7 500 |
| Bosman (koordynator zespołu) | 20h | 250 | 5 000 |
| Persona AI (Claude integration) | 40h | 250 | 10 000 |
| Anti-spam, anti-loop, token refresh | 30h | 250 | 7 500 |
| **AI łącznie** | **470h** | | **117 500 PLN** |

### DevOps & Infrastruktura
| Element | Estymacja | Koszt |
|---------|-----------|-------|
| Vercel deploy + CI/CD | 15h | 3 750 |
| Render deploy (backend) | 10h | 2 500 |
| DNS, domeny, SSL | 5h | 1 250 |
| Monitoring (UptimeRobot) | 5h | 1 250 |
| **DevOps łącznie** | **35h** | **8 750 PLN** |

### ŁĄCZNY KOSZT ODTWORZENIA
| Warstwa | Godziny | Koszt |
|---------|---------|-------|
| Frontend | 1 090h | 218 000 PLN |
| Backend | 145h | 36 250 PLN |
| AI & Automatyzacja | 470h | 117 500 PLN |
| DevOps | 35h | 8 750 PLN |
| **RAZEM** | **1 740h** | **380 500 PLN** |

**Przy stawce 150 PLN/h:** 261 000 PLN
**Przy stawce 200 PLN/h:** 348 000 PLN
**Przy stawce 250 PLN/h:** 435 000 PLN

---

## Metoda 2: Wartość rynkowa (Market Value)

### Porównanie z konkurencją
| System | Cena/mies. | Funkcje | Nasz odpowiednik |
|--------|-----------|---------|-----------------|
| Systemy legacy | ~200-500 PLN | Rezerwacje, CRM | Mamy + pogoda + AI |
| Bsport | €49-199/mies. | Booking, CRM (fitness) | Brak pogody, brak kite workflow |
| Bookeo | $40-400/mies. | Generic booking | Zero sportów wodnych |
| Mindbody | $139-699/mies. | Fitness studio | Nie dla kite/surf |

### Wycena SaaS (Revenue Multiple)
- **Scenariusz rok 1:** 17 klientów × 200 PLN avg = 3 400 PLN MRR = **40 800 PLN ARR**
- **Scenariusz rok 2:** 50 klientów × 250 PLN avg = 12 500 PLN MRR = **150 000 PLN ARR**
- **SaaS multiple:** 5-10x ARR (early stage)
- **Wycena rok 2:** 150 000 × 5 = **750 000 PLN** (low) do **1 500 000 PLN** (high)

### Wartość IP (Intellectual Property)
- Wiedza domenowa: workflow szkoły kite — **bezcenne** (żaden software house tego nie ma)
- Dane pogodowe: 3 źródła + Transfer 2nd Spot — **unikalne na rynku**
- AI agenci: 12 agentów przetestowanych 6 miesięcy — **know-how wart 100-200k PLN**
- Social proof: 1000+ kursantów, 321k PLN — **trudne do powtórzenia**

---

## Metoda 3: Wartość dla klienta (Customer Value)

### Ile klient oszczędza?
- **Czas właściciela:** 2-3h/dzień × 120 dni × 100 PLN/h = **24 000 - 36 000 PLN/sezon**
- **Czas instruktorów:** 30 min/dzień × 10 osób × 120 dni × 50 PLN/h = **30 000 PLN/sezon**
- **Utracone rezerwacje** (chaos, brak odpowiedzi): 5-10% = **16 000 - 32 000 PLN/sezon**
- **Łączna wartość dla klienta:** **70 000 - 98 000 PLN/sezon**
- **Cena SurfIQ:** 2 988 - 5 988 PLN/rok = **ROI 12-33x**

---

## Podsumowanie wyceny

| Metoda | Wartość |
|--------|--------|
| Koszt odtworzenia | **350 000 - 435 000 PLN** |
| Revenue multiple (rok 2) | **750 000 - 1 500 000 PLN** |
| IP + know-how | **100 000 - 200 000 PLN** (dodatkowe) |

### **Rekomendowana wycena: 400 000 - 600 000 PLN**

To uwzględnia:
- Gotowy, przetestowany produkt (0 dodatkowego developmentu)
- Social proof (1000+ kursantów, 2 sezony)
- AI agenci (12 botów, 6 kanałów, 6 miesięcy know-how)
- Brak realnej konkurencji w niszy
- Dual-location (Polska + Egipt)
- 17 tabel, 22 ekrany, 4 role użytkowników
