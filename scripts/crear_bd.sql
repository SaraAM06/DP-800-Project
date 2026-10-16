DROP DATABASE IF EXISTS IncidentesDB;
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
