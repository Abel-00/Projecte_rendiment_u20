# -*- coding: utf-8 -*-
"""
Created on Thu Jul  3 17:01:15 2025

@author: abelg
"""

import jugadors
import partits
import cincs_entrades


import sqlite3


def carregar_partit():
    
    """
    
    DADES INICIALS (JORNADA I LOCALITAT)
    
    
    """
    jornada_confirmada = False

    while not jornada_confirmada: #doble confirmació de la jornada per tal de comprovar que ho hem fet correctament
        jornada = input("Quina jornada vols carregar? ")
    
        if jornada.isdigit():
            jornada = int(jornada)
            print("Has posat la jornada", jornada, ",estàs segur? (S/N)")
            confirmacio = input().strip().upper()
    
            if confirmacio == "S":
                print("✅ Configurat jornada", jornada)
                jornada_confirmada = True
            else:
                print("🔁 Tornem-hi.")
        else:
            print("⚠️ Has d'introduir un número vàlid per la jornada.")
            
    
            
    localitat_confirmada = False

    while not localitat_confirmada: #doble verificacio de si vam jugar com a locals o com a visitants
        rol = input("L'equip juga com a local o visitant? (escriu 'local' o 'visitant'): ").strip().lower()
    
        if rol == "local" or rol == "visitant":
            print(f"Has dit que l'equip juga com a {rol}. Estàs segur? (S/N)")
            confirmacio = input().strip().upper()
    
            if confirmacio == "S":
                print(f"✅ Configurat com a {rol}.")
                localitat_confirmada = True
            else:
                print("🔁 Tornem-hi.")
        else:
            print("⚠️ Has d'escriure exactament 'local' o 'visitant'.")
    
    #creem la variable nom_document i la variable local (booleana)
    nom_document = "CB_Imma_J" + str(jornada) + ".json" 
    if rol == "local":
        local = True
    else:
        local = False
        
    """
    
    CRIDA A LES FUNCIONS PER A CARREGAR LES DADES
    
    """
        
    jugadors.insert_dades_jugadors(nom_document, local)
    print("Dades dels jugadors introduides correctament")
    partits.insert_data_partit(nom_document, jornada, local)
    print("Dades del partit introduides correctament")
    cincs_entrades.completar_taula_cinc(nom_document)
    print("Dades de la taula cinc introduïdes correctament")
    cincs_entrades.crea_entrada(nom_document, jornada, local)
    print("Dades de la taula entrada introduïdes correctament")
    cincs_entrades.components_cinc(nom_document)
    print("Dades de la taula cinc components introduïdes correctament")
    
    print("DADES DE LA JORNADA", jornada, "INTRODUÏDES CORRECTAMENT")
    
    
#carregar_partit()

def carregar_tots_partits():
    
    llista_localitat = {1: True, 2:False, 3:True, 4:False, 5:True, 6:False, 7:True, 8: True, 9:False, 
                        10:True, 11:False, 12:False, 13:True, 14:False, 15:True, 16: False,
                        17: True, 18:False, 19:False, 20: True, 21: False, 22:True}
    #True vol dir que hem jugat a casa i False a fora
    
    for jornada, local in llista_localitat.items():
        
        nom_document = "PARTITS/CB_Imma_J" + str(jornada) + ".json" 
        
        jugadors.insert_dades_jugadors(nom_document, local)
        #print("Dades dels jugadors introduides correctament")
        partits.insert_data_partit(nom_document, jornada, local)
        #print("Dades del partit introduides correctament")
        cincs_entrades.completar_taula_cinc(nom_document,local)
        #print("Dades de la taula cinc introduïdes correctament")
        cincs_entrades.crea_entrada(nom_document, jornada, local)
        #print("Dades de la taula entrada introduïdes correctament")
        cincs_entrades.components_cinc(nom_document, local)
        #print("Dades de la taula cinc components introduïdes correctament")
        print("DADES DE LA JORNADA", jornada, "INTRODUÏDES CORRECTAMENT")
        
        
carregar_tots_partits()        

def esborrar_dades(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = OFF")  # Desactiva restriccions temporals
    cursor = conn.cursor()

    # Llista de totes les taules (excloent les del sistema SQLite)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    taules = [fila[0] for fila in cursor.fetchall()]

    for taula in taules:
        cursor.execute(f"DELETE FROM {taula};")

    conn.commit()
    conn.close()
    
#esborrar_dades(nom_base_dades = "CB_IMMA.db")

def mostra_menu():
    
    print("Què vols fer?")
    print("1 - Introduir Partit")
    print("2 - Calcular estadístiques")
    print("5 - Sortir")
    

def main_principal():

    opcio = 0
    
    while opcio != 5:
    
        mostra_menu()
        opcio = int(input("Opció: "))
        
        
        if opcio == 1: #INTRODUIR LES DADES D'UN PARTIT EN CONCRET
        
            carregar_partit()
    
#main_principal()
       




        
    
