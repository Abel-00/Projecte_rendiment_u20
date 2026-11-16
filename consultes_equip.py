import sqlite3
from tabulate import tabulate


### FUNCIONS EQUIP ###



def minuts_jugats(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT j.nom, j.cognom,
               COUNT(DISTINCT e.jornada) AS partits_jugats,
               SUM(e.minuts_jugats) AS total_minuts,
               ROUND(SUM(e.minuts_jugats) * 1.0 / COUNT(DISTINCT e.jornada), 2) AS minuts_per_partit
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.nom, j.cognom
        ORDER BY j.nom, j.cognom
    """)

    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]

    #print(tabulate(resultats, headers=columnes, tablefmt="grid"))
    conn.close()
    return resultats


    
    
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

    # 2. Balanç quan NO està en pista ("OFF") però només en els partits que sí ha jugat
    cursor.execute("""
        SELECT j.id_jugador, j.nom, 
               IFNULL(SUM(e.balanc), 0) AS balanc_off
        FROM Jugador j
        JOIN (
            -- jornades on el jugador ha jugat
            SELECT DISTINCT j2.id_jugador, e2.jornada
            FROM Jugador j2
            JOIN Components_cinc cc2 ON j2.id_jugador = cc2.id_jugador
            JOIN Cinc c2 ON cc2.id_cinc = c2.id_cinc
            JOIN Entrada e2 ON c2.id_cinc = e2.id_cinc
        ) jugades ON j.id_jugador = jugades.id_jugador
        JOIN Entrada e ON e.jornada = jugades.jornada
        WHERE e.id_cinc NOT IN (
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
        if id_jugador in on_data:
            on_data[id_jugador]["off"] = balanc_off
        else:
            on_data[id_jugador] = {"nom": row[1], "on": 0, "off": balanc_off}

    # 3. Calcular On/Off
    resultats = []
    for jugador in on_data.values():
        bal_on = jugador.get("on", 0)
        bal_off = jugador.get("off", 0)
        on_off = bal_on - bal_off
        resultats.append([jugador["nom"], bal_on, bal_off, on_off])

    conn.close()
    return resultats

    
def plus_minus_ajustat(nom_base_dades):
    # Això et diu si, mentre ell és a pista, l’equip millora (valor positiu) o empitjora (valor negatiu) 
    # respecte al ritme normal del vostre equip en les jornades que ell juga.

    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades_final = []
    total_minuts = 0
    total_diferencia = 0
    jugador_dades = []

    for id_jugador, nom in jugadors:
        # Minuts i plus-minus només en jornades on el jugador ha jugat
        cursor.execute("""
            SELECT SUM(e.minuts_jugats),
                   SUM((e.punts_favor_final - e.punts_favor_inici) - (e.punts_contra_final - e.punts_contra_inici))
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ?
        """, (id_jugador,))
        fila = cursor.fetchone()
        minuts_jugador = fila[0] or 0
        plus_minus = fila[1] or 0

        total_minuts += minuts_jugador
        total_diferencia += plus_minus

        jugador_dades.append((nom, minuts_jugador, plus_minus))

    # Ara calculem l’ajustat per cada jugador, un cop tenim totals
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


def atac_per_minut_per_jugador(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT j.nom,
               SUM(e.punts_favor_final - e.punts_favor_inici) AS total_punts_anotats,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_favor_final - e.punts_favor_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.nom
        ORDER BY punts_per_minut DESC
    """)

    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]

    #print(tabulate(resultats, headers=columnes, tablefmt="grid"))
    conn.close()
    return resultats

def defensa_per_minut_per_jugador(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT j.nom,
               SUM(e.punts_contra_final - e.punts_contra_inici) AS total_punts_rebuts,
               SUM(e.minuts_jugats) AS total_minuts_jugats,
               ROUND(CAST(SUM(e.punts_contra_final - e.punts_contra_inici) AS FLOAT) / SUM(e.minuts_jugats), 2) AS punts_per_minut
        FROM Jugador j
        JOIN Components_cinc cc ON j.id_jugador = cc.id_jugador
        JOIN Cinc c ON cc.id_cinc = c.id_cinc
        JOIN Entrada e ON c.id_cinc = e.id_cinc
        GROUP BY j.nom
        ORDER BY punts_per_minut ASC
    """)

    resultats = cursor.fetchall()
    columnes = [desc[0] for desc in cursor.description]

    print(tabulate(resultats, headers=columnes, tablefmt="grid"))
    conn.close()
    return resultats
    
    
    

def atac_on_off(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades = []

    for id_jugador, nom in jugadors:
        # Atac ON: quan està en pista
        cursor.execute("""
            SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ?
        """, (id_jugador,))
        punts_on = cursor.fetchone()[0] or 0

        # Atac OFF: només en jornades en què ha jugat però no està en pista
        cursor.execute("""
            SELECT SUM(e.punts_favor_final - e.punts_favor_inici)
            FROM Entrada e
            JOIN (
                SELECT DISTINCT e2.jornada
                FROM Entrada e2
                JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
                JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
                WHERE cc2.id_jugador = ?
            ) jugades ON e.jornada = jugades.jornada
            WHERE e.id_cinc NOT IN (
                SELECT c.id_cinc
                FROM Cinc c
                JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
                WHERE cc.id_jugador = ?
            )
        """, (id_jugador, id_jugador))
        punts_off = cursor.fetchone()[0] or 0

        diferència = punts_on - punts_off
        dades.append([nom, punts_on, punts_off, diferència])

    conn.close()
    return dades


def defensa_on_off(nom_base_dades):
    conn = sqlite3.connect(nom_base_dades)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute("SELECT id_jugador, nom FROM Jugador")
    jugadors = cursor.fetchall()

    dades = []

    for id_jugador, nom in jugadors:
        # Defensa ON: quan està en pista
        cursor.execute("""
            SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
            FROM Entrada e
            JOIN Cinc c ON e.id_cinc = c.id_cinc
            JOIN Components_cinc cc ON cc.id_cinc = c.id_cinc
            WHERE cc.id_jugador = ?
        """, (id_jugador,))
        punts_on = cursor.fetchone()[0] or 0

        # Defensa OFF: només en jornades en què ha jugat però no està en pista
        cursor.execute("""
            SELECT SUM(e.punts_contra_final - e.punts_contra_inici)
            FROM Entrada e
            JOIN (
                SELECT DISTINCT e2.jornada
                FROM Entrada e2
                JOIN Cinc c2 ON e2.id_cinc = c2.id_cinc
                JOIN Components_cinc cc2 ON cc2.id_cinc = c2.id_cinc
                WHERE cc2.id_jugador = ?
            ) jugades ON e.jornada = jugades.jornada
            WHERE e.id_cinc NOT IN (
                SELECT c.id_cinc
                FROM Cinc c
                JOIN Components_cinc cc ON c.id_cinc = cc.id_cinc
                WHERE cc.id_jugador = ?
            )
        """, (id_jugador, id_jugador))
        punts_off = cursor.fetchone()[0] or 0

        diferència = punts_off - punts_on
        dades.append([nom, punts_on, punts_off, diferència])

    conn.close()
    return dades
    


def crea_taula_general(nom_base_dades):
    
    taula_general = {}  
    
    #MINUTS
    
    minuts = minuts_jugats(nom_base_dades)
    for jugador in minuts:
        
        
        taula_general[jugador[0]] = {}
        taula_general[jugador[0]]["cognoms"] = jugador[1]
        taula_general[jugador[0]]["partits jugats"] = jugador[2]
        taula_general[jugador[0]]["minuts totals"] = jugador[3]
        taula_general[jugador[0]]["minuts per partit"] = jugador[4]

    
    #ON_OFF
    
    on_off = calcula_on_off(nom_base_dades)
    for jugador in on_off:
        
        taula_general[jugador[0]]["balanç on"] = jugador[1]
        taula_general[jugador[0]]["balanç off"] = jugador[2]
        taula_general[jugador[0]]["on/off"] = jugador[3]
        
    
    #PLUS_MINUS_AJUSTAT
    ajustat = plus_minus_ajustat(nom_base_dades)
    for jugador in ajustat:
        
        taula_general[jugador[0]]["plus minus ajustat"] = round(jugador[3],2)
        
    #ATAC PER MINUT
    atac_minut = atac_per_minut_per_jugador(nom_base_dades)
    for jugador in atac_minut:
        taula_general[jugador[0]]["punts anotats pista"] = jugador[1]
        taula_general[jugador[0]]["punts anotats per minut"] = jugador[3]
    
    #DEFENSA_PER_MINUT
    defensa_minut = defensa_per_minut_per_jugador(nom_base_dades)
    for jugador in defensa_minut:
        taula_general[jugador[0]]["punts rebuts pista"] = jugador[1]
        taula_general[jugador[0]]["punts rebuts per minut"] = jugador[3]
        atac = taula_general[jugador[0]]["punts anotats per minut"] - jugador[3]
        taula_general[jugador[0]]["net rating"] = round(atac, 2) 
        
        
    #ATAC ON/OFF
    atac_on = atac_on_off(nom_base_dades)
    for jugador in atac_on:
        taula_general[jugador[0]]["on/off atac"] = jugador[3]
        
    #DEFENSA ON/OFF
    defensa_on = defensa_on_off(nom_base_dades)
    for jugador in defensa_on:
        taula_general[jugador[0]]["on/off defensa"] = jugador[3]        
    
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