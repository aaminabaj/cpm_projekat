"""
Metoda kritičnog puta (CPM) - jezgro algoritma.

Ovaj fajl koristi samo standardnu biblioteku Pythona. Slike su u fajlu
crtanje.py, a provjera ispravnosti u fajlu provjera.py.

Pokretanje:
    python cpm.py primjeri/primjer_tablica_1.csv
    python cpm.py primjeri/primjer_tablica_1.csv --slike --provjera
    python cpm.py primjeri/primjer_tablica_1.csv --sta-ako C 3
"""
import argparse #obrada komandi iz terminala
import csv
import os #rad s putanjama na racunaru
import re #napredno razbijanje teksta po vise razlicitih znakova odjedno,
from collections import deque #uvozi dvostruki red
from dataclasses import dataclass #omogucava kreiranje strukturnog objekta Rezultat

EPS = 1e-9   # tolerancija pri poređenju trajanja koja nisu cijeli brojevi


# ---------------------------------------------------------------- 1. ulaz
def ucitaj_projekat(putanja):
    """Čita CSV s kolonama: aktivnost, trajanje, prethodnici.
    Prethodnici se odvajaju tačkom-zarezom, zarezom ili razmakom (npr. D;E),
    a '-' ili prazno znači da aktivnost nema prethodnika.
    Radi s fajlovima iz Excela (razdjelnik ; i BOM na početku).
    Vraća rječnike trajanje i prethodnici."""
    trajanje = {}
    prethodnici = {} #dva prazna rjecnika

    with open(putanja, newline="", encoding="utf-8-sig") as f:
        # Excel (kod nas) razdvaja kolone znakom ; a drugi programi zarezom.
        # Gleda se prvi red fajla da se vidi koji je razdjelnik.
        prvi_red = f.readline()
        f.seek(0) #vraca pokazivac na pocetak fajla
        if prvi_red.count(";") >= 2:
            razdjelnik = ";"
        else:
            razdjelnik = ","

        citac = csv.DictReader(f, delimiter=razdjelnik)
        for red in citac:
            naziv = red["aktivnost"].strip()
            if naziv in trajanje: #ako aktivnost ima i vec kljucevima rjecnika trajanje
                raise ValueError(f"Aktivnost {naziv} je navedena više puta.")

            # decimalni zarez iz Excela (2,5) pretvaramo u tačku (2.5)
            t = float(red["trajanje"].replace(",", "."))
            if t < 0: #provjera uslova da trajanje ne moze biti negativno
                raise ValueError(f"Aktivnost {naziv} ima negativno trajanje.")
            if t.is_integer(): #pretvaranje u int ako je int ili ostavljanje u float
                trajanje[naziv] = int(t)
            else:
                trajanje[naziv] = t

            # Tekst "D;E" se razdvaja na dijelove "D" i "E".
            dijelovi = re.split(r"[;,\s]+", red["prethodnici"].strip())
            #cijepa tekst kolone prethodnici na ; ili , ili razmak
            lista = []
            for dio in dijelovi:
            #prolazi kroz svaki dio tih dijelova i ako nije prazno ili - dodaje u listu prethodnika
                if dio != "" and dio != "-":
                    lista.append(dio)
            prethodnici[naziv] = lista
            #upisuje listu u rjecnik pod nazivom aktivnosti iz tog reda

    # Svaki prethodnik mora i sam biti aktivnost iz tablice.
    nepoznati = set()
    for lista in prethodnici.values():
    #prolazi korz procitane prethodnike i ako neki nema u kljucevima trajanja dodaje ga
        for p in lista:
            if p not in trajanje:
                nepoznati.add(p)
    if len(nepoznati) > 0:
        #ako ta lista nije prazna vraca se error
        raise ValueError(f"Prethodnici koji nisu aktivnosti: {sorted(nepoznati)}")

    return trajanje, prethodnici


def sljedbenici_iz(prethodnici):
    """Iz liste prethodnika gradi listu sljedbenika (jedan prolaz kroz ivice)."""
    sljedbenici = {}
    for v in prethodnici:
        sljedbenici[v] = []          # na početku svaka aktivnost ima praznu listu

    for y in prethodnici:
        for x in prethodnici[y]:
            # x je prethodnik od y, dakle y je sljedbenik od x
            sljedbenici[x].append(y)
    #svaka ivica se obidje tacno jednom pa je slozenost O(|V| + |E|)
    return sljedbenici


# -------------------------------------------- 2. topološko sortiranje (Kahn)
class CiklusGreska(ValueError):
    """Graf sadrži ciklus pa plan projekta nije izvodljiv."""
    def __init__(self, vrhovi):
        self.vrhovi = vrhovi
        super().__init__("Graf sadrži ciklus. Aktivnosti koje nije moguće "
                         f"rasporediti: {sorted(vrhovi)}")


def topoloski_poredak(prethodnici):
    sljedbenici = sljedbenici_iz(prethodnici)

    # ulazni stepen = broj direktnih prethodnika aktivnosti
    ulazni = {}
    for v in prethodnici:
        ulazni[v] = len(prethodnici[v])

    # deque je red kod kojeg se skidanje s početka radi brzo (O(1)),
    # a kod obične liste bi to bilo sporo (O(n)).
    red = deque()
    for v in prethodnici:
        #u red se dodaju sve aktivnosti sa ulaznim stepenom 0
        if ulazni[v] == 0:
            red.append(v)

    poredak = []
    while len(red) > 0:
        v = red.popleft()            # skidamo vrh s početka reda
        poredak.append(v)            # i stavljamo ga u konačni poredak
        for s in sljedbenici[v]:
            #za tu aktivnost smanjujemo ulazni stepen sljedbenika
            ulazni[s] = ulazni[s] - 1
            if ulazni[s] == 0:       # svi prethodnici od s su već obrađeni
                red.append(s)

    # Ako nisu obrađene sve aktivnosti, u grafu postoji ciklus.
    if len(poredak) < len(prethodnici):
        obradjeni = set(poredak)
        neobradjeni = set()
        for v in prethodnici:
            if v not in obradjeni:
                neobradjeni.add(v)
        raise CiklusGreska(neobradjeni)

    return poredak


# ------------------------------------------------------------------ 3. CPM
@dataclass #python automatski pravi konstruktor koji prima sva polja redom
class Rezultat:
    poredak: list
    ES: dict
    EF: dict
    LS: dict
    LF: dict
    slack: dict
    T: float
    kriticne: list


def izracunaj_cpm(trajanje, prethodnici):
    sljedbenici = sljedbenici_iz(prethodnici)
    poredak = topoloski_poredak(prethodnici)

    # ----- prolaz unaprijed (forward pass)
    ES = {}
    EF = {}
    for v in poredak:
        # ES(v) je najveći EF među prethodnicima. Aktivnost bez prethodnika
        # počinje u trenutku 0. Početna vrijednost 0 je ispravna jer su
        # trajanja nenegativna, pa nijedan EF nije manji od 0.
        najveci_kraj = 0
        for u in prethodnici[v]:
            if EF[u] > najveci_kraj:
                najveci_kraj = EF[u]
        ES[v] = najveci_kraj
        EF[v] = ES[v] + trajanje[v]

    # T je najveći EF među svim aktivnostima
    T = 0
    for v in poredak:
        if EF[v] > T:
            T = EF[v]

    # ----- prolaz unazad (backward pass), obrnutim topološkim poretkom
    LS = {}
    LF = {}
    for v in reversed(poredak):
        # LF(v) je najmanji LS među sljedbenicima. Aktivnost bez sljedbenika
        # mora završiti najkasnije u T. Početna vrijednost T je ispravna jer
        # nijedan LS nije veći od T.
        najmanji_pocetak = T
        for s in sljedbenici[v]:
            if LS[s] < najmanji_pocetak:
                najmanji_pocetak = LS[s]
        LF[v] = najmanji_pocetak
        LS[v] = LF[v] - trajanje[v]

    # ----- slack i kritične aktivnosti
    slack = {}
    for v in trajanje:
        slack[v] = LS[v] - ES[v]

    # Poređenje s EPS umjesto "== 0" jer decimalni brojevi mogu imati
    # sitne greške zaokruživanja.
    kriticne = []
    for v in poredak:
        if abs(slack[v]) < EPS:
            kriticne.append(v)

    return Rezultat(poredak, ES, EF, LS, LF, slack, T, kriticne)

def kriticne_ivice(rez, prethodnici):
    """Ivice (u, v) koje leže na nekom kritičnom putu: obje aktivnosti su
    kritične i v počinje tačno kad u završi."""
    ivice = set() #skupljaju se parovi (u, v)
    for v in rez.kriticne:
        for u in prethodnici[v]:
        #za svaku kriticnu aktivnost v prolazi kroz njene prethodnike
            u_je_kriticna = u in rez.kriticne
            v_pocinje_kad_u_zavrsi = abs(rez.EF[u] - rez.ES[v]) < EPS
            if u_je_kriticna and v_pocinje_kad_u_zavrsi:
                ivice.add((u, v))
    return ivice

def kriticni_putevi(rez, prethodnici, najvise=1000):
    """Svi kritični putevi (projekat ih može imati više).
    Putevi se grade redom po topološkom poretku: put do v nastaje
    tako što se v doda na svaki put do kritičnog prethodnika u."""
    ivice = kriticne_ivice(rez, prethodnici)

    # aktivnosti iz kojih izlazi bar jedna kritična ivica
    ima_izlaznu = set() #skup cvorova iz kojih izlazi bar jedna kriticna ivica
    for (u, v) in ivice:
        ima_izlaznu.add(u)

    # putevi_do[v] = lista svih kritičnih puteva od početka projekta do v
    putevi_do = {}
    for v in rez.poredak:
        if v not in rez.kriticne:
            continue # nekritične preskačemo

        ulazne = [] # prethodnici s kritičnom ivicom
        for u in prethodnici[v]:
            if (u, v) in ivice:
                ulazne.append(u)
        ulazne.sort()

        if len(ulazne) == 0:
            putevi_do[v] = [[v]] #ako nema nijednog krit prethodnika, kritični put počinje u v
                            #dupla je [] jer je put do v [v], ali je rjecnik lista puteva pa se stavlja u jos jednu listu
        else:
            novi_putevi = [] #ako ima kriticnih prethodnika
            for u in ulazne:
                for put in putevi_do[u]:
                    novi_putevi.append(put + [v])   # put do u, pa još v
            putevi_do[v] = novi_putevi[:najvise] #putevi_do[D] = [[A, B, D], [A, C, D]...]uzima prvih 1000 puteva

    # prosla petlja vraca puteve do svih aktivnosti
    # Kritični put završava u aktivnosti iz koje ne izlazi kritična ivica.
    putevi = []
    for v in rez.poredak:
        if v in putevi_do and v not in ima_izlaznu:
            for put in putevi_do[v]:
                putevi.append(put)
    return putevi[:najvise]

def sta_ako(trajanje, prethodnici, aktivnost, kasnjenje):
    """Za koliko se produži projekat ako aktivnost traje 'kasnjenje' dana duže."""
    staro = izracunaj_cpm(trajanje, prethodnici).T #uzima ukupno trajanje

    novo_trajanje = dict(trajanje) # kopija, original ostaje isti
    novo_trajanje[aktivnost] = novo_trajanje[aktivnost] + kasnjenje
    novo = izracunaj_cpm(novo_trajanje, prethodnici).T

    return novo - staro

# --------------------------------------------------------------- 4. izlaz
def br(x):
    """Cijeli brojevi bez decimalne tačke (17 umjesto 17.0)."""
    if float(x).is_integer():
        return str(int(x))
    return f"{x:.2f}"


def formatiraj_red(celije, sirine):
    """Poravnava ćelije jednog reda tablice na zadate širine kolona."""
    poravnate = []
    for i in range(len(celije)):
        poravnate.append(celije[i].ljust(sirine[i]))
    return "  ".join(poravnate)


def tablica_rezultata(rez, trajanje, prethodnici):
    zaglavlje = ["Aktivnost", "w", "Prethodnici", "ES", "EF", "LS", "LF",
                 "Slack", "Kritična"]

    redovi = []
    for v in rez.poredak:
        if len(prethodnici[v]) > 0:
            tekst_prethodnika = ", ".join(prethodnici[v])
        else:
            tekst_prethodnika = "-"

        if v in rez.kriticne:
            kriticna = "da"
        else:
            kriticna = "ne"

        redovi.append([v, br(trajanje[v]), tekst_prethodnika,
                       br(rez.ES[v]), br(rez.EF[v]), br(rez.LS[v]),
                       br(rez.LF[v]), br(rez.slack[v]), kriticna])

    # širina kolone = dužina najdužeg teksta u toj koloni (uključujući naslov)
    sirine = []
    for i in range(len(zaglavlje)):
        najduze = len(zaglavlje[i])
        for red in redovi:
            if len(red[i]) > najduze:
                najduze = len(red[i])
        sirine.append(najduze)

    linije = [formatiraj_red(zaglavlje, sirine)]
    linije.append("-" * (sum(sirine) + 2 * (len(sirine) - 1)))
    for red in redovi:
        linije.append(formatiraj_red(red, sirine))
    return "\n".join(linije)


def spremi_rezultate(rez, trajanje, prethodnici, putanja):
    with open(putanja, "w", newline="", encoding="utf-8") as f:
        pisac = csv.writer(f)
        pisac.writerow(["aktivnost", "trajanje", "prethodnici", "ES", "EF",
                        "LS", "LF", "slack", "kriticna"])
        for v in rez.poredak:
            if v in rez.kriticne:
                kriticna = "da"
            else:
                kriticna = "ne"
            pisac.writerow([v, br(trajanje[v]), ";".join(prethodnici[v]),
                            br(rez.ES[v]), br(rez.EF[v]), br(rez.LS[v]),
                            br(rez.LF[v]), br(rez.slack[v]), kriticna])


# ---------------------------------------------------------------- program
def main():
    ap = argparse.ArgumentParser(description="CPM: kritični put projekta")
    ap.add_argument("projekat", help="CSV fajl s aktivnostima")
    ap.add_argument("--slike", action="store_true", help="napravi slike")
    ap.add_argument("--provjera", action="store_true",
                    help="provjeri rezultat nezavisnim metodama")
    ap.add_argument("--sta-ako", nargs=2, metavar=("AKTIVNOST", "DANI"),
                    help="za koliko se projekat produži ako aktivnost kasni")
    ap.add_argument("--jedinica", default="dana",
                    help="jedinica vremena u ispisu i na slikama (npr. mjeseci)")
    ap.add_argument("--dijelova", type=int, default=1,
                    help="na koliko slika podijeliti mrežni dijagram (npr. 2)")
    args = ap.parse_args()

    trajanje, prethodnici = ucitaj_projekat(args.projekat)
    try:
        rez = izracunaj_cpm(trajanje, prethodnici)
    except CiklusGreska as greska:
        print("GREŠKA:", greska)
        raise SystemExit(1)

    if args.sta_ako:
        aktivnost = args.sta_ako[0]
        dani = float(args.sta_ako[1])
        if aktivnost not in trajanje:
            raise SystemExit(f"Aktivnost {aktivnost} ne postoji.")
        pomak = sta_ako(trajanje, prethodnici, aktivnost, dani)
        print(f"Aktivnost: {aktivnost}")
        print(f"Slack aktivnosti: {br(rez.slack[aktivnost])} ({args.jedinica})")
        print(f"Kašnjenje: {br(dani)} ({args.jedinica})")
        print(f"Produženje projekta: {br(pomak)} ({args.jedinica})")
        print(f"Novo trajanje projekta: {br(rez.T + pomak)} ({args.jedinica})")
        return        # za analizu kašnjenja ne ispisuje se ostatak rezultata

    print(tablica_rezultata(rez, trajanje, prethodnici))
    print(f"\nUkupno trajanje projekta: T = {br(rez.T)} {args.jedinica}")
    putevi = kriticni_putevi(rez, prethodnici)
    print(f"Broj kritičnih puteva: {len(putevi)}")
    for put in putevi:
        print("  Kritični put:", " -> ".join(put))

    # folder za rezultate: izlaz/<ime fajla bez nastavka>
    ime = os.path.splitext(os.path.basename(args.projekat))[0]
    izlaz = os.path.join("izlaz", ime)
    os.makedirs(izlaz, exist_ok=True)
    spremi_rezultate(rez, trajanje, prethodnici,
                     os.path.join(izlaz, "rezultati.csv"))
    print(f"\nRezultati su sačuvani u {izlaz}/rezultati.csv")

    if args.provjera:
        from provjera import provjeri
        provjeri(trajanje, prethodnici, rez)

    if args.slike:
        from crtanje import nacrtaj_mrezu, nacrtaj_gantt
        nacrtaj_mrezu(rez, trajanje, prethodnici,
                      os.path.join(izlaz, "mreza.png"), args.dijelova)
        nacrtaj_gantt(rez, trajanje, os.path.join(izlaz, "gantt.png"), args.jedinica)
        print(f"Slike su sačuvane u {izlaz}/")


if __name__ == "__main__":
    main()