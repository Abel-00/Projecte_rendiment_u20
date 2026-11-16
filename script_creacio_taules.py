# -*- coding: utf-8 -*-
"""
Created on Thu Jul  3 17:39:08 2025

@author: abelg
"""

import sqlite3

conn = sqlite3.connect("CB_IMMA.db")
conn.execute("PRAGMA foreign_keys = ON")  # Molt important!
cursor = conn.cursor()

# CREACIÓ DE TAULES AMB CORRECCIONS

cursor.execute("""
CREATE TABLE IF NOT EXISTS Jugador (
    nom TEXT,
    cognom TEXT,
    dorsal INTEGER, 
    id_jugador TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Cinc (
    id_cinc TEXT PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Partit (
    rival TEXT,
    jornada INTEGER PRIMARY KEY,
    data TEXT, 
    hora TEXT, 
    local_visitant TEXT,  
    victoria TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Components_cinc (
    id_jugador TEXT,
    id_cinc TEXT,
    PRIMARY KEY (id_jugador, id_cinc),
    FOREIGN KEY (id_jugador) REFERENCES Jugador(id_jugador),
    FOREIGN KEY (id_cinc) REFERENCES Cinc(id_cinc)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS Entrada (
    id_cinc TEXT,
    minut_inici INTEGER,
    minut_final INTEGER,
    jornada INTEGER,
    punts_favor_inici INTEGER,
    punts_contra_inici INTEGER,
    punts_favor_final INTEGER,  
    punts_contra_final INTEGER,
    balanc INTEGER,
    minuts_jugats INTEGER,
    PRIMARY KEY (id_cinc, minut_inici, minut_final, jornada),
    FOREIGN KEY (id_cinc) REFERENCES Cinc(id_cinc),
    FOREIGN KEY (jornada) REFERENCES Partit(jornada)
)
""")

conn.commit()
conn.close()



