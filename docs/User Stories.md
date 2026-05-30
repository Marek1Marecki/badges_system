
User Stories

    Wersja: 1.1
    Data: 2026-05-29
    Właściciel: Dominik / AI Architect
    Status: approved (Dla Fazy C: Użytkownik i Logistyka)

Format stories
code Text

Jako [ROLA], chcę [DZIAŁANIE], aby [CEL / KORZYŚĆ].

Priorytety
Symbol	Znaczenie
🔴 P0	Krytyczne — bez tego system nie działa
🟠 P1	Wysokie — kluczowe dla MVP Fazy C
🟡 P2	Średnie — ważne, ale można opóźnić
🟢 P3	Niskie — nice-to-have (np. zaawansowana analityka)
Epic 1: Profil Turysty i Kontekst Weryfikacji (Verification Context)
US-C01 — Rejestracja i Wiek Turysty 🔴 P0

Story: Jako Turysta, chcę zdefiniować swoją datę urodzenia w profilu, aby system mógł poprawnie weryfikować odznaki posiadające ograniczenia wiekowe.
Dotyczy encji: TouristProfile (Nowa), MinAgeRule, MaxAgeRule
Powiązane invarianty: —

Kryteria akceptacji:

    Model TouristProfile jest powiązany z modelem autoryzacyjnym Django (User) za pomocą relacji OneToOneField.

    Profil przechowuje bezpiecznie birth_date.

    Silnik Domenowy podczas ewaluacji otrzymuje prawdziwą datę z profilu zamiast dotychczasowego mocka w kodzie.

US-C02 — Przynależność Klubowa (Data zapisu) 🟠 P1

Story: Jako Turysta, chcę móc odnotować datę dołączenia do konkretnego Klubu (np. KGP), aby system zaliczał mi logi wejść zrobione dopiero po tej dacie.
Dotyczy encji: ClubMembership (Nowa), OrganizerModel, RequiresClubJoinDateRule

Kryteria akceptacji:

    Turysta może wybrać Organizatora z bazy i podać datę zapisu.

    VerifyBadgeUseCase ignoruje wejścia starsze niż data członkostwa dla odznak wymagających tej reguły.

Epic 2: Dziennik Wejść i Złoty Zbiór (The Ascent Log)
US-C03 — Logowanie Wejścia (Ascent) 🔴 P0

Story: Jako Turysta, chcę zapisać fakt wejścia na konkretny Obiekt Turystyczny, podając datę i aktywność (np. Pieszo/Rower), aby budować swoją historię górską.
Dotyczy encji: AscentLog (Nowa), TouristObject
Powiązane invarianty: T-01 (Bitemporalność obiektu)

Kryteria akceptacji:

    Zapis logu wymaga podania tourist_object_id, date oraz activity_type.

    System twardo odrzuca log (Fail-Fast), jeśli podana data nie mieści się w przedziale existence_start i existence_end obiektu (T-01).

US-C04 — Dowody Wejścia (Załączniki) 🟠 P1

Story: Jako Turysta, chcę załączyć zdjęcie lub skan (np. pieczątki ze schroniska) do logu wejścia, aby weryfikator PTTK miał fizyczny dowód na moją obecność.
Dotyczy encji: AscentLog

Kryteria akceptacji:

    Pola w bazie: proof_image (ImageField) oraz proof_file (FileField).

    Obsługiwane formaty: JPEG, PNG dla zdjęć; PDF dla skanów książeczek.

    Twardy limit rozmiaru pliku: maksymalnie 5 MB (walidowane na poziomie Pydantic DTO oraz formularza).

    Przechowywanie w katalogu media/ascents/ (w środowisku deweloperskim na dysku lokalnym, gotowe na podpięcie django-storages / S3 dla produkcji).

Epic 3: Silnik Postępu (Badge Progress)
US-C05 — Rozpoczęcie zdobywania Wersji Odznaki 🔴 P0

Story: Jako Turysta, chcę rozpocząć zdobywanie Odznaki, aby system na zawsze przypisał mnie do obowiązującego w tym dniu regulaminu (Wersji).
Dotyczy encji: UserBadgeProgress (Nowa), BadgeVersionModel
Powiązane invarianty: P-01 (Prawa Nabyte)

Kryteria akceptacji:

    Utworzenie rekordu UserBadgeProgress z odpowiednim ID historycznej lub obecnej BadgeVersion.

    Data przypisania decyduje o tym, na jakich zasadach weryfikowany jest turysta.

US-C06 — Obliczanie Postępu (Set Math w Domenie) 🔴 P0

Story: Jako Turysta, chcę zobaczyć na jakim jestem etapie (np. 12/25 szczytów), aby wiedzieć, ile brakuje mi do danego Stopnia odznaki.
Dotyczy encji: UserBadgeProgress, BadgeTierModel, VerifyBadgeUseCase
Powiązane invarianty: R-01, T-02

Kryteria akceptacji:

    Przeliczanie statusów (NOT_STARTED, IN_PROGRESS, COMPLETED) następuje synchronicznie w locie (On-Demand) podczas ładowania widoku (dla gwarancji Immediate Consistency).

    Ukończenie wymagań dla konkretnego BadgeTierModel oznacza ten stopień jako gotowy do Wniosku Weryfikacyjnego.

US-C09 — Kolejny Cykl Odznaki (Pętla Prestiżu) 🟠 P1

Story: Jako Turysta, chcę rozpocząć ponowne zdobywanie tej samej odznaki (nowy cykl), aby móc zweryfikować ją po raz kolejny, używając wyłącznie nowych wejść.
Dotyczy encji: UserBadgeProgress (Rozbudowa o cycle_number)
Powiązane edge cases: EC-030

Kryteria akceptacji:

    Dodanie pola cycle_number (domyślnie 1) do UserBadgeProgress.

    Turysta może utworzyć nowy cykl TYLKO wtedy, gdy poprzedni cykl jest w statusie COMPLETED.

    Wejścia wykorzystane do zamknięcia Cyklu 1 są odfiltrowywane i nie wchodzą do puli ewaluacyjnej Cyklu 2.

Epic 4: Logistyka i Kanban (Verification & Fulfillment)
US-C07 — Wniosek Weryfikacyjny (Verification Request) 🟠 P1

Story: Jako Turysta, chcę zebrać moje "ZDOBYTE" stopnie odznak z danego Oddziału PTTK w jedną "Paczkę" i wysłać je do fizycznej weryfikacji.
Dotyczy encji: VerificationRequest (Nowa), UserBadgeProgress
Powiązane edge cases: EC-030 (Odznaki Wielokrotne)

Kryteria akceptacji:

    Użytkownik tworzy wniosek agregujący wiele zdobytych odznak z danego Cyklu.

    Wniosek bezwzględnie wymaga wgranego dokumentu, jeśli jakakolwiek odznaka we wniosku ma BadgeModel.is_booklet_required = True.

US-C08 — Maszyna Stanów Logistyki 🟠 P1

Story: Jako Turysta i Administrator, chcemy widzieć, na jakim etapie logistycznym jest paczka z odznakami, aby zarządzać procesem wysyłki.
Dotyczy encji: VerificationRequest

Kryteria akceptacji:

    Jednokierunkowa maszyna stanów: WAITING_FOR_SEND → WAITING_FOR_VERIFICATION → WAITING_FOR_RECEIVING → ALBUM.

    System archiwizuje daty przejść (timestampy) dla każdego statusu.

Mapa zależności
Story	Opis skrócony	Blokuje	Zablokowana przez
US-C01	Profil i Wiek	US-C02, US-C06	—
US-C03	Logowanie Wejścia	US-C06, US-C04	US-C01
US-C04	Załączniki do Wejść	—	US-C03
US-C05	Zapis na Odznakę	US-C06, US-C07	US-C01
US-C06	Silnik Postępu	US-C07, US-C09	US-C01, US-C03, US-C05
US-C09	Pętla Prestiżu (Cykle)	—	US-C06
US-C07	Wniosek Weryfikacyjny	US-C08	US-C06, US-C05
US-C08	Maszyna Stanów Kanban	—	US-C07
Historia zmian
Wersja	Data	Autor	Opis zmiany
1.0	2026-05-29	Dominik / AI Architect	Pierwsza wersja (Faza C).
1.1	2026-05-29	AI Architect	Uzupełnienie Mapy Zależności. Doprecyzowanie synchronicznego triggera US-C06 (Immediate Consistency), dodanie US-C09 (Pętla Prestiżu / EC-030).