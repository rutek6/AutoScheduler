## Funkcje
- Windows / Linux
- Wczytywanie planu w formacie HTML z USOSweb  
- Generowanie wszystkich możliwych planów bez kolizji  
- Szybkie wykrywanie kolizji (C/DLL)  
- System wag i preferencji:
  - wolne dni  
  - okienka  
  - późne końce  
  - preferowane grupy  
  - ograniczenia godzinowe  
- Wizualizacja planu w czytelnej siatce godzinowej  
- Sortowanie planów według jakości

## Jak korzystać?
1. Pobierz plik AutoScheduler.exe (lub AutoScheduler.bin na Linuxie).
2. Aplikacja wczytuje pliki .html pobrane z USOSa.
   - Na USOSie stwórz nowy plan użytkownika zawierający wszystkie przedmioty, które chcesz umieścić w planie.
   - Wyświetl plan w formacie "Nowy HTML" (domyślny), strona powinna wyświetlić siatkę ze wszystkimi grupami wszystkich przedmiotów.
   - Kliknij prawym przyciskiem myszy gdziekolwiek na stronie, wybierz zapisz jako i zapisz plik w formacie czysty .html
4. Po otwarciu aplikacji, wczytaj plan w formacie .html.
5. Dostosuj wagi preferencji za pomocą suwaków, wybierz preferowane godziny początku i końca zajęć (wpisz godzinę, np "15") oraz preferowane dni wolne.
6. Jeśli istnieje plan zgodny z preferencjami, wyświetli się siatka godzin.


W przypadku korzystania z wersji źródłowej, wystarczy uruchomić plik gui.py ze wszystkimi pozostałymi w jednym folderze.
W teorii możliwe jest skorzystanie z wersji źródłowej na Macu. Wtedy należy skompilować scheduler_core.c do biblioteki dynamicznej w formacie .dylib i umieścić bibliotekę w tym samym folderze.
Program powinien ją wykryć i działać normalnie (nietestowane).
