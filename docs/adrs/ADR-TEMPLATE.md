# ADR-[NUMER] — [Tytuł Decyzji]

> **Status:** `[proposed | accepted | deprecated | superseded by ADR-XXX]`  
> **Data:** YYYY-MM-DD  
> **Autor:** [Imię i Nazwisko / AI Architect]  
> **Zastępuje:** [Brak lub ADR-XXX]  
> **Zastąpiony przez:** [Brak lub ADR-XXX]

---

## Kontekst

[Opisz w 2-3 zdaniach sytuację biznesową lub techniczną. Z jakim problemem się zderzyliśmy? Dlaczego w ogóle musimy podjąć decyzję?]

**Pytanie decyzyjne:**  
[Jak najkrócej: "W jaki sposób zaimplementujemy X, aby osiągnąć Y, nie psując Z?"]

---

## Opcje rozważane

[Zawsze wymieniaj alternatywy. Dobry ADR pokazuje nie tylko to, co wybraliśmy, ale też to, czego świadomie NIE wybraliśmy i dlaczego.]

### Opcja A: [Tytuł Opcji]
**Opis:** [Krótki opis mechanizmu]
**Plusy:** [Zalety w tym kontekście]
**Minusy:** [Wady, ryzyka]

### Opcja B: [Tytuł Opcji]
...

---

## Decyzja

Wybieramy **Opcję X: [Tytuł Opcji]**.

[Opisz krótko konkretny sposób wdrożenia tej opcji. Wypunktuj 2-3 najważniejsze zasady, które powstaną w wyniku tej decyzji i które będą chronić architekturę.]

---

## Konsekwencje

### Pozytywne
- [Co zyskujemy dzięki tej decyzji?]

### Negatywne / Działania wymagane
- [Co staje się trudniejsze? Z czym musimy się zmierzyć?]
- [Jakie zadania trafiają do Backlogu w wyniku tej decyzji?]

---

## Warunek rewizji (Trigger for Review)

[W jakich okolicznościach ta decyzja przestanie być aktualna? Np. "Zrewidować, gdy ruch przekroczy 10,000 użytkowników" lub "Gdy framework wyda wersję X".]

## Relacje (Related)
- **C4 Diagram:** [Link do pliku .puml jeśli dotyczy]
- **Kontrakty:** [Link do reguły w Linterze Importów, jeśli z tej decyzji wynika zakaz]
- **Dług (Debt):** [Opis ewentualnego długu technicznego wygenerowanego przez tę decyzję]
