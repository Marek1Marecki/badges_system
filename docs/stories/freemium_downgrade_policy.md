# Story: Polityka Downgrade Konta (Freemium Reconciliation)

## As-IS (Problem)
AUDYT-087. Gdy turysta z pakietu PRO (limit=5) wraca do FREE (limit=3),
system nie definiuje zachowania dla 2 nadmiarowych odznak `IN_PROGRESS`.

## To-BE (Polityka)
> **Decyzja: Zamrożenie (Read-Only), nie aktywne wymuszenie rezygnacji.**

1. Odznaki już przekraczające limit po downgrade pozostają w stanie
   `IN_PROGRESS` (zablokowane — "zamrożone") w UI (szarawe przyciski).
2. Turysta może ręcznie `unsubscribe` z nadmiarowych odznak w dowolnym momencie.
3. Dopóki limit nie zostanie obniżony poniżej maksymalnego `IN_PROGRESS`,
   turysta może logować wejścia na szczyty w obrębie **pozostałych** aktywnych odznak.
4. Próba `start_badge_progress` gdy limit jest osiągnięty → `UseCaseError`
   (już zaimplementowane w `StartBadgeProgressUseCase` — invariant US-C01c).

## Invariant
`VerifyBadgeUseCase` musi **zablokować ewaluację** dla odznaki, gdyby
jej status `IN_PROGRESS` przekraczał nowy limit po downgrade — chroni to
przed "phantom scoringiem" na zamrożonych odznakach.

## Wdrożenie (2026-09-03)
- ✅ `VerifyBadgeUseCase.execute()` — walidacja: jeśli `domain_status != "COMPLETED"`
  i limit aktywnych odznak >= `max_active_badges`, rzuca `UseCaseError` (reconciliation)
- ✅ Polityka udokumentowana: ten plik
