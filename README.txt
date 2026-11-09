CPM - implementacija (diplomski rad)

Potrebne biblioteke:
    pip install matplotlib networkx
(jezgro u cpm.py koristi samo standardnu biblioteku; matplotlib treba za slike,
networkx samo za provjeru ispravnosti)

Fajlovi:
    cpm.py        jezgro: čitanje CSV-a, Kahnov algoritam, forward/backward pass,
                  slack, kritični putevi, analiza "šta ako", ispis rezultata
    crtanje.py    slike: mrežni dijagram (ES, EF, LS, LF, slack) i Gantt
    provjera.py   provjera nezavisnim metodama (NetworkX i gruba sila)
    primjeri/     ulazni CSV fajlovi

Format ulaznog CSV-a (primjeri/primjer_tablica_1.csv):
    aktivnost,trajanje,prethodnici
    A,3,-
    B,5,A
    F,3,D;E          <- više prethodnika odvojeno tačkom-zarezom

Pokretanje:
    python cpm.py primjeri/primjer_tablica_1.csv
    python cpm.py primjeri/primjer_tablica_1.csv --provjera
    python cpm.py primjeri/primjer_tablica_1.csv --slike
    python cpm.py primjeri/primjer_tablica_1.csv --sta-ako C 3
Rezultati i slike se čuvaju u izlaz/<ime projekta>/.
