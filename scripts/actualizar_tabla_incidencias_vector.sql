USE IncidentesDB;
GO

ALTER TABLE Incidencias
ADD VectorDescripcion VECTOR(768);
GO

