USE IncidentesDB;
GO

SELECT Titulo, Descripcion, Estado 
FROM Incidencias 
WHERE Estado = 'Abierto';


-- Creamos un índice para que SQL Server busque más rápido por la columna "Estado"
CREATE NONCLUSTERED INDEX IX_Incidencias_Estado 
ON Incidencias(Estado);
GO

-- Comprobacción
SELECT Titulo, Descripcion, Estado 
FROM Incidencias 
WHERE Estado = 'Abierto';