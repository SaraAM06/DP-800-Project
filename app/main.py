import json
import pyodbc
import ollama
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse

app = FastAPI(title="API Gestión de Incidencias DP-800")

# Credenciales y conexión a SQL Server
SERVER = 'localhost'
DATABASE = 'IncidentesDB'
DRIVER = '{ODBC Driver 17 for SQL Server}'

# Parámetros de control para la IA y la búsqueda vectorial
UMBRAL_DISTANCIA = 0.35   # Límite de distancia para considerar un ticket válido
MARGEN_RELATIVO = 0.04    # Diferencia permitida respecto al mejor resultado
MAX_CANDIDATOS = 2        # Límite de tickets extraídos de la base de datos
MAX_CONTEXTO = 1          # Límite de tickets que leerá el modelo de lenguaje
MODELO_LLM = 'llama3.2'
MODELO_EMBED = 'nomic-embed-text'

# Estructura JSON estricta que deberá devolver la IA
ESQUEMA_RESPUESTA = {
    "type": "object",
    "properties": {
        "aplicable": {"type": "boolean"},
        "pasos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["aplicable", "pasos"],
}


def get_db_connection():
    # Establece y devuelve la conexión segura con la base de datos
    connection_string = (
        f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};'
        f'Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
    )
    return pyodbc.connect(connection_string)


def embed(texto: str, tipo: str) -> str:
    # Genera el vector matemático del texto usando el prefijo adecuado (búsqueda o guardado)
    r = ollama.embeddings(model=MODELO_EMBED, prompt=f"{tipo}: {texto}")
    return str(r['embedding'])


# Modelos de datos para validar las peticiones de los usuarios
class TicketCreate(BaseModel):
    titulo: str
    descripcion: str
    operador_id: Optional[int] = None


class BusquedaTicket(BaseModel):
    consulta: str


class SolicitudResolucion(BaseModel):
    descripcion_problema: str


# Rutas de diagnóstico para comprobar el estado de los servicios
@app.get("/test-db")
def test_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        conn.close()
        return {"status": "conexión exitosa", "sql_version": row[0]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/test-ia")
def test_ia():
    try:
        embed_response = ollama.embeddings(
            model=MODELO_EMBED,
            prompt='El ratón del ordenador no funciona.'
        )
        text_response = ollama.generate(
            model=MODELO_LLM,
            prompt='Responde únicamente con la frase: "Sistemas de IA operativos y listos para trabajar."',
            stream=False
        )
        return {
            "status": "IA conectada correctamente",
            "vector_generado_longitud": len(embed_response['embedding']),
            "respuesta_llama": text_response['response']
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Rutas funcionales de la aplicación
@app.post("/tickets")
def crear_ticket(ticket: TicketCreate):
    conn = None
    try:
        # Transformamos el texto del ticket en un vector antes de guardarlo
        vector_str = embed(f"{ticket.titulo}. {ticket.descripcion}", "search_document")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Incidencias (OperadorID, Titulo, Descripcion, Estado, VectorDescripcion)
            VALUES (?, ?, ?, 'Abierto', CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(768)))
        """, (ticket.operador_id, ticket.titulo, ticket.descripcion, vector_str))
        conn.commit()

        return {
            "status": "éxito",
            "mensaje": "Ticket guardado y vectorizado correctamente.",
            "titulo": ticket.titulo
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


@app.post("/buscar-similares")
def buscar_similares(busqueda: BusquedaTicket):
    # Devuelve las distancias reales para ayudar a calibrar el umbral matemático
    conn = None
    try:
        vector_consulta = embed(busqueda.consulta, "search_query")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 5
                Titulo, Descripcion, Estado,
                CASE WHEN Solucion IS NULL OR LEN(Solucion) = 0 THEN 0 ELSE 1 END AS TieneSolucion,
                VECTOR_DISTANCE('cosine', VectorDescripcion,
                    CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(768))) AS Distancia
            FROM Incidencias
            WHERE VectorDescripcion IS NOT NULL
            ORDER BY Distancia ASC
        """, (vector_consulta,))
        filas = cursor.fetchall()

        return {
            "status": "éxito",
            "consulta_original": busqueda.consulta,
            "umbral_actual": UMBRAL_DISTANCIA,
            "incidencias_similares": [
                {
                    "titulo": f.Titulo,
                    "descripcion": f.Descripcion,
                    "estado": f.Estado,
                    "tiene_solucion": bool(f.TieneSolucion),
                    "distancia": round(f.Distancia, 4),
                    "supera_umbral": f.Distancia <= UMBRAL_DISTANCIA,
                }
                for f in filas
            ],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


@app.post("/vectorizar-historico")
def vectorizar_historico():
    # Calcula y guarda los vectores de los tickets antiguos que aún no lo tengan
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IncidenciaID, Titulo, Descripcion FROM Incidencias WHERE VectorDescripcion IS NULL"
        )
        filas = cursor.fetchall()

        if not filas:
            return {"status": "éxito", "mensaje": "No hay registros pendientes de vectorizar."}

        actualizados = 0
        for fila in filas:
            vector_str = embed(f"{fila.Titulo}. {fila.Descripcion}", "search_document")
            cursor.execute("""
                UPDATE Incidencias
                SET VectorDescripcion = CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(768))
                WHERE IncidenciaID = ?
            """, (vector_str, fila.IncidenciaID))
            actualizados += 1

        conn.commit()
        return {
            "status": "éxito",
            "mensaje": "Migración completada.",
            "registros_actualizados": actualizados
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


@app.post("/sugerir-solucion")
def sugerir_solucion(solicitud: SolicitudResolucion):
    conn = None
    try:
        vector = embed(solicitud.descripcion_problema, "search_query")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP (?) IncidenciaID, Titulo, Descripcion, Solucion,
                   VECTOR_DISTANCE('cosine', VectorDescripcion,
                       CAST(CAST(? AS VARCHAR(MAX)) AS VECTOR(768))) AS Distancia
            FROM Incidencias
            WHERE VectorDescripcion IS NOT NULL
              AND Solucion IS NOT NULL AND LEN(Solucion) > 0
            ORDER BY Distancia ASC
        """, (MAX_CANDIDATOS, vector))
        filas = cursor.fetchall()

        # Filtramos matemáticamente los resultados más relevantes antes de usar la IA
        mejor = filas[0].Distancia if filas else None
        relevantes = [
            f for f in filas
            if f.Distancia <= UMBRAL_DISTANCIA and f.Distancia <= mejor + MARGEN_RELATIVO
        ][:MAX_CONTEXTO]

        # Si no hay tickets lo suficientemente parecidos, rechazamos responder
        if not relevantes:
            return {
                "status": "éxito",
                "nivel_confianza": "sin_coincidencias",
                "mensaje": ("No he encontrado incidencias resueltas parecidas a este "
                            "problema, así que no puedo darte una solución fiable. "
                            "Te recomiendo abrir un ticket para que lo revise un operador."),
                "mejor_distancia": round(mejor, 3) if mejor is not None else None,
            }

        # Si hay coincidencias, pedimos a la IA que extraiga los pasos basándose estrictamente en ellas
        contexto = "\n\n".join(
            f"[Ticket {i + 1}] Problema: {f.Descripcion}\nSolución aplicada: {f.Solucion}"
            for i, f in enumerate(relevantes)
        )
        r = ollama.chat(
            model=MODELO_LLM,
            format=ESQUEMA_RESPUESTA,
            options={"temperature": 0, "num_predict": 400},
            messages=[
                {"role": "system", "content":
                    "Eres un asistente de soporte. Respondes SOLO con información presente en los "
                    "tickets proporcionados. No añadas pasos, comandos ni herramientas que no "
                    "aparezcan en ellos. Copia los pasos de la solución sin reinterpretarlos. "
                    "Si ninguna solución encaja con el problema del usuario, "
                    "devuelve aplicable=false y pasos=[]. Responde en español."},
                {"role": "user", "content":
                    f"TICKETS HISTÓRICOS:\n{contexto}\n\n"
                    f"PROBLEMA DEL USUARIO:\n{solicitud.descripcion_problema}\n\n"
                    "Resume en 2-3 pasos la solución aplicable."},
            ],
        )
        try:
            salida = json.loads(r['message']['content'])
        except json.JSONDecodeError:
            # Por seguridad, si la IA no devuelve un JSON válido, descartamos la respuesta
            salida = {"aplicable": False, "pasos": []}
        
        salida["pasos"] = salida.get("pasos", [])[:4]

        if not salida.get("aplicable") or not salida.get("pasos"):
            return {
                "status": "éxito",
                "nivel_confianza": "sin_coincidencias",
                "mensaje": "He encontrado incidencias parecidas, pero ninguna solución encaja "
                           "claramente con tu caso. Te recomiendo abrir un ticket.",
            }

        return {
            "status": "éxito",
            "nivel_confianza": "basado_en_historico",
            "pasos": salida["pasos"],
            "tickets_usados": [
                {"id": f.IncidenciaID, "titulo": f.Titulo, "distancia": round(f.Distancia, 3)}
                for f in relevantes
            ],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


@app.get("/", response_class=FileResponse)
def interfaz_usuario():
    # Sirve el archivo HTML de la interfaz gráfica web
    return FileResponse("app/index.html")
