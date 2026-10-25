# Memoria del Proyecto DP-800: Aplicación de Gestión de Incidencias
**Autora:** Sara Antón Madero

## Fase 1: Configuración inicial y Diseño Relacional

### 1.1. Inicialización del Entorno y Control de Versiones
Se ha creado la estructura de directorios en local separando la lógica del proyecto en tres bloques principales: aplicación (`app`), base de datos (`database`) y documentación (`docs`). 

Para el control de versiones, se ha inicializado Git y se ha vinculado a un repositorio remoto en GitHub.

```bash
mkdir app database docs
git init
git remote add origin https://github.com/SaraAM06/DP-800-Project.git
git add .
git commit -m "Inicialización del proyecto y estructura de carpetas"
git push -u origin main
```
> *(Inserta aquí la captura de tu repositorio de GitHub)*
> *(Opcional: Inserta aquí la captura de la consola resolviendo el merge con Vim)*

### 1.2. Diseño de la Base de Datos Relacional
La base de datos se ha montado sobre SQL Server 2025 utilizando SQL Server Management Studio (SSMS). Se ha creado el esquema inicial `IncidentesDB` con dos tablas principales relacionadas por una clave foránea (`OperadorID`):

```sql
CREATE DATABASE IncidentesDB;
GO
USE IncidentesDB;
GO

CREATE TABLE Operadores (
    OperadorID INT IDENTITY(1,1) PRIMARY KEY,
    Nombre NVARCHAR(100) NOT NULL,
    Email NVARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE Incidencias (
    IncidenciaID INT IDENTITY(1,1) PRIMARY KEY,
    OperadorID INT FOREIGN KEY REFERENCES Operadores(OperadorID),
    Titulo NVARCHAR(200) NOT NULL,
    Descripcion NVARCHAR(MAX) NOT NULL,
    Estado NVARCHAR(50) DEFAULT 'Abierta',
    FechaCreacion DATETIME DEFAULT GETDATE(),
    Solucion NVARCHAR(MAX)
);
```
![tablas creadas](capturas/tablas_creadas.png)

### 1.3. Generación de Datos de Prueba (Mock Data)
Para preparar la futura búsqueda semántica, se ha utilizado Inteligencia Artificial generativa para poblar la base de datos con registros que simulan incidencias de soporte técnico reales, utilizando lenguaje natural variado. 

Primero se insertaron los registros en la tabla `Operadores` para respetar la integridad referencial y evitar conflictos de clave foránea, y posteriormente se insertaron las incidencias.

**Ejemplo de inserción generada:**
```sql
INSERT INTO Incidencias (OperadorID, Titulo, Descripcion, Estado) VALUES 
(3, 'Mi pantalla parpadea', 'Mi pantalla parpadea de forma constante cuando abro Excel o cualquier programa de Office, me marea bastante.', 'Abierto');
```
![incidencias insertadas](capturas/incidencias_insertadas.png)

### 1.4. Conexión entre la Aplicación y la Base de Datos
Para establecer la comunicación entre el backend y SQL Server, se instalaron las dependencias necesarias (`fastapi`, `uvicorn`, `pyodbc`). Se desarrolló un *endpoint* de prueba en el archivo `app/main.py`.

**Código de app/main.py:**
```python
import pyodbc
from fastapi import FastAPI

app = FastAPI(title="API Gestión de Incidencias DP-800")

SERVER = 'TU_SERVIDOR' # Configurado según la instancia local
DATABASE = 'IncidentesDB'
DRIVER = '{ODBC Driver 17 for SQL Server}' 

def get_db_connection():
    conn = pyodbc.connect(f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;')
    return conn

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
```

**Resolución de incidencias de acceso:**
Durante la primera prueba, la API devolvió el error `18456` debido a que el usuario de Windows no tenía permisos de acceso a la base de datos. Esto se solucionó desde SQL Server Management Studio, creando un "Nuevo inicio de sesión" para el usuario y otorgándole el rol de servidor `sysadmin`.

Tras aplicar este ajuste y ejecutar el servidor web de FastAPI (`python -m uvicorn main:app --reload`), la prueba de conexión devolvió un estado exitoso y la versión correcta de SQL Server.

![conexion fastAPI](capturas/conexion_fastapi.png)

## Fase 2: Seguridad, Optimización y Programación Básica

### 2.1. Seguridad: Enmascaramiento de Datos (DDM)
Para proteger la información sensible de los operadores frente a accesos no autorizados, se ha implementado *Dynamic Data Masking* (DDM) nativo de SQL Server en la tabla `Operadores`. Concretamente, se ha enmascarado la columna `Email` para que los usuarios sin privilegios vean un formato ofuscado.

```sql
ALTER TABLE Operadores
ALTER COLUMN Email ADD MASKED WITH (FUNCTION = 'email()');
```

### 2.2. Programación Básica y Pruebas de Ejecución (CRUD)
Por motivos de seguridad e integridad, las operaciones de modificación de datos no se delegan directamente a los modelos de IA. En su lugar, se han desarrollado Procedimientos Almacenados en T-SQL para centralizar y asegurar la inserción, actualización y eliminación de tickets.

Para garantizar el correcto funcionamiento de estos procedimientos antes de la integración con la IA, se han realizado las siguientes pruebas:

**1. Prueba de Inserción de Incidencia:**
Se simuló la creación manual de un ticket ejecutando el procedimiento `sp_InsertarIncidencia`, validando que el motor de base de datos lo registra correctamente y devuelve el ID generado.

![prueba insercion](capturas/insertar_incidencia.png)

**2. Prueba de Actualización y Resolución:**
Se simuló la resolución técnica del ticket anterior ejecutando `sp_ActualizarIncidencia`. Posteriormente, se verificó el registro comprobando que el estado y la solución se guardaron correctamente.

![comprobar resultado](capturas/comprobaccion_procedimientos.png)

### 2.3. Optimización: Índices y Planes de Ejecución
Se ha analizado el rendimiento del motor de base de datos ante consultas frecuentes para aplicar mejoras proactivas. Se tomó como caso de uso la búsqueda de tickets filtrados por estado.

**1. Análisis de consulta sin optimizar:**
Al ejecutar `SELECT Titulo, Descripcion, Estado FROM Incidencias WHERE Estado = 'Abierto';`, el Plan de Ejecución de SQL Server reveló un *Clustered Index Scan*. Esto indicaba que el motor estaba realizando un escaneo completo, leyendo secuencialmente toda la tabla.

![incidencia sin optimiza](capturas/plan_ejecucion.png)

**2. Implementación de índices:**
Para resolver el cuello de botella, se creó un índice no agrupado apuntando específicamente a la columna implicada en el filtrado.

```sql
CREATE NONCLUSTERED INDEX IX_Incidencias_Estado 
ON Incidencias(Estado);
```

**3. Verificación de la optimización:**
Al repetir exactamente la misma consulta, el Plan de Ejecución se actualizó a un *Index Seek*. Esto confirmó que el motor de SQL Server utilizó el nuevo índice para localizar directamente las filas requeridas, optimizando el consumo de recursos y los tiempos de respuesta.

![incidencia optimizada](capturas/plan_ejecucion_optimizado.png)

# Fase 3: Integración de Inteligencia Artificial Local (Ollama)

## Objetivo
Implementar un motor de inteligencia artificial 100% local utilizando Ollama para garantizar la privacidad de los datos. Los modelos requeridos son:
- **nomic-embed-text**: Para generar vectores (embeddings) a partir de los textos de los tickets.
- **llama3.2**: Para razonamiento lógico y traducción de lenguaje natural a consultas SQL.

## Problemas Encontrados y Soluciones

### 1. Bloqueo de Red en la Terminal (Firewall/DNS)
**Problema:** Al intentar descargar los modelos mediante el comando estándar (`ollama pull llama3.2`), la terminal se quedaba atascada indefinidamente en el estado `"pulling manifest"`. Esto fue causado por un bloqueo de red a nivel de sistema operativo o configuración de DNS que impedía a Ollama conectarse a sus servidores de registro.

**Solución (Instalación Offline):**
Se optó por descargar los pesos de los modelos manualmente desde el navegador (Hugging Face) en formato `.gguf` para saltar el bloqueo de la terminal.
1. Se descargaron los archivos `nomic-embed-text-v1.5.f16.gguf` y `Llama-3.2-3B-Instruct-Q4_K_M.gguf` en una carpeta local (`C:\Modelos`).
2. Se crearon archivos de instrucciones (`Modelfile.txt` y `Modelfile_llama.txt`) apuntando al archivo local usando el comando `FROM ./[nombre_del_archivo]`.
3. Se compilaron los modelos localmente usando el comando `ollama create`.

![Creación de modelo Nomic Embed Text](capturas/ollama_descarga_1.png)

![Creación de modelo Llama 3.2](capturas/ollama_descarga_2.png)

## Resultado Final
Se instaló la librería oficial de Python (`pip install ollama`).

![Instalación de la librería Ollama](capturas/ollama_descarga_3.png)

El endpoint `/test-ia` respondió exitosamente, confirmando que:
1. `nomic-embed-text` genera vectores correctamente (longitud de 768 dimensiones).
2. `llama3.2` recibe y responde prompts desde Python.

![Prueba de conexión exitosa](capturas/prueba_conexion_ia.png)

# Fase 4: Sistema RAG Estricto y Búsqueda Semántica Avanzada

## Objetivo

Implementar la arquitectura final de Recuperación Aumentada por Generación (RAG). El objetivo es utilizar las capacidades vectoriales de SQL Server 2025 para encontrar tickets históricos similares y emplear el modelo de lenguaje Llama 3.2 (ejecutado localmente vía Ollama) para redactar soluciones técnicas estructuradas, limitando estrictamente su conocimiento a la base de datos corporativa.

## 4.1. Evolución de la Arquitectura: Enfoque RAG Estricto (Pure RAG)

Durante las pruebas de integración, se determinó que permitir al LLM responder con "conocimiento general" cuando no había coincidencias en la base de datos introducía un riesgo de respuestas no verificadas corporativamente. Para garantizar la máxima fiabilidad en un entorno de producción, se evolucionó hacia un **RAG Estricto**:

1. **Filtrado Matemático Riguroso (Thresholding):** Se establecieron variables de control estricto en el backend (`UMBRAL_DISTANCIA = 0.45` y `MARGEN_RELATIVO = 0.04`). SQL Server descarta automáticamente cualquier ticket cuya distancia del coseno supere este límite.
2. **Eliminación del Conocimiento General:** Si la base de datos no devuelve resultados por debajo del umbral, el sistema interrumpe el flujo y deniega la respuesta, instando al usuario a abrir un nuevo ticket. El LLM ya no intenta adivinar soluciones.
3. **Extracción de Múltiples Contextos:** El sistema recupera los `MAX_CANDIDATOS` más cercanos y agrupa varios casos relevantes para enriquecer la solución de forma segura.
4. **Forzado de Esquema JSON (Structured Output):** Llama 3.2 devuelve la solución bajo un esquema JSON rígido, garantizando que el *frontend* reciba siempre una lista procesable (`pasos`) y un booleano de validez (`aplicable`).

## 4.2. Implementación en FastAPI (Backend)

El endpoint principal `/sugerir-solucion` centraliza esta lógica. Convierte la petición del usuario a vector mediante `nomic-embed-text`, y consulta SQL Server usando la función nativa `VECTOR_DISTANCE`. 

![sugerir solucion input](capturas/post_sugerir_solucion.png)
![sugerir solucion output](capturas/post_sugerir_solucion_respuesta.png)

## 4.3. Interfaz de Usuario (Frontend)

Se limpió la interfaz eliminando opciones ambiguas para el usuario (como el checkbox de consejo general). El diseño es minimalista, responsive y manejado de forma asíncrona (Fetch API) desde un archivo `index.html`.

La interfaz ahora maneja dos estados visuales claros:
* **Éxito (Violeta):** Muestra los pasos técnicos exactos y lista la fuente corporativa utilizada.
* **Denegación / Sin coincidencias (Gris):** Informa de que no hay un historial fiable y bloquea la generación de la IA.

## 4.4. Pruebas de Validación

Se realizaron diversas pruebas funcionales para comprobar el acierto semántico y el blindaje del sistema ante consultas no pertinentes:

**1. Búsqueda con sinónimos (Hardware y Ofimática):**
El modelo asocia "rayas y titila" con problemas de monitor, devolviendo una solución estructurada.
![Prueba de coincidencia de monitor](capturas/prueba_1.png)

**2. Comprensión semántica de almacenamiento:**
El sistema enlaza "disco C casi sin espacio" con el histórico de "Disco duro lleno" correctamente.
![Prueba de coincidencia de disco duro](capturas/prueba_2.png)

**3. Software específico (Microsoft Teams):**
El motor reconoce caídas en videollamadas asociándolas a problemas de caché y aceleración de hardware.
![Prueba de coincidencia de Teams](capturas/prueba_3.png)

**4. Blindaje contra consultas fuera de dominio (Out-of-Domain):**
Al introducir texto no relacionado con soporte técnico ("hola, ¿Cómo te llamas?"), el umbral matemático descarta todos los tickets y el sistema se niega a inventar una respuesta, sugiriendo la apertura de un ticket tradicional.
![Prueba de denegación](capturas/prueba_4.png)

## Conclusión de la Fase 4

Se ha logrado construir un portal de soporte autónomo, seguro y libre de alucinaciones. Al restringir el sistema a un RAG Estricto con salida JSON forzada, se cumplen los requisitos técnicos de nivel empresarial para la certificación DP-800, demostrando un dominio absoluto sobre bases de datos relacionales con capacidades vectoriales y modelos de IA locales.
