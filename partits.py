import orjson
from datetime import datetime
import sqlite3

def insert_data_partit(nom_arxiu, jornada, local):
    conn = sqlite3.connect("CB_IMMA.db")
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    with open(nom_arxiu, "rb") as f:
        data = orjson.loads(f.read())
    
    data_hora = data["time"]
    resultat = data["score"][-1]
    
    if local:
        guanyat = "Si" if resultat["local"] > resultat["visit"] else "No"
    else:
        guanyat = "Si" if resultat["visit"] > resultat["local"] else "No"
    
    dt = datetime.strptime(data_hora, "%b %d, %Y %I:%M:%S %p")
    data_partit = dt.strftime("%Y-%m-%d")
    hora_partit = dt.strftime("%H:%M:%S")
    
    rival = data["teams"][1]["name"] if local else data["teams"][0]["name"]
    localitat = "Local" if local else "Visitant"
    
    try:
        cursor.execute("""
            INSERT INTO Partit (rival, jornada, data, hora, local_visitant, victoria)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rival, jornada, data_partit, hora_partit, localitat, guanyat))
    except sqlite3.IntegrityError:
        print(f"La jornada {jornada} ja existeix a la base de dades. No s'ha afegit el partit.")
    else:
        conn.commit()
        #print("Partit inserit correctament:")
        #print("Jornada:", jornada)
        #print("Data_Partit:", data_partit)
        #print("Hora_Partit:", hora_partit)
        #print("Rival:", rival)
        #print("Local o Visitant:", localitat)
        #print("Guanyat:", guanyat)
    finally:
        conn.close()
