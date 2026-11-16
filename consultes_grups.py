# -*- coding: utf-8 -*-
"""
Created on Sat Jul 12 11:30:04 2025

@author: abelg
"""

import sqlite3
from collections import defaultdict
from itertools import combinations
from tabulate import tabulate



def llista_ids_jugadors(nom_base_dades):
    # Obre la connexió a la base de dades
    conn = sqlite3.connect(nom_base_dades)
    cursor = conn.cursor()
    
    # Obtenim només els id_jugador com a valors sencers (no com tuples d'un element)
    cursor.execute("SELECT id_jugador FROM jugador")
    resultats = cursor.fetchall()
    jugadors = [fila[0] for fila in resultats]  # extreu només l'ID
    
    # Combinacions de 2 en 2
    comb_2 = list(combinations(jugadors, 2))
    comb_3 = list(combinations(jugadors, 3))
    

    return comb_2, comb_3

def llista_ids_jugadors_5(nom_base_dades):
    # Obre la connexió a la base de dades
    conn = sqlite3.connect(nom_base_dades)
    cursor = conn.cursor()
    
    # Obtenim només els id_jugador com a valors sencers (no com tuples d'un element)
    cursor.execute("SELECT id_jugador FROM jugador")
    resultats = cursor.fetchall()
    jugadors = [fila[0] for fila in resultats]  # extreu només l'ID
    
    # Combinacions de 2 en 2
    comb_5 = list(combinations(jugadors, 5))

    return comb_5




def minuts_jugats_conjunts(nom_base_dades, ids_jugadors):
    if not ids_jugadors:
        return (tuple(), 0)  # Si no hi ha jugadors, no hi ha minuts conjunts

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Fem un JOIN per cada jugador per assegurar que tots estan en el mateix cinc
    joins = ""
    params = []
    for i, id_j in enumerate(ids_jugadors):
        joins += f"""
        JOIN Components_cinc cc{i} ON cc{i}.id_cinc = c.id_cinc AND cc{i}.id_jugador = ?
        """
        params.append(id_j)

    query = f"""
    SELECT SUM(e.minuts_jugats)
    FROM Cinc c
    {joins}
    JOIN Entrada e ON e.id_cinc = c.id_cinc
    """

    cursor.execute(query, params)
    suma_minuts = cursor.fetchone()[0] or 0
    conn.close()

    return [tuple(ids_jugadors), suma_minuts]



def calcula_on_off_grup(nom_base_dades, ids_jugadors):
    

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # ---------- 1. Subquery per trobar els cincs ON ----------
    joins = ""
    params = []
    for i, id_j in enumerate(ids_jugadors):
        joins += f"""
        JOIN Components_cinc cc{i} ON cc{i}.id_cinc = c.id_cinc AND cc{i}.id_jugador = ?
        """
        params.append(id_j)

    subquery_cincs_on = f"""
        SELECT c.id_cinc
        FROM Cinc c
        {joins}
    """

    # ---------- 2. Balanç ON ----------
    query_on = f"""
        SELECT SUM(e.balanc)
        FROM Entrada e
        WHERE e.id_cinc IN ({subquery_cincs_on})
    """
    cursor.execute(query_on, params)
    balanc_on = cursor.fetchone()[0] or 0

    # ---------- 3. Subquery: jornades on han jugat junts ----------
    subquery_jornades_on = f"""
        SELECT DISTINCT e.jornada
        FROM Entrada e
        WHERE e.id_cinc IN ({subquery_cincs_on})
    """

    # ---------- 4. Balanç OFF ----------
    # A les jornades en què han coincidit, però en cincs on no hi són tots
    query_off = f"""
        SELECT SUM(e.balanc)
        FROM Entrada e
        WHERE e.jornada IN ({subquery_jornades_on})
          AND e.id_cinc NOT IN ({subquery_cincs_on})
    """
    cursor.execute(query_off, params * 2)  # perquè apareix dues vegades
    balanc_off = cursor.fetchone()[0] or 0

    conn.close()
    return [(tuple(ids_jugadors), balanc_on, balanc_off, balanc_on - balanc_off)]



def plus_minus_ajustat_grup(nom_base_dades, ids_jugadors):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    if not ids_jugadors:
        return None

    # Construïm joins per trobar els cincs on estan tots
    joins = ""
    params = []
    for i, id_j in enumerate(ids_jugadors):
        joins += f"""
            JOIN Components_cinc cc{i} ON cc{i}.id_cinc = c.id_cinc AND cc{i}.id_jugador = ?
        """
        params.append(id_j)

    # 1. Minuts i plus-minus del grup (quan tots estan a pista)
    query_grup = f"""
        SELECT SUM(e.minuts_jugats),
               SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici)),
               GROUP_CONCAT(DISTINCT e.jornada)
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        {joins}
    """
    cursor.execute(query_grup, params)
    fila = cursor.fetchone()
    minuts_grup = fila[0] or 0
    plus_minus_grup = fila[1] or 0
    jornades_grup = fila[2]

    if not jornades_grup:
        return [(tuple(ids_jugadors), 0, 0, None)]  # Cap minut jugat plegats

    # 2. Minuts i plus-minus de la resta (quan almenys un no hi és), però només a les mateixes jornades
    jornades_placeholder = ",".join("?" for _ in jornades_grup.split(","))
    query_restants = f"""
        SELECT SUM(e.minuts_jugats),
               SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici))
        FROM Entrada e
        WHERE e.jornada IN ({jornades_placeholder})
        AND e.id_cinc NOT IN (
            SELECT c.id_cinc
            FROM Cinc c
            {joins}
        )
    """
    cursor.execute(query_restants, jornades_grup.split(",") + params)
    fila_restants = cursor.fetchone()
    minuts_restants = fila_restants[0] or 0
    plus_minus_restants = fila_restants[1] or 0

    # 3. Ajustat
    if minuts_grup == 0:
        ajustat = None
    else:
        total_minuts = minuts_grup + minuts_restants
        total_diferencia = plus_minus_grup + plus_minus_restants
        mitjana_equip = total_diferencia / total_minuts if total_minuts else 0
        mitjana_grup = plus_minus_grup / minuts_grup
        ajustat = mitjana_grup - mitjana_equip

    conn.close()

    return [(tuple(ids_jugadors), minuts_grup, plus_minus_grup, round(ajustat, 2) if ajustat is not None else None)]

def atac_per_minut_grup(nom_base_dades, ids_jugadors):
    if not ids_jugadors:
        return None, 0, 0  # no hi ha jugadors

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    joins = ""
    params = []
    for i, id_j in enumerate(ids_jugadors):
        joins += f"""
        JOIN Components_cinc cc{i} ON cc{i}.id_cinc = c.id_cinc AND cc{i}.id_jugador = ?
        """
        params.append(id_j)

    query = f"""
    SELECT 
        SUM(e.punts_favor_final - e.punts_favor_inici) AS total_punts_anotats,
        SUM(e.minuts_jugats) AS total_minuts_jugats
    FROM Cinc c
    {joins}
    JOIN Entrada e ON c.id_cinc = e.id_cinc
    """

    cursor.execute(query, params)
    fila = cursor.fetchone()
    conn.close()

    if fila is None or fila[1] is None or fila[1] == 0:
        return None, 0, 0

    punts_per_minut = round(fila[0] / fila[1], 2)

    return punts_per_minut, fila[0], fila[1]


def defensa_per_minut_grup(nom_base_dades, ids_jugadors):
    if not ids_jugadors:
        return None, 0, 0  # no hi ha jugadors

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    joins = ""
    params = []
    for i, id_j in enumerate(ids_jugadors):
        joins += f"""
        JOIN Components_cinc cc{i} ON cc{i}.id_cinc = c.id_cinc AND cc{i}.id_jugador = ?
        """
        params.append(id_j)

    query = f"""
    SELECT 
        SUM(e.punts_contra_final - e.punts_contra_inici) AS total_punts_rebuts,
        SUM(e.minuts_jugats) AS total_minuts_jugats
    FROM Cinc c
    {joins}
    JOIN Entrada e ON c.id_cinc = e.id_cinc
    """

    cursor.execute(query, params)
    fila = cursor.fetchone()
    conn.close()

    if fila is None or fila[1] is None or fila[1] == 0:
        return None, 0, 0

    punts_per_minut = round(fila[0] / fila[1], 2)

    return punts_per_minut, fila[0], fila[1]

def atac_on_off_grup(nom_base_dades, grup_jugadors_ids):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # Obtenir les jornades en què algun jugador del grup ha jugat
    query_jornades = """
        SELECT DISTINCT e.jornada
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador IN ({})
    """.format(','.join(['?'] * len(grup_jugadors_ids)))
    cursor.execute(query_jornades, grup_jugadors_ids)
    jornades = [row[0] for row in cursor.fetchall()]

    if not jornades:
        conn.close()
        return []

    # Query Atac ON (quan el grup està en pista)
    query_on = """
        SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador IN ({})
    """.format(','.join(['?'] * len(grup_jugadors_ids)))

    cursor.execute(query_on, grup_jugadors_ids)
    punts_on = cursor.fetchone()[0] or 0

    # Query Atac OFF (quan el grup no està en pista però és jornada que han jugat)
    query_off = """
        SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
        FROM Entrada e
        JOIN (
            SELECT DISTINCT e2.jornada
            FROM Entrada e2
            JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
            JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
            WHERE cc2.id_jugador IN ({})
        ) jugades ON e.jornada = jugades.jornada
        WHERE e.id_cinc NOT IN (
            SELECT c.id_cinc
            FROM Cinc c
            JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
            WHERE cc.id_jugador IN ({})
        )
        AND e.jornada IN ({})
    """.format(
        ','.join(['?'] * len(grup_jugadors_ids)),
        ','.join(['?'] * len(grup_jugadors_ids)),
        ','.join(['?'] * len(jornades))
    )

    # Paràmetres: ids jugadors per la subconsulta + ids jugadors per l'altra subconsulta + jornades
    params = list(grup_jugadors_ids) + list(grup_jugadors_ids) + jornades
    cursor.execute(query_off, params)
    punts_off = cursor.fetchone()[0] or 0

    diferència = punts_on - punts_off

    conn.close()
    return [punts_on, punts_off, diferència]



def defensa_on_off_grup(nom_base_dades, grup_jugadors_ids):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    query_jornades = """
        SELECT DISTINCT e.jornada
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador IN ({})
    """.format(','.join(['?'] * len(grup_jugadors_ids)))
    cursor.execute(query_jornades, grup_jugadors_ids)
    jornades = [row[0] for row in cursor.fetchall()]

    if not jornades:
        conn.close()
        return []

    query_on = """
        SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
        FROM Entrada e
        JOIN Cinc c ON e.id_cinc = c.id_cinc
        JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
        WHERE cc.id_jugador IN ({})
    """.format(','.join(['?'] * len(grup_jugadors_ids)))

    cursor.execute(query_on, grup_jugadors_ids)
    punts_on = cursor.fetchone()[0] or 0

    query_off = """
        SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
        FROM Entrada e
        JOIN (
            SELECT DISTINCT e2.jornada
            FROM Entrada e2
            JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
            JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
            WHERE cc2.id_jugador IN ({})
        ) jugades ON e.jornada = jugades.jornada
        WHERE e.id_cinc NOT IN (
            SELECT c.id_cinc
            FROM Cinc c
            JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
            WHERE cc.id_jugador IN ({})
        )
        AND e.jornada IN ({})
    """.format(
        ','.join(['?'] * len(grup_jugadors_ids)),
        ','.join(['?'] * len(grup_jugadors_ids)),
        ','.join(['?'] * len(jornades))
    )

    params = list(grup_jugadors_ids) + list(grup_jugadors_ids) + jornades
    cursor.execute(query_off, params)
    punts_off = cursor.fetchone()[0] or 0

    diferència = punts_off - punts_on

    conn.close()
    return [punts_on, punts_off, diferència]



def crea_taula_general_parelles(nom_base_dades):
    
    
    comb_2, comb_3 = llista_ids_jugadors(nom_base_dades)
    
    taula_general = {} 
    
    for jugadors in comb_2:
    
        
        #MINUTS
        
        minuts = minuts_jugats_conjunts(nom_base_dades,jugadors)
        if minuts[1] < 70:  
            
            continue  
        
        #print(minuts)
          
        taula_general[jugadors] = {}
        #taula_general[jugadors]["cognoms"] = jugador[1]
        taula_general[jugadors]["minuts_jugats"] = minuts[1]
        
        
        
        on_off = calcula_on_off_grup(nom_base_dades, jugadors)
       
        #ON_OFF
       
        taula_general[jugadors]["on/off"] = on_off[0][3]
            
        
        #PLUS_MINUS_AJUSTAT
        ajustat = plus_minus_ajustat_grup(nom_base_dades,jugadors)
        
        
            
        taula_general[jugadors]["mes_menys"] = ajustat[0][2]
        taula_general[jugadors]["plus_minus_ajustat"] = ajustat[0][3]
        
        
        #ATAC PER MINUT
        atac_minut = atac_per_minut_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["punts_anotats_pista"] = atac_minut[1]
        taula_general[jugadors]["punts_anotats_per_minut"] = atac_minut[0]
        
        #DEFENSA_PER_MINUT
        defensa_minut = defensa_per_minut_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["punts_rebuts_pista"] = defensa_minut[1]
        taula_general[jugadors]["punts_rebuts_per_minut"] = defensa_minut[0]
        net = atac_minut[0] - defensa_minut[0]
        taula_general[jugadors]["net rating"] = round(net,2)
        
           
        #ATAC ON/OFF
        atac_on = atac_on_off_grup(nom_base_dades,jugadors)
        #print(atac_on)
        taula_general[jugadors]["on/off atac"] = atac_on[2]
            
        #DEFENSA ON/OFF
        defensa_on = defensa_on_off_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["on/off defensa"] = defensa_on[2]        
        
        
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
        
        
def crea_taula_general_trios(nom_base_dades):
    
    
    comb_2, comb_3 = llista_ids_jugadors(nom_base_dades)
    
    taula_general = {}  
    
    for jugadors in comb_3:
    
        
        
        #MINUTS
        
        minuts = minuts_jugats_conjunts(nom_base_dades,jugadors)
        if minuts[1] < 55:  
            
            continue  
        
        #print(minuts)
          
        taula_general[jugadors] = {}
        #taula_general[jugadors]["cognoms"] = jugador[1]
        taula_general[jugadors]["minuts_jugats"] = minuts[1]
        
        
        
        on_off = calcula_on_off_grup(nom_base_dades, jugadors)
       
        #ON_OFF
       
        taula_general[jugadors]["on/off"] = on_off[0][3]
            
        
        #PLUS_MINUS_AJUSTAT
        ajustat = plus_minus_ajustat_grup(nom_base_dades,jugadors)
        
        
            
        taula_general[jugadors]["mes_menys"] = ajustat[0][2]
        taula_general[jugadors]["plus_minus_ajustat"] = ajustat[0][3]
        
        
        #ATAC PER MINUT
        atac_minut = atac_per_minut_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["punts_anotats_pista"] = atac_minut[1]
        taula_general[jugadors]["punts_anotats_per_minut"] = atac_minut[0]
        
        #DEFENSA_PER_MINUT
        defensa_minut = defensa_per_minut_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["punts_rebuts_pista"] = defensa_minut[1]
        taula_general[jugadors]["punts_rebuts_per_minut"] = defensa_minut[0]
        
        net = atac_minut[0] - defensa_minut[0]
        taula_general[jugadors]["net rating"] = round(net,2)
        
           
        #ATAC ON/OFF
        atac_on = atac_on_off_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["on/off atac"] = atac_on[2]
            
        #DEFENSA ON/OFF
        defensa_on = defensa_on_off_grup(nom_base_dades,jugadors)
        
        taula_general[jugadors]["on/off defensa"] = defensa_on[2]        
        
        
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
    #llista_ids_jugadors(nom_base_dades)
    crea_taula_general_parelles(nom_base_dades)
    #crea_taula_general_trios(nom_base_dades)
    