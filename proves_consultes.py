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
    

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    consulta = """
    SELECT SUM(e.balanc) AS Balanc_Sense_Jugador
    FROM Entrada e
    WHERE e.id_cinc NOT IN (
        SELECT c.id_cinc
        FROM Cinc c
        JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
        JOIN Jugador j ON j.id_jugador = cc.id_jugador
        WHERE j.nom = ?
    )
    """
    
    cursor.execute(consulta, (nom_jugador,))
    
    resultat = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
    
    print(tabulate(resultat, headers=columnes, tablefmt="grid"))
    
    conn.close()


### FUNCIONS EQUIP ###

def minuts_jugats_equip(nom_base_dades):

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT j.nom, j.cognom, SUM(e.minuts_jugats) AS MINUTS_JUGATS
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.nom, j.cognom
     
    """)  # Passar paràmetre com a tupla de 1 element
    
    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
    
    print(tabulate(resultats, headers=columnes, tablefmt="grid"))

    conn.close()
    
def mes_menys_equip(nom_base_dades):
    
        
    """
    #aqui hi pot haver algun petit error pq a l'hora del canvi nomès posa el minut i no segon 
    i jo agafo el resultat al principi del minut i això pot generar algun petit error
        
    """
        
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
        
    cursor.execute("""
        SELECT j.nom,j.cognom, SUM(e.balanc) AS Balanç
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.nom, j.cognom
    """)  # Passar paràmetre com a tupla de 1 element
        
    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
        
    print(tabulate(resultats, headers=columnes, tablefmt="grid"))

    conn.close()


def balanc_sense_cada_jugador(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    consulta = """
    SELECT j.nom AS Jugador, j.cognom, 
           IFNULL(SUM(e.balanc), 0) AS Balanc_Sense_Ell,
           IFNULL(SUM(e.minuts_jugats), 0) AS Minuts_Sense_Ell
    FROM Jugador j
    LEFT JOIN Entrada e ON e.id_cinc NOT IN (
        SELECT c.id_cinc
        FROM Cinc c
        JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
        WHERE cc.id_jugador = j.id_jugador
    )
    GROUP BY j.nom, j.cognom
    """

    cursor.execute(consulta)
    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]
    print(tabulate(resultats, headers=columnes, tablefmt="grid"))

    conn.close()
    
def calcula_on_off(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 1. Balanç quan està en pista ("ON")
    cursor.execute("""
        SELECT j.id_jugador, j.nom, 
               IFNULL(SUM(e.balanc), 0) AS balanc_on
        FROM Jugador j
        LEFT JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        LEFT JOIN Cinc c ON cc.id_cinc = c.id_cinc
        LEFT JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.id_jugador
    """)
    on_data = {row[0]: {"nom": row[1], "on": row[2]} for row in cursor.fetchall()} 
    #diccionari on la clau és el id del jugador i els valors són el nom i el rendiment a pista
    
    # 2. Balanç quan NO està en pista ("OFF")
    cursor.execute("""
        SELECT j.id_jugador, j.nom, 
               IFNULL(SUM(e.balanc), 0) AS balanc_off
        FROM Jugador j
        LEFT JOIN Entrada e ON e.id_cinc NOT IN (
            SELECT c.id_cinc
            FROM Cinc c
            JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
            WHERE cc.id_jugador = j.id_jugador
        )
        GROUP BY j.id_jugador
    """)
    for row in cursor.fetchall():
        id_jugador = row[0]
        balanc_off = row[2]
        on_data[id_jugador]["off"] = balanc_off #completem el diccionari ab el off
       
 
    # 3. Calcular On/Off
    resultats = []
    for jugador in on_data.values():
        bal_on = jugador.get("on", 0)
        bal_off = jugador.get("off", 0)
        on_off = bal_on - bal_off
        resultats.append([jugador["nom"], bal_on, bal_off, on_off])

    print(tabulate(resultats, headers=["Jugador", "Balanç ON", "Balanç OFF", "ON/OFF"], tablefmt="grid"))
    conn.close()

    


if __name__ == "__main__":
    
    nom_base_dades = "CB_IMMA.db"
    nom_jugador = "ERIC"
    #minuts_jugats_jugador(nom_base_dades, nom_jugador)
    #mes_menys_jugador(nom_base_dades, nom_jugador)
    #minuts_jugats_equip(nom_base_dades)
    #mes_menys_equip(nom_base_dades)
    #mes_menys_sense_jugador(nom_base_dades, nom_jugador)
    #balanc_sense_cada_jugador(nom_base_dades)
    calcula_on_off(nom_base_dades)