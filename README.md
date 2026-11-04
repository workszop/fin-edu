# Finanse bez tajemnic

Interaktywna aplikacja webowa o podstawach finansów: sześć lekcji, w każdej małe demo i kalkulator do własnych eksperymentów, do tego słownik terminów. Całość w jednym pliku `index.html` w stylu edulab.

Otwórz `index.html` w przeglądarce. Nie wymaga instalacji ani serwera. Ikony Lucide i czcionki Google Fonts ładują się z CDN. Bez sieci aplikacja działa i liczy wszystko tak samo, tylko bez ikon i z czcionkami systemowymi.

## Lekcje

| Lekcja | Demo | Kalkulator |
|---|---|---|
| Inflacja | pizza za 100 zł po latach inflacji, skala z celem NBP | wehikuł czasu dla portfela, inflacja w Polsce 2015–2024 |
| Stopy procentowe | łańcuch skutków podwyżki i obniżki stóp, lokata kontra inflacja | gra „zostań prezesem banku centralnego” |
| Procent składany | kula śnieżna: wpłata, odsetki proste i odsetki od odsetek rok po roku | oszczędzanie z podatkiem i inflacją, porównanie częstotliwości kapitalizacji |
| Obligacje skarbowe | wybór rodzaju obligacji z okresem i oprocentowaniem, tabela wszystkich ośmiu rodzajów z bieżącą ofertą, kapitalizacja kontra wypłata odsetek | stałe czy indeksowane przy obecnej inflacji (i o 1 pkt proc. niższej lub wyższej) oraz w przykładowych scenariuszach, huśtawka cena–stopy |
| Akcje | koszyki jajek: jedna firma kontra dwadzieścia, siatka 100 akcji z dywidendą | symulacja jednej firmy i koszyka, reinwestowanie dywidend, 1000 możliwych przyszłości |
| Kredyty | raty równe i malejące na słupkach, telefon „0%” z RRSO | kalkulator kredytu z RRSO, test wzrostu stóp |
| Słownik | 28 haseł z wyszukiwarką, m.in. kapitalizacja i indeksowanie | linki do lekcji, przykłady liczone na bieżących danych |

## Aktualne dane

Aplikacja pokazuje bieżącą inflację (GUS, API SDP), stopę referencyjną NBP i oprocentowanie obligacji z oferty Ministerstwa Finansów, zawsze z datą, której dotyczą. Dane zapisuje plik `data/rates.json`, który codziennie odświeża workflow `.github/workflows/rates.yml` (skrypt `scripts/fetch_rates.py`, sama biblioteka standardowa Pythona). Ręcznie: `python3 scripts/fetch_rates.py`. Gdy plik się nie wczyta (np. po otwarciu `index.html` z dysku), aplikacja używa kopii zapisanej w kodzie i wyraźnie to zaznacza.

Materiał edukacyjny, nie porada inwestycyjna. Modele są uproszczone, a parametry przykładowe.
