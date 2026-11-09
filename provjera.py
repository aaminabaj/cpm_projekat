"""
Provjera ispravnosti CPM rezultata dvjema nezavisnim metodama:
  1. grubom silom: nabrojati SVE puteve od početka do kraja i uzeti najduži
     (direktno iz definicije, radi samo za male projekte),
  2. bibliotekom NetworkX: najduži putevi preko Bellman-Fordovog algoritma.
Nijedna od njih ne koristi forward/backward pass iz cpm.py.
"""
from cpm import EPS, kriticni_putevi, sljedbenici_iz


def najduzi_putevi_grubom_silom(trajanje, prethodnici, najvise_puteva=1000000):
    """Vraća (T, lista svih najdužih puteva) nabrajanjem svih puteva.
    Putevi se produžavaju korak po korak, od početnih aktivnosti do završnih.
    Ako puteva ima više od 'najvise_puteva', vraća (None, None)."""
    #za male projekte brzo ali za velike nije izvodljivo (puteva moze biti eksponenc mnogo)
    sljedbenici = sljedbenici_iz(prethodnici)

    # Počinje se s putevima koji imaju samo jednu aktivnost:
    # svaka aktivnost bez prethodnika je početak jednog puta.
    tekuci = [] #lista puteva
    for v in trajanje:
        if len(prethodnici[v]) == 0:
            tekuci.append([v])

    gotovi = [] # putevi koji su stigli do kraja projekta
    while len(tekuci) > 0:
        novi = [] # putevi produženi za jednu aktivnost
        for put in tekuci:
            zadnja = put[-1] #za svaki trenutni uzima se posljednja aktivnost na putu (-1)
            if len(sljedbenici[zadnja]) == 0:
                gotovi.append(put) #ako poslj akt nema sljedbenik, put je kompletan
            else:
                for s in sljedbenici[zadnja]: #za svakog sljedbenika se pravi novi put
                    novi.append(put + [s])   # put se grana kroz svakog sljedbenika
        if len(novi) > najvise_puteva:
            return None, None  # previše puteva za nabrajanje
        tekuci = novi

    # Dužina puta je zbir trajanja njegovih aktivnosti.
    duzine = []
    najveca = 0
    for put in gotovi:
        zbir = 0
        for v in put:
            zbir = zbir + trajanje[v]
        duzine.append(zbir)
        if zbir > najveca:
            najveca = zbir

    # Najduži su svi putevi čija je dužina jednaka najvećoj.
    najduzi = []
    for i in range(len(gotovi)):
        if abs(duzine[i] - najveca) <= EPS:
            najduzi.append(gotovi[i])
    return najveca, najduzi


def vrijednosti_networkx(trajanje, prethodnici):
    """EF i LF za svaku aktivnost, računati kao najduži putevi u NetworkX-u.
    Težina vrha je prebačena na ivice: ivica (u, v) dobija težinu w(v)."""
    #koristi Bellman-Fordov algoritam iz biblioteke - problem jer networkx racuna s tezinama na ivicama
    import networkx as nx
    sljedbenici = sljedbenici_iz(prethodnici)

    # Težine su negativne: najduži put je isto što i najkraći put s
    # negativnim težinama (to je dozvoljeno jer graf nema cikluse).
    G = nx.DiGraph()
    for v in trajanje:
        if len(prethodnici[v]) == 0:
            G.add_edge("POCETAK", v, weight=-trajanje[v])
        for s in sljedbenici[v]:
            G.add_edge(v, s, weight=-trajanje[s])
        if len(sljedbenici[v]) == 0:
            G.add_edge(v, "KRAJ", weight=0)

    # dužine najkraćih (ovdje najdužih) puteva od POCETKA do svakog vrha
    od_pocetka = nx.single_source_bellman_ford_path_length(G, "POCETAK")
    EF = {}
    for v in trajanje:
        EF[v] = -od_pocetka[v]
    T = -od_pocetka["KRAJ"]

    # isto na obrnutom grafu, od KRAJA unazad
    do_kraja = nx.single_source_bellman_ford_path_length(G.reverse(), "KRAJ")
    LF = {}
    for v in trajanje:
        LF[v] = T + do_kraja[v]
    return T, EF, LF


def provjeri(trajanje, prethodnici, rez):
    """Baca AssertionError ako se bilo koji rezultat razlikuje."""
    # ----- provjera 1: NetworkX
    T_nx, EF_nx, LF_nx = vrijednosti_networkx(trajanje, prethodnici)
    assert abs(rez.T - T_nx) < EPS, f"T: {rez.T} != {T_nx} (NetworkX)"
    for v in trajanje:
        assert abs(rez.EF[v] - EF_nx[v]) < EPS, f"EF({v}) se razlikuje"
        assert abs(rez.LF[v] - LF_nx[v]) < EPS, f"LF({v}) se razlikuje"
    print("\nProvjera 1 (NetworkX): T, EF i LF svih aktivnosti se poklapaju.")

    # ----- provjera 2: gruba sila
    T_gs, putevi_gs = najduzi_putevi_grubom_silom(trajanje, prethodnici)
    if T_gs is None:
        print("Provjera 2 (gruba sila) je preskočena: projekat ima previše puteva.")
        return
    assert abs(rez.T - T_gs) < EPS, f"T: {rez.T} != {T_gs} (gruba sila)"

    # Putevi se porede kao skupovi (tuple jer liste ne mogu u skup).
    nasi = set()
    for put in kriticni_putevi(rez, prethodnici):
        nasi.add(tuple(put))
    ocekivani = set()
    for put in putevi_gs:
        ocekivani.add(tuple(put))
    assert nasi == ocekivani, "kritični putevi se razlikuju"
    print("Provjera 2 (gruba sila): T i svi kritični putevi se poklapaju.")