# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 17:52:37 2025

@author: abelg
"""

import sqlite3
from collections import defaultdict
from tabulate import tabulate


def titulars_i_suplents(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    jugador_titular = defaultdict(list)
    jugador_suplent = defaultdict(list)

    # Obtenim totes les jornades presents a Entrada
    cursor.execute("SELECT DISTINCT jornada FROM Entrada")
    jornades = [fila[0] for fila in cursor.fetchall()]

    for jornada in jornades:
        # Jugadors que han jugat algun minut en aquesta jornada
        cursor.execute("""
            SELECT DISTINCT j.id_jugador
            FROM Jugador j
            JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
            JOIN Cinc c ON cc.id_cinc = c.id_cinc
            JOIN Entrada e ON c.id_cinc = e.id_cinc
            WHERE e.jornada = ?
        """, (jornada,))
        han_jugat = {fila[0] for fila in cursor.fetchall()}

        # Jugadors titulars (amb minut_inici = 0 en aquesta jornada)
        cursor.execute("""
            SELECT DISTINCT j.id_jugador
            FROM Jugador j
            JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
            JOIN Cinc c ON cc.id_cinc = c.id_cinc
            JOIN Entrada e ON c.id_cinc = e.id_cinc
            WHERE e.jornada = ? AND e.minut_inici = 0
        """, (jornada,))
        titulars = {fila[0] for fila in cursor.fetchall()}

        suplents = han_jugat - titulars

        for id_j in titulars:
            jugador_titular[id_j].append(jornada)
        for id_j in suplents:
            jugador_suplent[id_j].append(jornada)

    conn.close()
    return dict(jugador_titular), dict(jugador_suplent)



def filtra_diccionaris_comuns(d1, d2, min_aparicions=5):
    """
    Retorna dues còpies filtrades dels diccionaris `d1` i `d2`, amb només aquells jugadors
    que apareixen als dos i tenen com a mínim `min_aparicions` en cada diccionari.
    
    Paràmetres:
        d1, d2 (dict): Diccionaris amb el format {jugador: llista_de_jornades}
        min_aparicions (int): Nombre mínim d'aparicions requerides per jugador

    Retorna:
        d1_filtrat, d2_filtrat (dict, dict): Diccionaris filtrats
    """
    jugadors_comuns = {
        jugador for jugador in d1
        if jugador in d2 and len(d1[jugador]) >= min_aparicions and len(d2[jugador]) >= min_aparicions
    }

    d1_filtrat = {jugador: d1[jugador] for jugador in jugadors_comuns}
    d2_filtrat = {jugador: d2[jugador] for jugador in jugadors_comuns}
    
    return d1_filtrat, d2_filtrat





def minuts_jugats(nom_base_dades, jornades_valides=None, nom_jugador=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    condicions = []
    params = []

    if jornades_valides:
        condicions.append("e.jornada IN ({})".format(','.join(['?'] * len(jornades_valides))))
        params.extend(jornades_valides)

    if nom_jugador:
        condicions.append("j.id_jugador = ?")
        params.append(nom_jugador)

    condicio_final = f"WHERE {' AND '.join(condicions)}" if condicions else ""

    query = f"""
        SELECT j.nom, j.cognom,
               COUNT(DISTINCT e.jornada) AS partits_jugats,
               SUM(e.minuts_jugats) AS total_minuts,
               ROUND(SUM(e.minuts_jugats) * 1.0 / COUNT(DISTINCT e.jornada), 2) AS minuts_per_partit
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        {condicio_final}
        GROUP BY j.nom, j.cognom
        ORDER BY j.nom, j.cognom
    """
    cursor.execute(query, params)
    resultats = cursor.fetchall()
    conn.close()
    return resultats
    

def calcula_on_off(nom_base_dades, jornades_valides=None, nom_jugador=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cond_jornades_on = ""
    cond_jug = ""
    params_on = []

    if jornades_valides:
        cond_jornades_on += "AND e.jornada IN ({}) ".format(','.join(['?'] * len(jornades_valides)))
        params_on.extend(jornades_valides)

    if nom_jugador:
        cond_jug += "AND j.id_jugador = ? "
        params_on.append(nom_jugador)

    cursor.execute(f"""
        SELECT j.id_jugador, j.nom, IFNULL(SUM(e.balanc), 0) AS balanc_on
        FROM Jugador j
        LEFT JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        LEFT JOIN Cinc c ON cc.id_cinc = c.id_cinc
        LEFT JOIN Entrada e ON c.id_cinc = e.id_cinc
        WHERE 1=1 {cond_jornades_on} {cond_jug}
        GROUP BY j.id_jugador
    """, params_on)

    on_data = {row[0]: {"nom": row[1], "on": row[2]} for row in cursor.fetchall()}

    cond_jornades_off = ""
    params_off = []
    if jornades_valides:
        cond_jornades_off += "AND e2.jornada IN ({}) ".format(','.join(['?'] * len(jornades_valides)))
        params_off.extend(jornades_valides)
    if nom_jugador:
        cond_jornades_off += "AND j2.id_jugador = ? "
        params_off.append(nom_jugador)

    cursor.execute(f"""
        SELECT j.id_jugador, j.nom, IFNULL(SUM(e.balanc), 0) AS balanc_off
        FROM Jugador j
        JOIN (
            SELECT DISTINCT j2.id_jugador, e2.jornada
            FROM Jugador j2
            JOIN Components_cinc cc2 ON j2.id_jugador = cc2.id_jugador
            JOIN Cinc c2 ON cc2.id_cinc = c2.id_cinc
            JOIN Entrada e2 ON c2.id_cinc = e2.id_cinc
            WHERE 1=1 {cond_jornades_off}
        ) jugades ON j.id_jugador = jugades.id_jugador
        JOIN Entrada e ON e.jornada = jugades.jornada
        WHERE e.id_cinc NOT IN (
            SELECT c.id_cinc
            FROM Cinc c
            JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
            WHERE cc.id_jugador = j.id_jugador
        )
        GROUP BY j.id_jugador
    """, params_off)

    for row in cursor.fetchall():
        id_jugador = row[0]
        balanc_off = row[2]
        if id_jugador in on_data:
            on_data[id_jugador]["off"] = balanc_off
        else:
            on_data[id_jugador] = {"nom": row[1], "on": 0, "off": balanc_off}

    resultats = []
    for jugador in on_data.values():
        bal_on = jugador.get("on", 0)
        bal_off = jugador.get("off", 0)
        on_off = bal_on - bal_off
        resultats.append([jugador["nom"], bal_on, bal_off, on_off])
   
    conn.close()
    return resultats

from collections import defaultdict
import sqlite3

def plus_minus_ajustat_global(nom_base_dades, jornades_valides=None, nom_jugador=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    if jornades_valides:
        jornades = jornades_valides
    else:
        cursor.execute("SELECT DISTINCT id_jornada FROM Entrada")
        jornades = [fila[0] for fila in cursor.fetchall()]

    totals_jugador = defaultdict(lambda: {'minuts': 0, 'plus_minus': 0})
    total_equips = {'minuts': 0, 'plus_minus': 0}

    for id_jornada in jornades:
        cursor.execute("""
            SELECT SUM(e.minuts_jugats),
                   SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici))
            FROM Entrada e
            WHERE e.jornada = ?
        """, (id_jornada,))
        total_minuts, total_diferencia = cursor.fetchone()
        if not total_minuts or total_minuts == 0:
            continue

        total_equips['minuts'] += total_minuts
        total_equips['plus_minus'] += total_diferencia

        condicions = "e.jornada = ?"
        valors = [id_jornada]

        if nom_jugador:
            condicions += " AND j.id_jugador = ?"
            valors.append(nom_jugador)

        cursor.execute(f"""
            SELECT j.nom, SUM(e.minuts_jugats), 
                   SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici))
            FROM Jugador j
            JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
            JOIN Cinc c ON cc.id_cinc = c.id_cinc
            JOIN Entrada e ON e.id_cinc = c.id_cinc
            WHERE {condicions}
            GROUP BY j.nom
        """, valors)

        for nom, minuts_jugador, plus_minus in cursor.fetchall():
            totals_jugador[nom]['minuts'] += minuts_jugador
            totals_jugador[nom]['plus_minus'] += plus_minus

    conn.close()

    if total_equips['minuts'] == 0:
        return []

    mitjana_equip_global = total_equips['plus_minus'] / total_equips['minuts']

    resultat_final = []
    for nom, dades in totals_jugador.items():
        minuts = dades['minuts']
        plus_minus = dades['plus_minus']
        if minuts == 0:
            ajustat = None
        else:
            mitjana_jugador = plus_minus / minuts
            ajustat = mitjana_jugador - mitjana_equip_global

        resultat_final.append([
            nom,
            minuts,
            plus_minus,
            round(ajustat, 2) if ajustat is not None else None
        ])
    
    #print(resultat_final)
    return resultat_final



def atac_per_minut_per_jugador_i_jornada(nom_base_dades, id_jugador, jornades_valides):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    placeholders = ','.join(['?'] * len(jornades_valides))
    query = f"""
        SELECT j.id_jugador,
               SUM(e.punts_favor_final - e.punts_favor_inici) AS total_punts_anotats,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_favor_final - e.punts_favor_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        WHERE j.id_jugador = ? AND e.jornada IN ({placeholders})
        GROUP BY j.id_jugador
    """
    
    cursor.execute(query, [id_jugador] + jornades_valides)
    resultats = cursor.fetchall()
    conn.close()
    return resultats




def defensa_per_minut_per_jugador_i_jornada(nom_base_dades, jornades_valides=None, nom_jugador=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    condicions = []
    valors = []

    if nom_jugador:
        condicions.append("j.id_jugador = ?")
        valors.append(nom_jugador)

    if jornades_valides:
        if isinstance(jornades_valides, str):
            jornades_valides = [int(j.strip()) for j in jornades_valides.split(",")]
        placeholders = ",".join(["?"] * len(jornades_valides))
        condicions.append(f"e.jornada IN ({placeholders})")
        valors.extend(jornades_valides)

    where_clause = "WHERE " + " AND ".join(condicions) if condicions else ""

    query = f"""
        SELECT j.nom,
               SUM(e.punts_contra_final - e.punts_contra_inici) AS total_punts_rebuts,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_contra_final - e.punts_contra_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        {where_clause}
        GROUP BY j.id_jugador
    """

    cursor.execute(query, valors)
    resultats = cursor.fetchall()
    conn.close()
    return resultats

def atac_on_off_jugador_jornada(nom_base_dades, nom_jugador, jornades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Obtenir l'id del jugador
    cursor.execute("SELECT id_jugador FROM Jugador WHERE id_jugador = ?", (nom_jugador,))
    fila = cursor.fetchone()
    if not fila:
        conn.close()
        return f"Jugador {nom_jugador} no trobat."
    id_jugador = fila[0]

    # Convertir la llista de jornades en placeholders (?, ?, ?...)
    placeholders = ",".join(["?"] * len(jornades))

    # ATAC ON: punts a favor mentre és en pista en les jornades indicades
    cursor.execute(f"""
        SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador = ? AND e.jornada IN ({placeholders})
    """, [id_jugador] + jornades)
    punts_on = cursor.fetchone()[0] or 0

    # ATAC OFF: en les mateixes jornades, però minuts en què no està a pista
    cursor.execute(f"""
        SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
        FROM Entrada e
        WHERE e.jornada IN ({placeholders})
          AND e.id_cinc NOT IN (
              SELECT c.id_cinc
              FROM Cinc c
              JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
              WHERE cc.id_jugador = ?
          )
    """, jornades + [id_jugador])
    punts_off = cursor.fetchone()[0] or 0

    diferencia = punts_on - punts_off

    conn.close()
    return [nom_jugador, jornades, punts_on, punts_off, diferencia]



def defensa_on_off_jugador_jornada(nom_base_dades, nom_jugador, jornades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Obtenir l'id del jugador
    cursor.execute("SELECT id_jugador FROM Jugador WHERE id_jugador = ?", (nom_jugador,))
    fila = cursor.fetchone()
    if not fila:
        conn.close()
        return f"Jugador {nom_jugador} no trobat."
    id_jugador = fila[0]

    # Crear placeholders (?, ?, ...) segons la mida de jornades
    placeholders = ",".join(["?"] * len(jornades))

    # DEFENSA ON: punts en contra mentre és en pista en les jornades indicades
    cursor.execute(f"""
        SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador = ? AND e.jornada IN ({placeholders})
    """, [id_jugador] + jornades)
    punts_on = cursor.fetchone()[0] or 0

    # DEFENSA OFF: minuts en què NO està en pista en les mateixes jornades
    cursor.execute(f"""
        SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
        FROM Entrada e
        WHERE e.jornada IN ({placeholders})
          AND e.id_cinc NOT IN (
              SELECT c.id_cinc
              FROM Cinc c
              JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
              WHERE cc.id_jugador = ?
          )
    """, jornades + [id_jugador])
    punts_off = cursor.fetchone()[0] or 0

    diferencia = punts_off - punts_on

    conn.close()
    return [nom_jugador, jornades, punts_on, punts_off, diferencia]





def crea_taula_tiulars_suplents(nom_base_dades, diccionari_filtrats):
    
    taula_general = {}
    
    for jugador, jornades in diccionari_filtrats.items():
            
        #MINUTS
        minuts = minuts_jugats(nom_base_dades, jornades, jugador)[0]
        
        #nom, cognoms, partits_jugats, total_minuts, minuts_partit
        
            
        taula_general[jugador] = {}
        taula_general[jugador]["cognoms"] = minuts[1]
        taula_general[jugador]["partits_jugats"] = minuts[2]
        taula_general[jugador]["minuts_totals"] = minuts[3]
        taula_general[jugador]["minuts_per_partit"] = minuts[4]
        
        
        
        #ON_OFF
        
        on_off = calcula_on_off(nom_base_dades,jornades,jugador)[0]
        #nom, balanç on, balanç off, diferència
        taula_general[jugador]["balanç_on"] = on_off[1]
        taula_general[jugador]["balanç_off"] = on_off[2]
        taula_general[jugador]["on/off"] = on_off[3]
        
        #PLUS_MINUS_AJUSTAT
        ajustat = plus_minus_ajustat_global(nom_base_dades,jornades,jugador)[0]
        
        
        
        taula_general[jugador]["plus_minus_ajustat"] = round(ajustat[3],2)
        
        
        
        #ATAC PER MINUT
        atac_minut = atac_per_minut_per_jugador_i_jornada (nom_base_dades,jugador,jornades,)[0]
        
        
        
        taula_general[jugador]["punts_anotats_pista"] = atac_minut[2]
        taula_general[jugador]["punts_anotats_per_minut"] = atac_minut[3]
        
        
        #DEFENSA_PER_MINUT
        defensa_minut = defensa_per_minut_per_jugador_i_jornada(nom_base_dades,jornades,jugador)[0]
        
        taula_general[jugador]["punts_rebuts_pista"] = defensa_minut[2]
        taula_general[jugador]["punts_rebuts_per_minut"] = defensa_minut[3]
        
        net = atac_minut[3] - defensa_minut[3]
        taula_general[jugador]["net rating"] = round(net,2)
            
        
        #ATAC ON/OFF
        atac_on = atac_on_off_jugador_jornada(nom_base_dades,jugador,jornades)
        
        
        taula_general[jugador]["on/off atac"] = atac_on[4]
        
        
        #DEFENSA ON/OFF
        defensa_on = defensa_on_off_jugador_jornada(nom_base_dades, jugador, jornades)
        taula_general[jugador]["on/off defensa"] = defensa_on[4] 
        
        
    # Convertim el diccionari en una llista de diccionaris
    taula_llista = []
    for nom, estadistiques in taula_general.items():
        fila = {"nom": nom}
        fila.update(estadistiques)
        taula_llista.append(fila)
    # Ordenem per nom
    taula_llista.sort(key=lambda x: x["nom"])
    
    # Imprimim com a TSV
    if taula_llista:
        # Obtenim l'ordre de les columnes a partir de la primera fila
        caps = list(taula_llista[0].keys())
        print('\t'.join(caps))
        for fila in taula_llista:
            print('\t'.join(str(fila.get(camp, '')) for camp in caps))
    
        

if __name__ == "__main__":
    
    nom_base_dades = "CB_IMMA.db"
    titulars, suplents = titulars_i_suplents(nom_base_dades)
    
    
    titulars_filtrats, suplents_filtrats = filtra_diccionaris_comuns(titulars,suplents, min_aparicions=5)
    
    
    print("TAULA TITULARS")
    crea_taula_tiulars_suplents(nom_base_dades, titulars_filtrats) 
    print("TAULA SUPLENTS")
    crea_taula_tiulars_suplents(nom_base_dades, suplents_filtrats)
    
    

   