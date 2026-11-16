# -*- coding: utf-8 -*-
"""
Created on Wed Jul  9 12:12:08 2025

@author: abelg
"""

import sqlite3
from tabulate import tabulate


def jornades_guanyades_i_derrotes_ajustades(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jornada
        FROM Entrada
        WHERE minut_final = 40
          AND (
              punts_favor_final > punts_contra_final
              OR (punts_contra_final > punts_favor_final AND (punts_contra_final - punts_favor_final) <= 5)
          )
        GROUP BY jornada
        ORDER BY jornada
    """)

    jornades = [fila[0] for fila in cursor.fetchall()]
    conn.close()
    print("Jornades Analitzades", jornades)
    return jornades

def minuts_jugats(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cond_jornades = ""
    params = ()
    if jornades_valides:
        cond_jornades = "WHERE e.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params = jornades_valides
        
    #si no hi ha jornades ajustades es tornen totes pq no entrem al IF

    query = f"""
        SELECT j.nom, j.cognom,
               COUNT(DISTINCT e.jornada) AS partits_jugats,
               SUM(e.minuts_jugats) AS total_minuts,
               ROUND(SUM(e.minuts_jugats) * 1.0 / COUNT(DISTINCT e.jornada), 2) AS minuts_per_partit
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        {cond_jornades}
        GROUP BY j.nom, j.cognom
        ORDER BY j.nom, j.cognom
    """
    cursor.execute(query, params)
    resultats = cursor.fetchall()
    conn.close()
    return resultats


def calcula_on_off(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Balanç ON (quan està en pista i en jornades vàlides)
    cond_jornades_on = ""
    params_on = ()
    if jornades_valides:
        cond_jornades_on = "AND e.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params_on = jornades_valides

    cursor.execute(f"""
        SELECT j.id_jugador, j.nom, 
               IFNULL(SUM(e.balanc), 0) AS balanc_on
        FROM Jugador j
        LEFT JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        LEFT JOIN Cinc c ON cc.id_cinc = c.id_cinc
        LEFT JOIN Entrada e ON c.id_cinc = e.id_cinc {cond_jornades_on}
        GROUP BY j.id_jugador
    """, params_on)
    on_data = {row[0]: {"nom": row[1], "on": row[2]} for row in cursor.fetchall()}

    # 2. Balanç OFF (quan NO està en pista però en jornades on ha jugat i jornades vàlides)
    params_off = ()
    cond_jornades_off = ""
    if jornades_valides:
        cond_jornades_off = "AND e2.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params_off = jornades_valides

    cursor.execute(f"""
        SELECT j.id_jugador, j.nom, 
               IFNULL(SUM(e.balanc), 0) AS balanc_off
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


def plus_minus_ajustat(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades_final = []
    total_minuts = 0
    total_diferencia = 0
    jugador_dades = []

    cond_jornades = ""
    params = ()
    if jornades_valides:
        cond_jornades = "AND e.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params = jornades_valides

    for id_jugador, nom in jugadors:
        cursor.execute(f"""
            SELECT SUM(e.minuts_jugats),
                   SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici))
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ? {cond_jornades}
        """, (id_jugador, *params))
        fila = cursor.fetchone()
        minuts_jugador = fila[0] or 0
        plus_minus = fila[1] or 0

        total_minuts += minuts_jugador
        total_diferencia += plus_minus

        jugador_dades.append((nom, minuts_jugador, plus_minus))

    for nom, minuts_jugador, plus_minus in jugador_dades:
        if minuts_jugador == 0 or total_minuts == 0:
            ajustat = None
        else:
            mitjana_equip = total_diferencia / total_minuts
            mitjana_jugador = plus_minus / minuts_jugador
            ajustat = mitjana_jugador - mitjana_equip

        dades_final.append([nom, minuts_jugador, plus_minus, round(ajustat, 2) if ajustat is not None else None])

    conn.close()
    return dades_final


def atac_per_minut_per_jugador(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cond_jornades = ""
    params = ()
    if jornades_valides:
        cond_jornades = "WHERE e.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params = jornades_valides

    query = f"""
        SELECT j.nom,
               SUM(e.punts_favor_final - e.punts_favor_inici) AS total_punts_anotats,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_favor_final - e.punts_favor_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        {cond_jornades}
        GROUP BY j.nom
        ORDER BY punts_per_minut DESC
    """

    cursor.execute(query, params)
    resultats = cursor.fetchall()
    conn.close()
    return resultats


def defensa_per_minut_per_jugador(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cond_jornades = ""
    params = ()
    if jornades_valides:
        cond_jornades = "WHERE e.jornada IN ({seq})".format(seq=','.join(['?']*len(jornades_valides)))
        params = jornades_valides

    query = f"""
        SELECT j.nom,
               SUM(e.punts_contra_final - e.punts_contra_inici) AS total_punts_rebuts,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_contra_final - e.punts_contra_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_concedits_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        {cond_jornades}
        GROUP BY j.nom
        ORDER BY punts_concedits_per_minut ASC
    """

    cursor.execute(query, params)
    resultats = cursor.fetchall()
    conn.close()
    return resultats


def atac_on_off(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades = []

    for id_jugador, nom in jugadors:
        params_on = [id_jugador]
        cond_jornada = ""
        if jornades_valides:
            cond_jornada = f"AND e.jornada IN ({','.join(['?']*len(jornades_valides))})"
            params_on += jornades_valides

        consulta_on = f"""
            SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ?
            {cond_jornada}
        """
        cursor.execute(consulta_on, params_on)
        punts_on = cursor.fetchone()[0] or 0

        # Atac OFF
        params_off = [id_jugador]
        subquery_cond = ""
        if jornades_valides:
            subquery_cond = f"AND e2.jornada IN ({','.join(['?']*len(jornades_valides))})"
            params_off += jornades_valides

        params_off.append(id_jugador)
        if jornades_valides:
            params_off += jornades_valides

        consulta_off = f"""
            SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
            FROM Entrada e
            JOIN (
                SELECT DISTINCT e2.jornada
                FROM Entrada e2
                JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
                JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
                WHERE cc2.id_jugador = ?
                {subquery_cond}
            ) jugades ON e.jornada = jugades.jornada
            WHERE e.id_cinc NOT IN (
                SELECT c.id_cinc
                FROM Cinc c
                JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
                WHERE cc.id_jugador = ?
            )
            {cond_jornada}
        """
        cursor.execute(consulta_off, params_off)
        punts_off = cursor.fetchone()[0] or 0

        diferencia = punts_on - punts_off
        dades.append([nom, punts_on, punts_off, diferencia])

    conn.close()
    return dades


def defensa_on_off(nom_base_dades, jornades_valides=None):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades = []

    for id_jugador, nom in jugadors:
        params_on = [id_jugador]
        cond_jornada = ""
        if jornades_valides:
            cond_jornada = f"AND e.jornada IN ({','.join(['?']*len(jornades_valides))})"
            params_on += jornades_valides

        consulta_on = f"""
            SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ?
            {cond_jornada}
        """
        cursor.execute(consulta_on, params_on)
        punts_on = cursor.fetchone()[0] or 0

        # Defensa OFF
        params_off = [id_jugador]
        subquery_cond = ""
        if jornades_valides:
            subquery_cond = f"AND e2.jornada IN ({','.join(['?']*len(jornades_valides))})"
            params_off += jornades_valides

        params_off.append(id_jugador)
        if jornades_valides:
            params_off += jornades_valides

        consulta_off = f"""
            SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
            FROM Entrada e
            JOIN (
                SELECT DISTINCT e2.jornada
                FROM Entrada e2
                JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
                JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
                WHERE cc2.id_jugador = ?
                {subquery_cond}
            ) jugades ON e.jornada = jugades.jornada
            WHERE e.id_cinc NOT IN (
                SELECT c.id_cinc
                FROM Cinc c
                JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
                WHERE cc.id_jugador = ?
            )
            {cond_jornada}
        """
        cursor.execute(consulta_off, params_off)
        punts_off = cursor.fetchone()[0] or 0

        diferencia = punts_off - punts_on
        dades.append([nom, punts_on, punts_off, diferencia])

    conn.close()
    return dades





def crea_taula_general(nom_base_dades, jornades_valides=None):
    taula_general = {}  
    
    
    jornades_valides = jornades_guanyades_i_derrotes_ajustades(nom_base_dades)
    print(jornades_valides)
    
    # MINUTS JUGATS
    minuts = minuts_jugats(nom_base_dades, jornades_valides)
    for jugador in minuts:
        taula_general[jugador[0]] = {
            "cognoms": jugador[1],
            "partits jugats": jugador[2],
            "minuts totals": jugador[3],
            "minuts per partit": jugador[4],
        }

    # ON/OFF
    on_off = calcula_on_off(nom_base_dades, jornades_valides)
    for jugador in on_off:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["balanç on"] = jugador[1]
            taula_general[jugador[0]]["balanç off"] = jugador[2]
            taula_general[jugador[0]]["on/off"] = jugador[3]

    # PLUS-MINUS AJUSTAT
    ajustat = plus_minus_ajustat(nom_base_dades, jornades_valides)
    for jugador in ajustat:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["plus minus ajustat"] = jugador[3]

    # ATAC PER MINUT
    atac_minut = atac_per_minut_per_jugador(nom_base_dades, jornades_valides)
    for jugador in atac_minut:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["punts anotats pista"] = jugador[1]
            taula_general[jugador[0]]["punts anotats_per minut"] = jugador[3]

    # DEFENSA PER MINUT
    defensa_minut = defensa_per_minut_per_jugador(nom_base_dades, jornades_valides)
    for jugador in defensa_minut:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["punts rebuts pista"] = jugador[1]
            taula_general[jugador[0]]["punts rebuts per minut"] = jugador[3]
            atac = taula_general[jugador[0]]["punts anotats_per minut"] - jugador[3]
            taula_general[jugador[0]]["net rating"] = round(atac, 2) 

    # ATAC ON/OFF
    atac_on = atac_on_off(nom_base_dades, jornades_valides)
    for jugador in atac_on:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["on/off atac"] = jugador[3]

    # DEFENSA ON/OFF
    defensa_on = defensa_on_off(nom_base_dades, jornades_valides)
    for jugador in defensa_on:
        if jugador[0] in taula_general:
            taula_general[jugador[0]]["on/off defensa"] = jugador[3]

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
    else:
        print("Cap dada a mostrar.")


if __name__ == "__main__":
    
    nom_base_dades = "CB_IMMA.db"
    crea_taula_general(nom_base_dades)
