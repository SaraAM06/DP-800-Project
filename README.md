# Guía de Despliegue y Pruebas: Portal de Soporte IA (DP-800)

Esta guía detalla los pasos exactos para desplegar y auditar el sistema híbrido RAG en un entorno local nuevo.

## Prerrequisitos del Sistema
Para ejecutar este proyecto, el equipo evaluador debe contar con el siguiente software instalado:
* **SQL Server 2025** (y SQL Server Management Studio).
* **Ollama** (ejecutándose en segundo plano).
* **Python 3.8 o superior** (con la variable de entorno PATH configurada).

---

## Paso 1: Replicar la Base de Datos y Vectores
El proyecto incluye un script de exportación (esquema + datos) que contiene todos los registros históricos y sus *embeddings* matemáticos ya generados.

1. Abre SQL Server Management Studio (SSMS).
2. Carga el archivo `setup_database.sql` ubicado en la carpeta `database`.
3. Haz clic en **Ejecutar** (o pulsa F5).
4. *Resultado:* Se desplegará automáticamente la base de datos `IncidentesDB` con su integridad referencial, seguridad (DDM) y datos vectorizados, lista para producción.

---

## Paso 2: Configurar la Conexión al Servidor Local
Para que el *backend* pueda comunicarse con la nueva base de datos, es necesario indicarle el nombre de la instancia local.

1. Abre el archivo `app/main.py` con cualquier editor de código.
2. Localiza las credenciales de conexión en las primeras líneas del código:
   ```python
   SERVER = 'TU_SERVIDOR'  # <-- Modificar esta línea
   DATABASE = 'IncidentesDB'
   DRIVER = '{ODBC Driver 17 for SQL Server}'
   ```
3. Sustituye `'TU_SERVIDOR'` por el nombre exacto de la instancia local de SQL Server del equipo de evaluación (por ejemplo, `localhost`, `.\SQLEXPRESS`, o el nombre del equipo).
4. Guarda los cambios.

---

## Paso 3: Ejecución Automatizada 
El levantamiento del motor de IA y el servidor *backend* está completamente empaquetado en un script ejecutable.

1. Navega hasta la carpeta raíz del proyecto (`DP-800-Project-main`).
2. Haz doble clic sobre el archivo **`iniciar_proyecto.bat`**.
3. El script realizará automáticamente y en orden las siguientes acciones:
   * **IA Local:** Descargará e inicializará los modelos necesarios en Ollama (`nomic-embed-text` para vectores y `llama3.2` para la generación estructurada).
   * **Entorno:** Creará un entorno virtual de Python (`venv`) aislado y seguro.
   * **Dependencias:** Instalará las librerías necesarias leyendo el archivo `requirements.txt`.
   * **Despliegue:** Levantará el servidor Uvicorn y abrirá la aplicación web en el navegador por defecto.
