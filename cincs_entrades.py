# -*- coding: utf-8 -*-
"""
Created on Thu Jul  3 12:24:49 2025

@author: abelg
"""

import jugadors
import sqlite3
import orjson

def resultat_minut_a_minut(nom_arxiu, local):
    """
    Retorna una llista amb els punts a favor i en contra minut a minut.
    
    Paràmetre:
        local (bool): True si el teu equip juga com a local, False si juga com a visitant.
    """

    with open(nom_arxiu, "rb") as f:
        data = orjson.loads(f.read())
        
    score_events = data["score"]
    
    # Ordenem els esdeveniments per ordre cronològic
    score_events.sort(key=lambda x: x['minuteAbsolute'])
    
    max_minute = 40
    marcador_local = 0
    marcador_visitant = 0
    idx = 0
    n = len(score_events)
    
    minut_a_minut = []
    
    for minut in range(max_minute + 1):
        while idx < n and score_events[idx]['minuteAbsolute'] == minut:
            marcador_local = score_events[idx]['local']
            marcador_visitant = score_events[idx]['visit']
            idx += 1
        
        if local:
            punts_a_favor = marcador_local
            punts_en_contra = marcador_visitant
        else:
            punts_a_favor = marcador_visitant
            punts_en_contra = marcador_local
        
        minut_a_minut.append({
            'minute': minut,
            'punts_a_favor': punts_a_favor,
            'punts_en_contra': punts_en_contra
        })
    
    return minut_a_minut



def crea_cincs(nom_arxiu, local):
    
    diccionari_jugadors = {}
    jugadors.crea_diccionari_in_out(nom_arxiu, diccionari_jugadors, local)
    
    events = [] #la llista events guarda tots els canvis, són tuples del tipus minut, IN/OUT i nom del jugador
    for nom, accions in diccionari_jugadors.items():
        for accio in accions:
            events.append((accio["minuteAbsolut"], accio["type"], nom)) 
    
    
    # Ordenem per minut (i perquè OUT_TYPE passi abans si coincideixen)
    events.sort(key=lambda x: (x[0], 0 if x[1] == "OUT_TYPE" else 1))  #ordenem els canvis per minut, abans els OUT que IN
    
    
    ultim_minut = 0
    jugadors_pista = set() #és els jugadors que hi ha en aquell moment a la pista
    intervals = [] #intervals és on guardem els canvis que anem fent, és una llista
    
    
    
    for i, (minut, tipus, nom) in enumerate(events):
        # Abans d’aplicar el canvi, mirem si hi ha 5 jugadors i ho guardem
        if len(jugadors_pista) == 5:
            minut_seguent = minut
            intervals.append((ultim_minut, minut_seguent, sorted(jugadors_pista), ''.join(sorted(jugadors_pista))))
        ultim_minut = minut
    
        # Actualitzem els jugadors a pista
        if tipus == "IN_TYPE":
            jugadors_pista.add(nom)
        elif tipus == "OUT_TYPE":
            jugadors_pista.discard(nom)
    
    #print(intervals)
    return intervals




def completar_taula_cinc(nom_arxiu, local):
    intervals = crea_cincs(nom_arxiu,local)
    
    conn = sqlite3.connect("CB_IMMA.db")
    cursor = conn.cursor()
    
    for codi_info in intervals:
        codi = codi_info[3]  # segons el teu codi, el codi està a la posició 2
        #print("Codi Cinc:", codi)
        
        try:
            cursor.execute("INSERT INTO Cinc (id_cinc) VALUES (?)", (codi,))
            #print(f"Cinc afegit: {codi}")
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()



def crea_entrada(nom_arxiu, jornada, local=True): 
    
    intervals = crea_cincs(nom_arxiu, local)  # [(start, end, components, codi_cinc), ...]
    marcador = resultat_minut_a_minut(nom_arxiu, local)  # llista de dicts amb 'minute', 'punts_a_favor', 'punts_en_contra'
    
    conn = sqlite3.connect("CB_IMMA.db")
    cursor = conn.cursor()
    
    for start, end, components, codi in intervals:
        marcador_inici = next((m for m in marcador if m['minute'] == start), None)
        marcador_final = next((m for m in marcador if m['minute'] == end), None)
        
        if marcador_inici is None or marcador_final is None:
            #print(f"No hi ha marcador per minuts {start} o {end}, saltant...")
            continue
        
        punts_favor_inici = int(marcador_inici['punts_a_favor'])
        punts_contra_inici = int(marcador_inici['punts_en_contra'])
        punts_favor_final = int(marcador_final['punts_a_favor'])
        punts_contra_final = int(marcador_final['punts_en_contra'])
        
        punts_anotats = punts_favor_final - punts_favor_inici
        punts_encaixats = punts_contra_final - punts_contra_inici
        balanc = int(punts_anotats - punts_encaixats)
        minuts_jugats = int(end - start)
        jornada_int = int(jornada)  # Assegura que jornada també és int
        
        try:
            cursor.execute("""
                INSERT INTO Entrada (
                    id_cinc, minut_inici, minut_final, jornada, 
                    punts_favor_inici, punts_contra_inici, 
                    punts_favor_final, punts_contra_final, 
                    balanc, minuts_jugats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                codi, start, end, jornada_int, 
                punts_favor_inici, punts_contra_inici, 
                punts_favor_final, punts_contra_final, 
                balanc, minuts_jugats
            ))
            #print(f"Entrada afegida: cinc {codi}, jornada {jornada_int}, minuts {start}-{end}")
        except sqlite3.IntegrityError:
            #print(f"Entrada ja existent: cinc {codi}, jornada {jornada_int}, minuts {start}-{end}")
            pass
    
    conn.commit()
    conn.close()


def components_cinc(nom_arxiu, local):
    intervals = crea_cincs(nom_arxiu, local)
    
    conn = sqlite3.connect("CB_IMMA.db")
    cursor = conn.cursor()
    
    for interval in intervals:
        llista_jugadors = interval[2]  # llista d'id_jugador (strings)
        codi = interval[3]             # id_cinc (string)
        
        for jugador in llista_jugadors:
            try:
                cursor.execute("""
                    INSERT INTO Components_cinc (id_jugador, id_cinc) VALUES (?, ?)
                """, (jugador, codi))
                #print(f"Afegit jugador {jugador} al cinc {codi}")
            except sqlite3.IntegrityError:
                # ja existeix aquesta relació, saltar
                pass
    
    conn.commit()
    conn.close()


#def crea_entrada(nom_arxiu, local):
#crea_cincs()
#crea_entrada_SQL(1)  
#components_cinc("CB_Imma_J1.json")
    