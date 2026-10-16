USE IncidentesDB;
GO

-- 1. Ocultar los correos por seguridad para que nadie los pueda robar
ALTER TABLE Operadores
ALTER COLUMN Email ADD MASKED WITH (FUNCTION = 'email()');
GO

-- 2. Crear una acción guardada para añadir incidencias nuevas
CREATE OR ALTER PROCEDURE sp_InsertarIncidencia
    @OperadorID INT,
    @Titulo NVARCHAR(200),
    @Descripcion NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Guarda los datos, le pone la fecha actual y el estado 'Abierta' por defecto
    INSERT INTO Incidencias (OperadorID, Titulo, Descripcion, Estado, FechaCreacion)
    VALUES (@OperadorID, @Titulo, @Descripcion, 'Abierta', GETDATE());
    
    -- Nos devuelve el número (ID) de la incidencia que se acaba de crear
    SELECT SCOPE_IDENTITY() AS NuevaIncidenciaID;
END;
GO

-- 3. Crear una acción guardada para cambiar el estado y poner la solución
CREATE OR ALTER PROCEDURE sp_ActualizarIncidencia
    @IncidenciaID INT,
    @Estado NVARCHAR(50),
    @Solucion NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Busca la incidencia por su ID y actualiza su estado y solución
    UPDATE Incidencias
    SET Estado = @Estado,
        Solucion = @Solucion
    WHERE IncidenciaID = @IncidenciaID;
END;
GO

-- 4. Crear una acción guardada para borrar incidencias en caso de error
CREATE OR ALTER PROCEDURE sp_EliminarIncidencia
    @IncidenciaID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Elimina la incidencia que coincida con el ID que le pasemos
    DELETE FROM Incidencias
    WHERE IncidenciaID = @IncidenciaID;
END;
GO