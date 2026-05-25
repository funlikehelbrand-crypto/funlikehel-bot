# SurfIQ — Pełna lista funkcjonalności

## Architektura
- **Frontend:** React Native + Expo (web + mobile)
- **Backend:** Supabase (PostgreSQL + Auth + RLS)
- **Deploy:** Vercel (web), Expo (mobile)
- **17 tabel w bazie danych**, 10 enumów, pełny RLS

---

## 1. Dashboard operacyjny
- Podsumowanie dnia: pogoda, lekcje, przychód
- Transfer 2nd Spot — alert przy niekorzystnym kierunku wiatru dla home spot
- Alerty: sprzęt w serwisie, konflikty w grafiku
- Szybkie akcje: nowa rezerwacja, oznacz obecność, dodaj płatność
- Przychód: dziś / tydzień / miesiąc / sezon z trendem

## 2. Kalendarz
- **Główny widok: godziny w pionie, instruktorzy w kolumnach** — układ znany z prognozy Windguru
- Widzisz godziny, kierunek i siłę wiatru jak w prognozie pogody
- Widok dzienny, tygodniowy, miesięczny + przełączanie klasyczny/godzinowy
- Kolory instruktorów (każdy ma przypisany hex)
- Drag & drop przesuwanie rezerwacji
- Warstwa pogodowa: live wiatr z Open-Meteo API
- Blokady (zła pogoda, urlopy, serwis)
- Filtry: lokalizacja, instruktor, sport
- Transfer 2nd Spot — alert nad kalendarzem
- Filtry sportów: Kite, Wind, Wing, SUP, Surf, Bosman

## 3. Rezerwacje
- **Lista:** wyszukiwanie po nazwisku, email, ref (FLH-2026-XXXX)
- **Filtry:** status (8 stanów), sezon (2025/2026), lokalizacja
- **Nowa rezerwacja — 4 kroki:**
  1. Wybór usługi (filtr lokalizacja + kategoria)
  2. Klient + data (wyszukaj istniejącego lub dodaj nowego)
  3. Instruktor + cena (z walidacją podwójnych rezerwacji)
  4. Notatki + metoda płatności
- **Rezerwacja cykliczna:** powtórz co tydzień (2-12 tygodni)
- **Statusy:** pending → confirmed → in_progress → completed / cancelled / no_show / rescheduled / weather_hold
- **Edycja:** zmiana terminu, instruktora, ceny (z ograniczeniami roli)
- **Archiwum:** soft-delete z powodem
- **Audit log:** każda zmiana statusu zapisana w booking_events

## 4. Obecność / Raport z lekcji
- Status: completed / no_show / cancelled (klient/pogoda/instruktor) / rescheduled
- Dane pogodowe: wiatr (węzły), warunki
- Notatki instruktora (technika, postęp)
- Ocena kursanta (1-5 gwiazdek)
- Umiejętności sprawdzone: body drag, water start, riding, upwind, tack/jibe, jump, rotation, wave riding, foil basics, foil upwind
- Progres IKO (poziom 1-4)

## 5. CRM Kursantów
- **Profil:** imię, email, telefon, data urodzenia, narodowość (flaga)
- **Dane:** poziom (beginner→professional), języki, tagi (VIP/returning/group_leader)
- **Historia:** wszystkie lekcje, zapłacone kwoty, certyfikaty
- **Kontakt awaryjny:** imię + telefon
- **Źródło:** website, instagram, whatsapp, viator, klook, email, phone, app, walk_in
- **Pakiety:** aktywne pakiety (sesje pozostałe / łącznie)
- **Waivers:** podpisane oświadczenia z datą i IP
- **Notatki:** wolny tekst, edytowalny przez staff

## 6. Instruktorzy
- **Profil:** zdjęcie, bio (PL + EN), dyscypliny, certyfikaty (IKO/PZKite/WOPR)
- **Grafik:** godziny pracy (pon-niedz), urlopy, blokady
- **Kolor:** hex na kalendarz
- **Stawka:** PLN/godz.
- **Historia:** przypisane rezerwacje, godziny przepracowane
- **Lokalizacja:** Hel / Hurghada / obie

## 7. Finanse
- **Przychód:** opłacony vs wystawiony, PLN + EUR osobno (kurs 4.3)
- **Okresy:** dziś / tydzień / miesiąc / sezon 2026 / sezon 2025 / wszystko
- **Karty:** rezerwacje, godziny, koszt/godzinę, zaległości
- **Rentowność:** przychód/godz., zysk/godz., koszt instruktorów
- **Revenue by service:** tabela z rozbiciem na usługi
- **Zaległości:** lista nieopłaconych z linkiem do rezerwacji
- **Eksport:** CSV / JSON

## 8. Płatności
- **Metody:** gotówka, karta, przelew, online, Viator, Klook
- **Statusy:** unpaid → deposit_paid → paid → refunded / partial_refund
- **Rejestracja:** kwota, metoda, data, referencja
- **Automatyczna aktualizacja** statusu rezerwacji po płatności

## 9. Pogoda
- **3 źródła:** dane z Open-Meteo API (real-time)
- **Lokalizacje:** Hel (54.6°N) i Hurghada (27.26°N)
- **Dane:** temperatura, wiatr (węzły + kierunek), kod pogody
- **Róża wiatrów:** wizualny kompas
- **Ocena:** Za słaby / Do nauki / Idealny / Średnio-silny / Za silny
- **Auto-refresh** na interwale

## 10. Transfer 2nd Spot — planowanie zastępczego spotu
- Gdy kierunek wiatru jest niekorzystny dla home spot, system planuje transfer na spot zastępczy i alertuje zespół
- **Zarządzanie transferem łodzią** (pojemność: 12 osób)
- **Kalendarz:** rezerwacje wymagające transferu na dany dzień
- **Status:** not_required → required → confirmed → paid
- **Koszty:** ~120 PLN/kurs (15L × 8 PLN/L), 50 PLN/os. (nie-kursanci)
- **Walidacja pojemności:** ostrzeżenie gdy >12 osób
- **Podsumowanie:** dzienne kursy, osoby, koszty, przychód

## 11. Sprzęt / Magazyn
- **Inwentarz:** kite, deska, trapez, bar, wing, foil, pianka, kask, inne
- **Status:** dostępny / w użyciu / serwis / wycofany
- **Dane:** marka, model, rozmiar, rok, numer seryjny
- **Serwis:** data ostatniego przeglądu, data następnego, alerty
- **Filtry:** lokalizacja, kategoria, status

## 12. Pakiety sesji
- **Pakiety lekcji:** np. 10x Kitesurfing (z progress barem)
- **Śledzenie:** sesje wykorzystane / łącznie
- **Ważność:** data od-do
- **Płatność:** status opłacenia
- **Przypisanie:** rezerwacja zużywa sesję z pakietu

## 13. Usługi (katalog)
- **Kategorie:** lekcja / kurs / obóz / pakiet / experience
- **Dane:** nazwa (PL+EN), opis, czas trwania, min/max osób
- **Ceny:** bazowa cena, waluta (PLN/EUR), jednostka (per_person/per_group/per_session/per_day)
- **Wymagania:** pogodowe, sprzętowe, poziom
- **Polityka anulowania**
- **Sort order** do kolejności w UI

## 14. Obozy / Półkolonie
- **Turnusy:** nazwa, typ (półkolonie/obóz/obóz_zewnętrzny), daty, max uczestników
- **Uczestnicy:** dziecko (imię, wiek, poziom, sport), rodzic (kontakt), alergie, notatki medyczne
- **Plan dzienny:** harmonogram aktywności (czas, aktywność, instruktor, lokalizacja)
- **Finanse:** przychód, koszty, bilans na turnus
- **Statusy:** planned → open → full → in_progress → completed → cancelled

## 15. Grafik instruktorów
- **Godziny pracy:** pon-ndz, start/end per dzień
- **Urlopy:** bloki czasowe z powodem (urlop/choroba/szkolenie)
- **Edycja per instruktor**

## 16. Raporty wizualne (owner-only)
- **Wykresy:** trend przychodu, przychód per usługa, per instruktor
- **Porównanie:** sezon 2026 vs 2025
- **Eksport:** PDF / PNG
- **Bookings per day:** trend dzienny

## 17. HR & Wynagrodzenia (owner-only)
- **Kalkulacja:** godziny × stawka = wynagrodzenie bazowe + bonus
- **Per instruktor:** godziny, lekcje, stawka, wynagrodzenie, przychód wygenerowany
- **Wydatki operacyjne:** sprzęt, paliwo, jedzenie, transport
- **Podsumowanie:** wynagrodzenia + wydatki = zysk netto

## 18. Analytics / Usage (owner-only)
- **Śledzenie użycia:** page views, feature usage, config changes
- **Top pages:** ranking odwiedzin
- **Aktywni użytkownicy:** distinct per email
- **Trend dzienny:** ostatnie 7 dni
- **Eksport:** CSV / JSON

## 19. Sklep / Katalog produktów
- **Produkty:** Cabrinha kites, deski, wing, akcesoria
- **Dane:** zdjęcie, nazwa, marka, rozmiary, cena (retail/sale/purchase)
- **Status:** dostępny / ostatnia sztuka / brak / brak ceny
- **Kategorie:** Kites, Boards, Wing, Accessories

## 20. Ustawienia
- **Lokalizacja domyślna:** Hel / Hurghada
- **Motyw:** dark / light
- **Zmiana hasła:** przez Supabase Auth
- **Usunięcie konta**

## 21. PZKite / Certyfikaty
- **Kursy:** PZK1/PZK2/PZK3, Water Rescue (WOPR)
- **Harmonogram:** daty kursów 2026
- **Linki:** PZKite, IKO, WOPR

---

## System ról (RBAC)

| Funkcja | Admin | Staff | Instruktor | Kursant |
|---------|-------|-------|------------|---------|
| Dashboard | ✅ | ✅ | ✅ | ❌ |
| Kalendarz | ✅ | ✅ | ✅ (swoje) | ❌ |
| Rezerwacje CRUD | ✅ | ✅ | ❌ | 🔒 swoje |
| Obecność | ✅ | ✅ | ✅ | ❌ |
| Finanse | ✅ | ✅ | ❌ | ❌ |
| CRM | ✅ | ✅ | 🔒 odczyt | ❌ |
| Instruktorzy CRUD | ✅ | ❌ | ❌ | ❌ |
| Usługi CRUD | ✅ | ❌ | ❌ | ❌ |
| Sprzęt | ✅ | 🔒 odczyt | ❌ | ❌ |
| Analytics | ✅ | ❌ | ❌ | ❌ |
| Raporty | ✅ | ❌ | ❌ | ❌ |
| HR/Payroll | ✅ | ❌ | ❌ | ❌ |

---

## Integracje
- **Supabase:** PostgreSQL + Auth + RLS + Real-time
- **Open-Meteo:** pogoda na żywo (Hel + Hurghada)
- **Viator / Klook:** import rezerwacji
- **Import danych:** migracja z poprzedniego systemu
- **Transfer 2nd Spot:** planowanie zastępczego spotu + transport łodzią
