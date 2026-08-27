# Instrukcja obsługi dla operatora

Ta instrukcja opisuje codzienną obsługę panelu operatora i terminala. Nie wymaga dostępu do ustawień administracyjnych ani tokenu API Snipe-IT.

## Przed rozpoczęciem

- Terminal musi mieć dostęp sieciowy do Snipe Bridge.
- Panel operatora otwórz we współczesnej przeglądarce na komputerze.
- Na skanerze otwórz adres `/terminal`.
- Skaner powinien dopisywać Enter po odczytanym kodzie.

## 1. Logowanie

Otwórz adres panelu i zaloguj się przez skonfigurowanego dostawcę tożsamości. Formularza lokalnego administratora używa tylko osoba utrzymująca aplikację.

![Logowanie do Snipe Bridge](images/login.png)

Język panelu jest przypisany do sesji zalogowanego użytkownika. Przed parowaniem język terminala można zmienić w jego nagłówku.

## 2. Parowanie terminala

W kroku 1 panel operatora wyświetla jednorazowy kod QR.

![Panel operatora z kodem parowania](images/operator.png)

Na terminalu:

1. Upewnij się, że kursor znajduje się w polu skanowania kodu parowania.
2. Zeskanuj QR widoczny na komputerze.
3. Jeżeli skanowanie QR nie jest dostępne, rozwiń ręczne parowanie w panelu i wpisz sześciocyfrowy kod widoczny na terminalu.

![Ekran parowania terminala](images/terminal-pairing.png)

Kod QR po krótkim czasie wygasa i jest jednorazowy. W razie wygaśnięcia wygeneruj nowy. Kod nie zawiera tokenu API Snipe-IT.

## 3. Wybór operacji

Po sparowaniu wybierz w kroku 2:

- **Wydanie** — jeden sprzęt na jedną operację;
- **Masowe wydanie** — lista urządzeń i jedno końcowe zatwierdzenie;
- **Zwrot** — jeden sprzęt na jedną operację;
- **Masowy zwrot** — lista urządzeń i jedno końcowe zatwierdzenie.

Wybrany ekran zostanie automatycznie wczytany na sparowanym terminalu.

## 4. Wydanie sprzętu

W kroku 3 wyszukaj odbiorcę po nazwisku lub adresie e-mail i wybierz właściwego użytkownika Snipe-IT. Następnie na terminalu:

1. Zeskanuj Asset Tag, numer seryjny, skonfigurowany dodatkowy identyfikator albo QR sprzętu z Snipe-IT.
2. Sprawdź kategorię, producenta i model, opcjonalną nazwę, Asset Tag, numer seryjny oraz odbiorcę.
3. Naciśnij zielony klawisz albo zielony przycisk potwierdzenia.
4. Jeżeli to nie ten sprzęt, naciśnij czerwony klawisz albo anuluj.

![Potwierdzenie sprzętu na terminalu](images/terminal-confirmation.png)

Po poprawnym wydaniu Snipe-IT przypisze sprzęt do odbiorcy i ustawi status skonfigurowany dla wydania.

## 5. Zwrot sprzętu

Przy zwrocie nie wybierasz osoby. Snipe Bridge odczytuje aktualnego użytkownika ze sprzętu.

1. Wybierz zwrot pojedynczy albo masowy.
2. Jeżeli panel o to poprosi, wybierz status: gotowy do użycia albo wymagający serwisu.
3. Zeskanuj sprzęt.
4. Sprawdź jego dane i aktualnie przypisaną osobę.
5. Potwierdź zielonym klawiszem lub przyciskiem.

Aplikacja odrzuci zwrot nieprzypisanego sprzętu albo zasobu niespełniającego skonfigurowanych reguł statusu. Przy wyborze serwisu zastosuje odpowiedni status i zapisze tę informację w notatce operacji.

## 6. Operacje masowe

Skanuj kolejne urządzenia pojedynczo. Ponowny skan tego samego zasobu pokaże ostrzeżenie i nie utworzy duplikatu.

Przed zatwierdzeniem:

- sprawdź liczbę sztuk i całą listę;
- użyj przycisku **Wybierz do usunięcia** przy błędnie dodanej pozycji;
- na ekranie potwierdzenia sprawdź Asset Tag, numer seryjny i dane sprzętu;
- zielony klawisz usuwa pozycję, czerwony anuluje;
- wybierz **Zatwierdź listę** dopiero po sprawdzeniu całości.

Po zakończeniu masowego wydania lub zwrotu lista jest zerowana. Sukces jest oznaczony na zielono, ostrzeżenie lub duplikat na żółto, a błąd na czerwono.

## 7. Zmiana trybu bez ponownego parowania

Wybierz inną operację w panelu operatora. Terminal automatycznie wczyta właściwy ekran. Nie skanuj w czasie krótkiego komunikatu ładowania. Jeżeli po chwili nadal widzisz poprzedni tryb, wykonaj jedno ręczne odświeżenie i zgłoś administratorowi, jeśli problem się powtarza.

## 8. Zakończenie sesji

Użyj **Zakończ sesję** na terminalu albo wyloguj się z panelu operatora. Powiązanie terminala zostanie usunięte, a panel ponownie pokaże QR. Samo zamknięcie przeglądarki nie jest właściwym zakończeniem pracy, szczególnie gdy urządzenie przejmuje inny operator.

Nieaktywna sesja terminala wygaśnie po czasie ustawionym przez administratora.

## Obsługiwane kody

| Zawartość | Przykład |
|---|---|
| Asset Tag | `ASSET-00064` |
| Numer seryjny | `SN-2026-0064` |
| Dodatkowe pole sprzętu | Wartość właściwa dla organizacji |
| Adres zasobu Snipe-IT | `https://snipe.example.org/hardware/64` |

Dla adresu URL aplikacja rozpoznaje fragment `/hardware/<numeryczne ID>` niezależnie od nazwy serwera Snipe-IT.

## Najczęstsze problemy

- **Nie znaleziono sprzętu:** sprawdź, czy zeskanowano cały kod i czy zasób istnieje w Snipe-IT.
- **Kod QR wygasł albo został użyty:** wygeneruj nowy QR i zeskanuj ponownie.
- **Sprzętu nie można przyjąć:** sprawdź jego przypisanie i status w Snipe-IT.
- **Wybrano złą osobę:** anuluj przed potwierdzeniem i wskaż właściwego odbiorcę w panelu.
- **Terminal nie zmienił trybu:** odczekaj chwilę, potem odśwież stronę jeden raz.
- **Przeglądarka terminala jest niestabilna:** poproś administratora o tryb bezpieczny albo wyłączenie obrazów.

Każda zakończona lub odrzucona operacja jest widoczna w Twojej historii. Przy zgłoszeniu podaj administratorowi godzinę, Asset Tag i treść komunikatu.
