"""
Slike za bilo koji projekat: mrežni dijagram s ES, EF, LS, LF i Ganttov
dijagram. Kritične aktivnosti su crvene, ostale plave ili crne.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Ellipse, FancyArrowPatch, Patch

from cpm import EPS, br, kriticne_ivice

CRNA = "#000000"
CRVENA = "#c00000"
PLAVA = "#2b6cb0"
SIRINA = 0.8          # polovina širine kutije
VISINA = 0.7          # polovina visine kutije
RAZMAK_X = 3.2        # vodoravni razmak među kutijama (nivoima)
RAZMAK_Y = 2.0        # okomiti razmak među kutijama
# visine (u odnosu na sredinu kutije) u kojima dugačke ivice ulaze/izlaze
POMACI = [-0.35, 0.35, -0.55, 0.55]


def prvi_element(par):
    """Pomoćna funkcija za sortiranje parova po prvom elementu."""
    return par[0]


def pozicije(rez, prethodnici):
    """Raspored: nivo (x) = najduži lanac prethodnika do aktivnosti;
    unutar nivoa aktivnosti se slažu po prosječnoj visini svojih prethodnika
    da bi se ivice što manje sijekle."""
    # nivo aktivnosti: 0 ako nema prethodnika, inače 1 + najveći nivo prethodnika
    nivo = {}
    for v in rez.poredak:
        najveci = 0
        for u in prethodnici[v]:
            if nivo[u] + 1 > najveci:
                najveci = nivo[u] + 1
        nivo[v] = najveci

    # aktivnosti grupisane po nivoima: {0: [A], 1: [B, C], ...}
    grupe = {}
    for v in rez.poredak:
        if nivo[v] not in grupe:
            grupe[nivo[v]] = []
        grupe[nivo[v]].append(v)

    poz = {}
    for n in sorted(grupe):
        # za svaku aktivnost u nivou računa se prosječna visina prethodnika
        parovi = []
        for v in grupe[n]:
            if len(prethodnici[v]) == 0:
                prosjek = 0
            else:
                zbir = 0
                for u in prethodnici[v]:
                    zbir = zbir + poz[u][1]
                prosjek = zbir / len(prethodnici[v])
            parovi.append((prosjek, v))

        parovi = sorted(parovi, key=prvi_element, reverse=True)   # gore -> dolje
        k = len(parovi)
        for i in range(k):
            v = parovi[i][1]
            x = n * RAZMAK_X
            y = ((k - 1) / 2 - i) * RAZMAK_Y
            poz[v] = (x, y)
    return poz


def tacka_na_ivici(c, drugi, elipsa=False):
    """Tačka u kojoj duž od centra c prema tački 'drugi' siječe rub oblika.
    Strelica počinje i završava na rubu, a ne u sredini. Oblik je kutija,
    a za milestones (elipsa=True) elipsa."""
    dx = drugi[0] - c[0]
    dy = drugi[1] - c[1]
    if elipsa:
        # rub elipse: (x/SIRINA)^2 + (y/VISINA)^2 = 1
        s = 1 / ((dx / SIRINA) ** 2 + (dy / VISINA) ** 2) ** 0.5
        return (c[0] + dx * s, c[1] + dy * s)
    if dx != 0:
        sx = SIRINA / abs(dx)
    else:
        sx = float("inf")
    if dy != 0:
        sy = VISINA / abs(dy)
    else:
        sy = float("inf")
    s = min(sx, sy)
    return (c[0] + dx * s, c[1] + dy * s)


def nivo_vrha(poz, v):
    """Nivo (kolona) u kojoj se aktivnost nalazi na mrežnom dijagramu."""
    return round(poz[v][0] / RAZMAK_X)


def granice_dijelova(najveci_nivo, dijelova):
    """Dijeli nivoe 0..najveci_nivo na 'dijelova' približno jednakih grupa.
    Vraća listu parova (prvi nivo, zadnji nivo) za svaki dio."""
    broj_nivoa = najveci_nivo + 1
    granice = []
    od = 0
    for i in range(dijelova):
        do = round((i + 1) * broj_nivoa / dijelova) - 1
        granice.append((od, do))
        od = do + 1
    return granice


def nacrtaj_mrezu(rez, trajanje, prethodnici, putanja, dijelova=1):
    """Mrežni dijagram. Za velike projekte dijagram se može podijeliti na
    'dijelova' slika (dio1, dio2, ...) da bi tekst ostao čitljiv u radu."""
    poz = pozicije(rez, prethodnici)

    najveci_nivo = 0
    for v in poz:
        if nivo_vrha(poz, v) > najveci_nivo:
            najveci_nivo = nivo_vrha(poz, v)

    if dijelova == 1:
        nacrtaj_dio(rez, trajanje, prethodnici, poz, 0, najveci_nivo,
                    najveci_nivo, putanja)
        return

    osnova = os.path.splitext(putanja)[0]
    granice = granice_dijelova(najveci_nivo, dijelova)
    for i in range(len(granice)):
        od_nivoa = granice[i][0]
        do_nivoa = granice[i][1]
        nacrtaj_dio(rez, trajanje, prethodnici, poz, od_nivoa, do_nivoa,
                    najveci_nivo, f"{osnova}_dio{i + 1}.png")


def trasa_duge_ivice(poz, trajanje, u, y, vrhovi, brojac):
    """Put ivice (u, y) koja preskače jedan ili više nivoa. Ivica ide iz
    aktivnosti u, okomito iznad ili ispod svih kutija koje bi presjekla,
    vodoravno iznad (ili ispod) njih, pa okomito do aktivnosti y.
    Vraća listu tačaka puta. brojac pamti koliko je traka već zauzeto."""
    nivo_u = nivo_vrha(poz, u)
    nivo_y = nivo_vrha(poz, y)

    # najviša i najniža tačka kutija (s oznakom slacka) u nivoima između
    gornja = None
    donja = None
    for v in vrhovi:
        if nivo_u < nivo_vrha(poz, v) < nivo_y:
            vrh_kutije = poz[v][1] + VISINA + 0.6
            dno_kutije = poz[v][1] - VISINA - 0.2
            if gornja is None or vrh_kutije > gornja:
                gornja = vrh_kutije
            if donja is None or dno_kutije < donja:
                donja = dno_kutije

    # traka iznad ili ispod, već prema tome koja je bliža aktivnostima u i y
    cijena_gore = abs(poz[u][1] - gornja) + abs(poz[y][1] - gornja)
    cijena_dole = abs(poz[u][1] - donja) + abs(poz[y][1] - donja)
    if cijena_gore <= cijena_dole:
        strana = "gore"
        traka = gornja + 0.4 * brojac["gore"]
    else:
        strana = "dole"
        traka = donja - 0.4 * brojac["dole"]
    redni = brojac[strana]
    brojac[strana] = brojac[strana] + 1

    # više dugačkih ivica može izlaziti iz iste aktivnosti ili ulaziti u istu,
    # pa im se visine razlikuju da se strelice ne spoje u jednu tačku
    if u not in brojac["izlaz"]:
        brojac["izlaz"][u] = 0
    if y not in brojac["ulaz"]:
        brojac["ulaz"][y] = 0
    y_polaska = poz[u][1] + POMACI[brojac["izlaz"][u] % 4]
    y_dolaska = poz[y][1] + POMACI[brojac["ulaz"][y] % 4]
    brojac["izlaz"][u] = brojac["izlaz"][u] + 1
    brojac["ulaz"][y] = brojac["ulaz"][y] + 1
    if trajanje[u] == 0:       # milestone je elipsa: ivica ide iz sredine
        y_polaska = poz[u][1]
    if trajanje[y] == 0:
        y_dolaska = poz[y][1]

    # okomiti dijelovi su u razmaku odmah iza u i odmah ispred y
    x1 = poz[u][0] + SIRINA + 0.2 + 0.12 * (redni % 3)
    x2 = poz[y][0] - SIRINA - 0.2 - 0.12 * (redni % 3)
    return [(poz[u][0] + SIRINA, y_polaska), (x1, y_polaska), (x1, traka),
            (x2, traka), (x2, y_dolaska), (poz[y][0] - SIRINA, y_dolaska)]


def nacrtaj_dio(rez, trajanje, prethodnici, poz, od_nivoa, do_nivoa,
                najveci_nivo, putanja):
    """Crta aktivnosti čiji je nivo između od_nivoa i do_nivoa. Ivice koje
    prelaze granicu dijela crtaju se kao kratke strelice uz kutiju, s
    oznakom aktivnosti s druge strane granice."""
    vrhovi = []
    for v in poz:
        if od_nivoa <= nivo_vrha(poz, v) <= do_nivoa:
            vrhovi.append(v)

    xs = []
    ys = []
    for v in vrhovi:
        xs.append(poz[v][0])
        ys.append(poz[v][1])

    # trase dugačkih ivica (preskaču nivo) računaju se unaprijed, jer
    # trake iznad i ispod kutija povećavaju visinu slike
    trase = {}
    brojac = {"gore": 0, "dole": 0, "izlaz": {}, "ulaz": {}}
    for y in prethodnici:
        for u in prethodnici[y]:
            u_je_unutra = od_nivoa <= nivo_vrha(poz, u) <= do_nivoa
            y_je_unutra = od_nivoa <= nivo_vrha(poz, y) <= do_nivoa
            if u_je_unutra and y_je_unutra:
                if nivo_vrha(poz, y) - nivo_vrha(poz, u) >= 2:
                    trase[(u, y)] = trasa_duge_ivice(poz, trajanje, u, y, vrhovi, brojac)
    najnize = min(ys) - VISINA
    najvise = max(ys) + VISINA + 0.5
    for tacke in trase.values():
        for (tx, ty) in tacke:
            if ty - 0.3 < najnize:
                najnize = ty - 0.3
            if ty + 0.3 > najvise:
                najvise = ty + 0.3

    # mjesto za oznake ivica koje prelaze granicu dijela
    lijevo = min(xs) - SIRINA - 0.5
    desno = max(xs) + SIRINA + 0.5
    if od_nivoa > 0:
        lijevo = min(xs) - SIRINA - 1.5
    if do_nivoa < najveci_nivo:
        desno = max(xs) + SIRINA + 1.5

    sirina = desno - lijevo
    visina = najvise - najnize + 1.2
    fig, ax = plt.subplots(figsize=(0.75 * sirina, 0.75 * visina))

    # ----- strelice unutar dijela; ivice preko granice se samo prikupljaju
    krit_ivice = kriticne_ivice(rez, prethodnici)
    izlazne = {}      # aktivnost u dijelu -> aktivnosti u kasnijem dijelu
    ulazne = {}       # aktivnost u dijelu -> aktivnosti iz ranijeg dijela
    for y in prethodnici:
        for u in prethodnici[y]:
            u_je_unutra = od_nivoa <= nivo_vrha(poz, u) <= do_nivoa
            y_je_unutra = od_nivoa <= nivo_vrha(poz, y) <= do_nivoa
            if u_je_unutra and not y_je_unutra:
                if u not in izlazne:
                    izlazne[u] = []
                izlazne[u].append(y)
            if y_je_unutra and not u_je_unutra:
                if y not in ulazne:
                    ulazne[y] = []
                ulazne[y].append(u)
            if not (u_je_unutra and y_je_unutra):
                continue

            je_krit = (u, y) in krit_ivice
            if je_krit:
                boja = CRVENA
                debljina = 2.6
            else:
                boja = CRNA
                debljina = 1.4

            if (u, y) in trase:
                # dugačka ivica: izlomljena linija iznad ili ispod kutija,
                # a strelica je samo posljednji dio
                tacke = trase[(u, y)]
                for i in range(len(tacke) - 2):
                    ax.plot([tacke[i][0], tacke[i + 1][0]],
                            [tacke[i][1], tacke[i + 1][1]], color=boja,
                            lw=debljina, zorder=2, solid_capstyle="round")
                strelica = FancyArrowPatch(
                    tacke[-2], tacke[-1], arrowstyle="-|>",
                    mutation_scale=15, color=boja, lw=debljina, zorder=2,
                    shrinkA=0, shrinkB=0)
                ax.add_patch(strelica)
                continue

            # milestones (trajanje 0) su elipse, ostale aktivnosti kutije
            pocetak = tacka_na_ivici(poz[u], poz[y], trajanje[u] == 0)
            kraj = tacka_na_ivici(poz[y], poz[u], trajanje[y] == 0)
            strelica = FancyArrowPatch(
                pocetak, kraj, arrowstyle="-|>", mutation_scale=15,
                color=boja, lw=debljina, zorder=2, shrinkA=0, shrinkB=2)
            ax.add_patch(strelica)

    # ----- kratke strelice za ivice koje izlaze iz dijela
    for u in izlazne:
        ciljevi = sorted(izlazne[u])
        for k in range(len(ciljevi)):
            # strelice se podižu iznad sredine da ne budu na ivici prema
            # susjednoj kutiji u istom redu
            pomak = (k - (len(ciljevi) - 1) / 2) * 0.5 + 0.35
            y_strelice = poz[u][1] + pomak
            x_pocetka = poz[u][0] + SIRINA
            boja = CRNA
            debljina = 1.4
            if (u, ciljevi[k]) in krit_ivice:
                boja = CRVENA
                debljina = 2.6
            strelica = FancyArrowPatch(
                (x_pocetka, y_strelice), (x_pocetka + 0.75, y_strelice),
                arrowstyle="-|>", mutation_scale=15, color=boja,
                lw=debljina, zorder=2, shrinkA=0, shrinkB=0)
            ax.add_patch(strelica)
            ax.text(x_pocetka + 0.87, y_strelice, ciljevi[k], ha="left",
                    va="center", fontsize=11, fontweight="bold", color=boja)

    # ----- kratke strelice za ivice koje ulaze u dio
    for y in ulazne:
        izvori = sorted(ulazne[y])
        for k in range(len(izvori)):
            pomak = (k - (len(izvori) - 1) / 2) * 0.5
            y_strelice = poz[y][1] + pomak
            x_kraja = poz[y][0] - SIRINA
            boja = CRNA
            debljina = 1.4
            if (izvori[k], y) in krit_ivice:
                boja = CRVENA
                debljina = 2.6
            strelica = FancyArrowPatch(
                (x_kraja - 0.75, y_strelice), (x_kraja, y_strelice),
                arrowstyle="-|>", mutation_scale=15, color=boja,
                lw=debljina, zorder=2, shrinkA=0, shrinkB=0)
            ax.add_patch(strelica)
            ax.text(x_kraja - 0.87, y_strelice, izvori[k], ha="right",
                    va="center", fontsize=11, fontweight="bold", color=boja)

    # ----- kutije
    for v in vrhovi:
        x = poz[v][0]
        y = poz[v][1]
        if v in rez.kriticne:
            boja = CRVENA
            debljina = 3
        else:
            boja = CRNA
            debljina = 1.6

        if trajanje[v] == 0:
            # milestone: elipsa samo s nazivom, centriranim
            oblik = Ellipse((x, y), 2 * SIRINA, 2 * VISINA,
                            fc="white", ec=boja, lw=debljina, zorder=3)
            ax.add_patch(oblik)
            ax.text(x, y, v, ha="center", va="center", fontsize=10,
                    fontweight="bold", zorder=5)
        else:
            kutija = Rectangle((x - SIRINA, y - VISINA), 2 * SIRINA,
                               2 * VISINA, fc="white", ec=boja, lw=debljina,
                               zorder=3)
            ax.add_patch(kutija)

            # dvije vodoravne crte dijele kutiju na tri reda
            for dy in (0.28, -0.28):
                ax.plot([x - SIRINA, x + SIRINA], [y + dy, y + dy],
                        color=boja, lw=1, zorder=4)

            # naziv i trajanje u sredini
            ax.text(x, y, f"{v}\n(w = {br(trajanje[v])})", ha="center",
                    va="center", fontsize=10, fontweight="bold", zorder=5)

            # ES, EF, LS, LF u uglovima: (pomak po x, pomak po y, tekst, poravnanje)
            oznake = [(-1, 1, f"ES={br(rez.ES[v])}", "left"),
                      (1, 1, f"EF={br(rez.EF[v])}", "right"),
                      (-1, -1, f"LS={br(rez.LS[v])}", "left"),
                      (1, -1, f"LF={br(rez.LF[v])}", "right")]
            for dx, dy, tekst, poravnanje in oznake:
                ax.text(x + dx * (SIRINA - 0.1), y + dy * 0.44, tekst,
                        ha=poravnanje, va="center", fontsize=8, zorder=5)

        # slack se ispisuje iznad kutije za svaku aktivnost (i kad je 0),
        # osim za milestone sa slackom 0 (npr. start i end)
        slack = rez.slack[v]
        if abs(slack) < EPS:
            slack = 0
        if trajanje[v] > 0 or slack > 0:
            ax.text(x, y + VISINA + 0.28, f"slack = {br(slack)}",
                    ha="center", va="center", fontsize=8, fontweight="bold")

    ax.set_xlim(lijevo, desno)
    ax.set_ylim(najnize - 0.3, najvise + 0.3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(putanja, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def nacrtaj_gantt(rez, trajanje, putanja, jedinica="dana"):
    # Aktivnosti se poredaju po ES, pa po EF, pa po nazivu.
    # Sortiranje torki (ES, EF, naziv) radi baš tim redom.
    za_sortiranje = []
    for v in trajanje:
        za_sortiranje.append((rez.ES[v], rez.EF[v], v))
    za_sortiranje.sort()
    redom = []
    for es, ef, v in za_sortiranje:
        redom.append(v)

    n = len(redom)
    fig, ax = plt.subplots(figsize=(10, 1.6 + 0.38 * n))

    # Prva aktivnost treba biti na vrhu, a matplotlib crta od dna,
    # pa se ide obrnutim redoslijedom.
    obrnuto = list(reversed(redom))
    for i in range(n):
        v = obrnuto[i]
        if v in rez.kriticne:
            boja = CRVENA
        else:
            boja = PLAVA

        # traka aktivnosti: od ES, dužine jednake trajanju
        ax.barh(i, trajanje[v], left=rez.ES[v], height=0.6,
                color=boja, edgecolor="white", zorder=3)
        if trajanje[v] > 0:
            ax.text(rez.ES[v] + trajanje[v] / 2, i, br(trajanje[v]),
                    ha="center", va="center", color="white", fontsize=8,
                    fontweight="bold", zorder=4)

        # šrafirana traka iza aktivnosti pokazuje slack
        if rez.slack[v] > EPS:
            ax.barh(i, rez.slack[v], left=rez.EF[v], height=0.6, color="none",
                    edgecolor=PLAVA, hatch="///", lw=1, zorder=3)

    ax.set_yticks(range(n))
    ax.set_yticklabels(obrnuto)

    # na dugim projektima oznake na x-osi ne idu svaki dan
    if rez.T <= 40:
        korak = 1
    else:
        korak = max(1, int(rez.T // 20))
    ax.set_xticks(range(0, int(rez.T) + 1, korak))
    ax.set_xlim(0, rez.T + 0.5)
    ax.set_xlabel(f"Vrijeme ({jedinica})")
    ax.grid(axis="x", color="#dddddd", zorder=0)
    ax.set_axisbelow(True)

    legenda = [Patch(fc=CRVENA, label="kritična aktivnost (slack = 0)"),
               Patch(fc=PLAVA, label="nekritična aktivnost"),
               Patch(fc="white", ec=PLAVA, hatch="///",
                     label="slack (vremenska rezerva)")]
    ax.legend(handles=legenda, loc="upper center", bbox_to_anchor=(0.5, -0.1),
              ncol=3, fontsize=8, frameon=False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.savefig(putanja, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)