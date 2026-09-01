# ADR-017 — Strategia Frontendu (HTMX + SSR zamiast SPA)

> **Status:** `accepted`
> **Data:** 2026-08-20
> **Autor:** AI Architecture / System Owner
> **Zastępuje:** Brak
> **Zastąpiony przez:** Brak

---

## Kontekst

Projekt PTTK Badges to aplikacja GIS dla turystów z intensywnym UI mapowym (MapLibre GL JS). W fazie projektowej rozważano dwa podejścia do warstwy prezentacji: klasyczną Single Page Application (React/Vue/Angular) albo Server-Side Rendering (Django Templates + HTMX). Wymagania kluczowe to szybki czas pierwszego renderu, dobre wyniki w SEO, minimalna konfiguracja deploymentu i wsparcie trybu Offline (PWA).

**Pytanie decyzyjne:**
Jak zaimplementujemy interfejs użytkownika, aby uzyskać szybki SSR + progresywną interaktywność mapową, nie psując UX ani SEO?

---

## Opcje rozważane

### Opcja A: SPA (React + Vite + REST/GraphQL API)
**Opis:** Frontend jako izolowana aplikacja React bundlerowana przez Vite, komunikująca się z backendem przez API.
**Plusy:**
- Rozbudowane możliwości interaktywnego UI (staleja niższy próg dla skomplikowanych komponentów).
- Silna ekosystem PWA (offline, service workery w JS).
- Dobre wsparcie dla map (MapLibre React).

**Minusy:**
- Długi czas budowania obrazu (Node.js + bundler) i dublowanie stosu (`node:20` + `python:3.14` w jednym repo monolithu).
- Problem z SEO — wymaga dodatkowego rozwiązania (SSR w Next.js/Nuxt), co znacząco podnosi próg wejścia.
- Trzy warstwy (Frontend, API, Domena) zwiększają liczbę granic API i ryzyko niespójności DTO.
- Wymaga oddzielnego pipeline’u CI (npm ci, testy JS, lint).

### Opcja B: HTMX + Django Templates (Server-Side Rendering)
**Opis:** HTML renderowany po stronie serwera w szablonach Django. Interaktywność (np. logowanie wejść) realizowana progresywnie przez HTMX (`hx-post`, `hx-get`) jako progressive enhancement do istniejących endpointów.
**Plusy:**
- Jeden stos technologiczny (Django), brak Node.js w obrazie.
- Naturalne SEO — każda strona jest prawdziwym HTML-em serwowanym od razu.
- Minimalny bundle JS — tylko `htmx.org` (~15KB gzipped) + specjalizowane skrypty mapowe.
- Prosty deployment: gunicorn + nginx, brak osobnego kroku build-frontendu.
- Ciasteczko sesyjne (cookie) działa out-of-the-box; brak potrzeby JWT w pierwszej kolejności.

**Minusy:**
- Granice UI bardziej ograniczone niż w czystym React (brak wirtualnego DOM).
- Wymaga refaktoryzacji logiki mapowej na czyste endpointy API (już częściowo zrobione — HTMX woła `/api/v1/ascents/`).
- Potencjalny "spaghetti JS" w szablonach wymaga dyscypliny (zob. `UI_GUIDELINES.md`).

---

## Decyzja

Wybieramy **Opcję B: HTMX + Django Templates (SSR)**.

Decyzja odróżnia dwa podziały:
1. **Mapa GIS** — renderowana po stronie klienta w MapLibre GL JS (nie da się inaczej — to specjalistyczny silnik mapowy). Logika zapisu wejść jest **deleguowana** do API (`hx-post` → `/api/v1/ascents/`).
2. **Reszta UI** — pełny SSR w szablonach Django z progressive enhancement HTMX.

**Zasady wynikające z decyzji (chroniące architekturę):**
- Każda akcja mutująca (np. logowanie wejścia) musi być dostępna przez **czysty endpoint HTTP**, który działa zarówno dla HTMX (partial swap), jak i jako API.
- Frontend nie importuje bezpośrednio ani nie zna logiki domenowej ani modeli Django — jedynie konsumuje odpowiedzi JSON/proste HTML-y.
- Brak Node.js w obrazie Docker — jedyny bundler to `ruff`/`uv`.

---

## Konsekwencje

### Pozytywne
- 70% mniejszy rozmiar obrazu Docker (brak `node:20` warstwy).
- Szybszy czas buildu CI (~30s vs ~90s dla SPA).
- SEO „zerowe” — Google indeksuje mapy POI i odznaki od razu.
- Prostszy debugging — backend dev może edytować szablon i od razu zobaczyć zmiany przez hot-reload.

### Negatywne / Działania wymagane
- [ ] Zadbbać o spójną integrację HTMX + MapLibre (zob. `UI Guidelines`).
- [ ] W przyszłości, jeśli UI stanie się zbyt złożone na HTMX, rozważyć migrację wybranych komponentów na mały, dedykowany micro-frontend (np. mapę POI).

---

## Warunek rewizji (Trigger for Review)

Zrewidować, gdy:
- Liczba interaktywnych komponentów UI przekracza 20 (próg, od którego koszt utrzymania HTMX zaczyna rosnąć wykładniczo).
- Wymagania PWA (pełny offline, natywne ikony) nie będą spełnialne przez prosty service worker w HTML.

## Relacje (Related)
- **Kontrakty:** Zasada `api/` jako warstwa transportowa — brak importów `apps.tourists.views` do `apps.api.views`.
- **Dług (Debt):** HTMX + MapLibre wymaga ręcznego utrzymania stanu klienta (scroll, zoom) — dokumentowane w `UI Guidelines`.
