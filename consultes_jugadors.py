# -*- coding: utf-8 -*-
"""
Created on Tue Jul  8 16:28:31 2025

@author: abelg
"""
import sqlite3
from tabulate import tabulate

### FUNCIONS JUGADORS #####

def minuts_jugats_jugador(nom_base_dades, nom_jugador):

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.nom, SUM(e.minuts_jugats) AS MINUTS_JUGATS
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        WHERE j.nom = ?
    """, (nom_jugador,))  # Passar paràmetre com a tupla de 1 element
    
    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
    
    print(tabulate(resultats, headers=columnes, tablefmt="grid"))

    conn.close()

    
def mes_menys_jugador(nom_base_dades, nom_jugador):
    
    """
    #aqui hi pot haver algun petit error pq a l'hora del canvi nomès posa el minut i no segon 
    i jo agafo el resultat al principi del minut i això pot generar algun petit error
    
    """
    
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.nom, SUM(e.balanc) AS Balanç
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        WHERE j.nom = ?
    """, (nom_jugador,))  # Passar paràmetre com a tupla de 1 element
    
    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
    
    print(tabulate(resultats, headers=columnes, tablefmt="grid"))

    conn.close()
    
def mes_menys_sense_jugador(nom_base_dades, nom_jugador):

