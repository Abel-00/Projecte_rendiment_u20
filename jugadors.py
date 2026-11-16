import orjson
import unicodedata
import sqlite3

def treure_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(c)
    )

def insert_dades_jugadors(nom_arxiu, local):
    with open(nom_arxiu, "rb") as f:
        data = orjson.loads(f.read())
        
    if local == True:
        jugadors = data["teams"][0]["players"]
    else:
        jugadors = data["teams"][1]["players"]
    
    conn = sqlite3.connect("CB_IMMA.db")
    cursor = conn.cursor()
    
    for jugador in jugadors:
        nom_complet = jugador["name"]
        nom_complet = treure_accents(nom_complet)
        
        parts = nom_complet.split(' ', 1)
        nom = parts[0]
        cognoms = parts[1] if len(parts) > 1 else ''
        dorsal = int(jugador["dorsal"])
        
 
        id_jugador = (nom + cognoms).replace(" ", "").upper()
        
        try:
            cursor.execute(
                "INSERT INTO Jugador (nom, cognom, dorsal, id_jugador) VALUES (?, ?, ?, ?)",
                (nom, cognoms, dorsal, id_jugador)
            )
            # print("Afegit:", nom_complet)
        except sqlite3.IntegrityError:
            # Si el jugador ja existeix (mateix nom/ID), no fem res.
            # Nota: Si vols que s'actualitzi el dorsal a la base de dades quan canvia,
            # hauries de fer un UPDATE aquí dins. De moment, ho deixem així.
            pass
    
    conn.commit()
    conn.close()

        
        
def crea_diccionari_in_out(nom_arxiu, diccionari_jugadors, local):
    
    with open(nom_arxiu, "rb") as f:
        data = orjson.loads(f.read())
    
    teams = data['teams']  # Això és una llista de dos equips
    
    # Mirem el primer equip
    if local == True:
        first_team = teams[0] 
    else:
        first_team = teams[1]
        
    players = first_team["players"]
    
    for jugador in players:
         
        nom = jugador["name"]
        nom = treure_accents(nom)
        
        # --- CANVI: Fem servir la mateixa lògica per l'ID que a insert_dades ---
        # Treiem espais i posem en majúscules per assegurar que coincideix
        id_jugador = nom.replace(" ", "").upper()
        
        dades = jugador["inOutsList"]
        diccionari_jugadors[id_jugador] = dades
        
    
#insert_dades_jugadors(1, 2)