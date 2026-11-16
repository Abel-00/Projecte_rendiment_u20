# -*- coding: utf-8 -*-
"""
Created on Tue Jul  1 11:15:50 2025

@author: abelg
"""

import orjson


def crea_diccionari_in_out(diccionari_jugadors):
    with open("CB_Imma_J1.json", "rb") as f:
        data = orjson.loads(f.read())
    
    teams = data['teams']  # Això és una llista de dos equips
    
    # Mirem el primer equip
    first_team = teams[0]
    
    # Ara pots veure les claus que conté
    #print(first_team.keys())
    
    
    
    players = first_team["players"]
    
    
    for jugador in players:
         
        nom = jugador["name"]
        dades = jugador["inOutsList"]
       
        diccionari_jugadors[nom] = dades
        
def mostra_cincs():
    
    diccionari_jugadors = {}
    crea_diccionari_in_out(diccionari_jugadors)
    
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
            intervals.append((ultim_minut, minut_seguent, sorted(jugadors_pista)))
        ultim_minut = minut
    
        # Actualitzem els jugadors a pista
        if tipus == "IN_TYPE":
            jugadors_pista.add(nom)
        elif tipus == "OUT_TYPE":
            jugadors_pista.discard(nom)
    
    # Mostrem els intervals on hi havia 5 jugadors
    for start, end, jugadors in intervals:
        print(f"Del minut {start} al {end}, jugadors a pista:")
        for j in jugadors:
            print(f"  - {j}")
        print()
        
def resultat_minut_a_minut():
    with open("CB_Imma_J1.json", "rb") as f:
        data = orjson.loads(f.read())
        
    score_events = data["score"]
    
    # Ordenem per 'minuteAbsolute' perquè els events estiguin en ordre cronològic
    score_events.sort(key=lambda x: x['minuteAbsolute'])
    
    # Inicialitzem variables
    max_minute = 39
    local_score = 0
    visit_score = 0
    idx = 0
    n = len(score_events)
    
    minut_a_minut = []
    
    for minut in range(max_minute + 1):
        # Actualitzem marcador amb tots els events que passen en aquest minut
        while idx < n and score_events[idx]['minuteAbsolute'] == minut:
            local_score = score_events[idx]['local']
            visit_score = score_events[idx]['visit']
            idx += 1
        
        # Afegim l'entrada amb el marcador acumulat a aquest minut
        minut_a_minut.append({
            'minute': minut,
            'local': local_score,
            'visit': visit_score
        })
    
    return minut_a_minut
    

def mostra_jugadors_resultats():
    intervals = mostra_cincs()
    marcador = resultat_minut_a_minut()
    
    for start, end, jugadors in intervals:
        # Obtenim el resultat al principi i al final de l'interval
        marcador_inici = next((m for m in marcador if m['minute'] == start), None)
        marcador_final = next((m for m in marcador if m['minute'] == end), None)
        
        print(f"Del minut {start} al {end}, jugadors a pista:")
        for j in jugadors:
            print(f"  - {j}")
        
        if marcador_inici and marcador_final:
            print(f"  Resultat al començar: Local {marcador_inici['local']} - Visitant {marcador_inici['visit']}")
            print(f"  Resultat al acabar: Local {marcador_final['local']} - Visitant {marcador_final['visit']}")
        print()
    
        

mostra_cincs()
llista = resultat_minut_a_minut()    
print(llista)
    
    
    
    


