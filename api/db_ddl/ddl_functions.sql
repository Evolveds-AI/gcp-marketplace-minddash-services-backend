
-- =======================================================
-- Tabla de Organizaciones
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_organization(
    p_name VARCHAR(50),
    p_company_name VARCHAR(100),
    p_description VARCHAR(200),
    p_country VARCHAR(25),
    INOUT io_organization_id UUID DEFAULT NULL -- Aquí se devolverá el ID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Generar el nuevo UUID y asignarlo al parámetro INOUT
    io_organization_id := uuid_generate_v4();
    
    -- 2. Insertar los datos, usando el ID del parámetro
    INSERT INTO organizations (
        id, name, company_name, description, country, updated_at
    )
    VALUES (
        io_organization_id, -- Usamos el ID asignado
        p_name,
        p_company_name,
        p_description,
        p_country,
        CURRENT_TIMESTAMP
    );
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_organization(
    p_organization_id UUID, -- Requiere el ID para saber qué actualizar
    p_name VARCHAR(50),
    p_company_name VARCHAR(100),
    p_description VARCHAR(200),
    p_country VARCHAR(25)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación: Asegurar que el ID existe antes de actualizar
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. La organización con ID % no existe.', p_organization_id;
    END IF;
    
    -- 2. ACTUALIZAR la fila
    UPDATE organizations
    SET
        name = p_name,
        company_name = p_company_name,
        description = p_description,
        country = p_country,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_organization_id;
        
    RAISE NOTICE 'Organización con ID % actualizada exitosamente.', p_organization_id;

END;
$$;


CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_organization(
    p_organization_id UUID -- Requiere el ID para saber qué eliminar
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación: Asegurar que el ID existe antes de proceder
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La organización con ID % no existe.', p_organization_id;
    END IF;
    
    -- 2. Manejo de Clave Foránea: Eliminar las referencias dependientes primero.
    --    Esto evita el error "violates foreign key constraint".
    DELETE FROM "access_user_organization"
    WHERE "organization_id" = p_organization_id;

    -- 3. ELIMINAR la organización principal
    DELETE FROM "organizations"
    WHERE id = p_organization_id;
    
    RAISE NOTICE 'Organización con ID % y sus referencias de acceso eliminadas exitosamente.', p_organization_id;

END;
$$;

-- =======================================================
-- Tabla de Proyectoss
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_project(
    p_organization_id UUID,
    p_name VARCHAR(50),
    p_label VARCHAR(50),
    p_label_color VARCHAR(20),
    p_description VARCHAR(200),
    INOUT io_project_id UUID DEFAULT NULL -- Devuelve el nuevo ID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación: Verificar que la organización exista (llave foránea)
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La organización con ID % no existe. No se puede crear el proyecto.', p_organization_id;
    END IF;
    
    -- 2. Generar el nuevo UUID
    io_project_id := uuid_generate_v4();

    -- 3. INSERTAR los datos
    INSERT INTO projects (
        id, organization_id, name, label, label_color, description, updated_at
    )
    VALUES (
        io_project_id,
        p_organization_id,
        p_name,
        p_label,
        p_label_color,
        p_description,
        CURRENT_TIMESTAMP
    );
    
    RAISE NOTICE 'Proyecto "%" (ID: %) creado exitosamente.', p_name, io_project_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_project(
    p_project_id UUID,                -- ID del proyecto a actualizar
    p_organization_id UUID,           -- Nueva Organization ID (para reasignación, si aplica)
    p_name VARCHAR(50),
    p_label VARCHAR(50),
    p_label_color VARCHAR(20),
    p_description VARCHAR(200)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del proyecto
    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. El proyecto con ID % no existe.', p_project_id;
    END IF;

    -- 2. Validación de existencia de la organización (llave foránea)
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La nueva organización con ID % no existe. No se puede reasignar el proyecto.', p_organization_id;
    END IF;
    
    -- 3. ACTUALIZAR la fila
    UPDATE projects
    SET
        organization_id = p_organization_id,
        name = p_name,
        label = p_label,
        label_color = p_label_color,
        description = p_description,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_project_id;
        
    RAISE NOTICE 'Proyecto con ID % actualizado exitosamente.', p_project_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_project(
    p_project_id UUID -- ID del proyecto a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_project_name VARCHAR(50);
BEGIN
    -- 1. Validar la existencia del proyecto y obtener su nombre para el mensaje
    SELECT "name" INTO v_project_name FROM projects WHERE id = p_project_id;

    IF v_project_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El proyecto con ID % no existe.', p_project_id;
    END IF;

    -- 2. Eliminar la fila
    -- Nota: 'CASCADE' en el DROP TABLE inicial indica que las llaves foráneas dependientes
    -- deberían manejar esto. Sin embargo, si existen registros dependientes (ej: tareas)
    -- y no tienen ON DELETE CASCADE, esta operación fallará, lo cual es correcto para 
    -- mantener la integridad. Si fuera necesario, se podrían eliminar registros dependientes aquí.
    DELETE FROM projects
    WHERE id = p_project_id;
    
    -- 3. Mensaje de éxito
    RAISE NOTICE 'Proyecto "%" (ID: %) eliminado exitosamente.', v_project_name, p_project_id;

END;
$$;

-- =======================================================
-- Tabla de Productos
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_product(
    -- 1. Parámetros OBLIGATORIOS
    p_project_id UUID,
    p_name VARCHAR(200),
    
    -- 2. Parámetros OPCIONALES
    p_description VARCHAR(200) DEFAULT NULL, 
    p_language VARCHAR(50) DEFAULT NULL,
    p_tipo VARCHAR(20) DEFAULT 'chatbot',
    p_config JSONB DEFAULT '{}'::jsonb,
    p_welcome_message VARCHAR(100) DEFAULT NULL,
    p_label VARCHAR(50) DEFAULT NULL,
    p_label_color VARCHAR(20) DEFAULT NULL,
    p_max_users INTEGER DEFAULT 100,
    p_is_active_rag BOOLEAN DEFAULT FALSE,
    p_is_active_alerts BOOLEAN DEFAULT FALSE,
    p_is_active_insight BOOLEAN DEFAULT FALSE,
    
    -- Parámetro de salida
    INOUT io_product_id UUID DEFAULT NULL 
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación: Verificar si el proyecto existe
    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: El proyecto con ID % no existe. No se puede crear el producto.', p_project_id;
    END IF;

    -- 2. Generar el nuevo UUID
    io_product_id := uuid_generate_v4();

    -- 3. INSERTAR los datos
    INSERT INTO products (
        id, project_id, name, description, language, tipo, config, 
        welcome_message, label, label_color, max_users, 
        is_active_rag, is_active_alerts, is_active_insight, updated_at
        -- is_active y created_at usan defaults de columna
    )
    VALUES (
        io_product_id,
        p_project_id,
        p_name,
        p_description,
        p_language,
        p_tipo,
        p_config,
        p_welcome_message,
        p_label,
        p_label_color,
        p_max_users,
        p_is_active_rag,
        p_is_active_alerts,
        p_is_active_insight,
        CURRENT_TIMESTAMP
    );
    
    RAISE NOTICE 'Producto "%" (ID: %) creado exitosamente.', p_name, io_product_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_product(
    -- Parámetros OBLIGATORIOS para la operación
    p_product_id UUID,          -- ID del producto a actualizar
    p_project_id UUID,          -- Project ID (debe existir)
    p_name VARCHAR(200),
    
    -- Parámetros de actualización (con default para manejar opcionales)
    p_description VARCHAR(200) DEFAULT NULL,
    p_language VARCHAR(50) DEFAULT NULL,
    p_tipo VARCHAR(20) DEFAULT 'chatbot',
    p_config JSONB DEFAULT '{}'::jsonb,
    p_welcome_message VARCHAR(100) DEFAULT NULL,
    p_label VARCHAR(50) DEFAULT NULL,
    p_label_color VARCHAR(20) DEFAULT NULL,
    p_max_users INTEGER DEFAULT 100,
    p_is_active BOOLEAN DEFAULT TRUE,            -- Se incluye para poder cambiar el estado
    p_is_active_rag BOOLEAN DEFAULT FALSE,
    p_is_active_alerts BOOLEAN DEFAULT FALSE,
    p_is_active_insight BOOLEAN DEFAULT FALSE
    -- Nota: 'mensajes_mes' se excluye si se asume que es un contador y no se actualiza manualmente
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del producto
    IF NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. El producto con ID % no existe.', p_product_id;
    END IF;

    -- 2. Validación de existencia del proyecto (llave foránea)
    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: El nuevo proyecto con ID % no existe. No se puede reasignar el producto.', p_project_id;
    END IF;
    
    -- 3. ACTUALIZAR la fila
    UPDATE products
    SET
        project_id = p_project_id,
        name = p_name,
        description = p_description,
        language = p_language,
        tipo = p_tipo,
        config = p_config,
        welcome_message = p_welcome_message,
        label = p_label,
        label_color = p_label_color,
        max_users = p_max_users,
        is_active = p_is_active,
        is_active_rag = p_is_active_rag,
        is_active_alerts = p_is_active_alerts,
        is_active_insight = p_is_active_insight,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_product_id;
        
    RAISE NOTICE 'Producto con ID % actualizado exitosamente.', p_product_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_product(
    p_product_id UUID -- ID del producto a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_product_name VARCHAR(200);
BEGIN
    -- 1. Validar la existencia del producto y obtener su nombre
    SELECT "name" INTO v_product_name FROM products WHERE id = p_product_id;

    IF v_product_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El producto con ID % no existe.', p_product_id;
    END IF;

    -- 2. Eliminar la fila
    -- Nota: Al igual que con 'projects', si hay tablas que referencian este 'product_id'
    -- y no tienen ON DELETE CASCADE, esta operación fallará, lo cual es correcto.
    DELETE FROM products
    WHERE id = p_product_id;
    
    -- 3. Mensaje de éxito
    RAISE NOTICE 'Producto "%" (ID: %) eliminado exitosamente.', v_product_name, p_product_id;

END;
$$;

-- =======================================================
-- Generar Accesos Nivel Organizacion
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_user_org_access(
    p_user_id UUID,
    p_organization_id UUID,
    p_role_id UUID,
    INOUT io_access_id UUID DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validar Llaves Foráneas
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La organización con ID % no existe.', p_organization_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El rol con ID % no existe.', p_role_id;
    END IF;

    -- 2. Opcional: Evitar duplicados exactos (mismo usuario/misma organización/mismo rol)
    IF EXISTS (
        SELECT 1 FROM access_user_organization 
        WHERE user_id = p_user_id 
          AND organization_id = p_organization_id 
          AND role_id = p_role_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Este usuario ya tiene el rol especificado en esta organización.';
    END IF;

    -- 3. Generar ID e Insertar
    io_access_id := uuid_generate_v4();

    INSERT INTO access_user_organization (
        id, user_id, organization_id, role_id, updated_at
    )
    VALUES (
        io_access_id,
        p_user_id,
        p_organization_id,
        p_role_id,
        CURRENT_TIMESTAMP
    );
    
    RAISE NOTICE 'Acceso de usuario a organización creado con ID: %', io_access_id;
END;
$$;

select * from access_user_organization 
where 
	organization_id in ('e7c77bdf-8f8e-438c-b038-5ea9253e0ad7', '091bec7c-1288-4bce-a5c1-70e7e78fb1c8');

select * from users u  where id='45fd8678-a7f4-4547-9bd7-499ac951cab3';
select * from users u  where id='acf43599-b6cc-4300-99e8-1c4a19a8e271';


'e7c77bdf-8f8e-438c-b038-5ea9253e0ad7', '091bec7c-1288-4bce-a5c1-70e7e78fb1c8'

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_user_org_access(
    p_access_id UUID,             -- ID del registro de acceso a actualizar
    p_user_id UUID,               -- User ID (debe existir)
    p_organization_id UUID,       -- Organization ID (debe existir)
    p_role_id UUID                -- Nuevo Role ID (debe existir)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de acceso
    IF NOT EXISTS (SELECT 1 FROM access_user_organization WHERE id = p_access_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. El registro de acceso con ID % no existe.', p_access_id;
    END IF;

    -- 2. Validación de Llaves Foráneas
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La organización con ID % no existe.', p_organization_id;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El nuevo rol con ID % no existe.', p_role_id;
    END IF;

    -- 3. ACTUALIZAR la fila
    UPDATE access_user_organization
    SET
        user_id = p_user_id,
        organization_id = p_organization_id,
        role_id = p_role_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_access_id;
        
    RAISE NOTICE 'Registro de acceso % actualizado. Nuevo Rol ID: %', p_access_id, p_role_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_user_org_access(
    p_access_id UUID   -- ID del registro de acceso a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    -- 1. Intentar la eliminación
    DELETE FROM access_user_organization
    WHERE id = p_access_id;

    -- 2. Verificar si se eliminó alguna fila
    GET DIAGNOSTICS v_row_count = ROW_COUNT;

    IF v_row_count = 0 THEN
        -- Si no se eliminó ninguna fila, el registro no existía.
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El registro de acceso con ID % no existe.', p_access_id;
    ELSE
        -- Notificación de éxito
        RAISE NOTICE 'Registro de acceso con ID % eliminado exitosamente.', p_access_id;
    END IF;

END;
$$;

-- =======================================================
-- Generar Accesos Nivel Projects
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_user_project_access(
    p_user_id UUID,
    p_project_id UUID,
    p_role_id UUID,
    INOUT io_access_id UUID DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validar Llaves Foráneas
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: El proyecto con ID % no existe.', p_project_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El rol con ID % no existe.', p_role_id;
    END IF;

    -- 2. Opcional: Evitar duplicados exactos (mismo usuario/mismo proyecto/mismo rol)
    IF EXISTS (
        SELECT 1 FROM access_user_project 
        WHERE user_id = p_user_id 
          AND project_id = p_project_id 
          AND role_id = p_role_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Este usuario ya tiene el rol especificado en este proyecto.';
    END IF;

    -- 3. Generar ID e Insertar
    io_access_id := uuid_generate_v4();

    INSERT INTO access_user_project (
        id, user_id, project_id, role_id, updated_at
    )
    VALUES (
        io_access_id,
        p_user_id,
        p_project_id,
        p_role_id,
        CURRENT_TIMESTAMP
    );
    
    RAISE NOTICE 'Acceso de usuario a proyecto creado con ID: %', io_access_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_user_project_access(
    p_access_id UUID,             -- ID del registro de acceso a actualizar (la fila)
    p_user_id UUID,               -- User ID (debe existir)
    p_project_id UUID,            -- Project ID (debe existir)
    p_role_id UUID                -- Nuevo Role ID (debe existir)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de acceso
    IF NOT EXISTS (SELECT 1 FROM access_user_project WHERE id = p_access_id) THEN
        RAISE EXCEPTION 'ERROR: El registro de acceso a proyecto con ID % no existe.', p_access_id;
    END IF;

    -- 2. Validación de Llaves Foráneas (Asegurar que los IDs en el UPDATE existan)
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: El proyecto con ID % no existe.', p_project_id;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El nuevo rol con ID % no existe.', p_role_id;
    END IF;

    -- 3. ACTUALIZAR la fila
    UPDATE access_user_project
    SET
        user_id = p_user_id,
        project_id = p_project_id,
        role_id = p_role_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_access_id;
        
    RAISE NOTICE 'Registro de acceso a proyecto % actualizado. Nuevo Rol ID: %', p_access_id, p_role_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_user_project_access(
    p_access_id UUID   -- ID del registro de acceso a proyecto a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    -- 1. Intentar la eliminación
    DELETE FROM access_user_project
    WHERE id = p_access_id;

    -- 2. Verificar si se eliminó alguna fila
    GET DIAGNOSTICS v_row_count = ROW_COUNT;

    IF v_row_count = 0 THEN
        -- Si no se eliminó ninguna fila, el registro no existía.
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El registro de acceso a proyecto con ID % no existe.', p_access_id;
    ELSE
        -- Notificación de éxito
        RAISE NOTICE '✅ Registro de acceso a proyecto con ID % eliminado exitosamente.', p_access_id;
    END IF;

END;
$$;

-- =======================================================
-- Generar Accesos Nivel Product
-- =======================================================


CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_user_prd_access(
    p_user_id UUID,
    p_product_id UUID,
    p_role_id UUID,
    INOUT io_access_id UUID DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validar Llaves Foráneas
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'ERROR: El producto con ID % no existe.', p_product_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El rol con ID % no existe.', p_role_id;
    END IF;
    
    -- Nota: Si 'data_role_id' debe validarse, la validación se colocaría aquí.

    -- 2. Opcional: Evitar duplicados exactos (mismo usuario/mismo producto/mismo rol)
    IF EXISTS (
        SELECT 1 FROM access_user_product 
        WHERE user_id = p_user_id 
          AND product_id = p_product_id 
          AND role_id = p_role_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Este usuario ya tiene el rol especificado en este producto.';
    END IF;

    -- 3. Generar ID e Insertar
    io_access_id := uuid_generate_v4();
	
    INSERT INTO access_user_product (
        id, user_id, product_id, role_id, updated_at
    )
    VALUES (
        io_access_id,
        p_user_id,
        p_product_id,
        p_role_id,
        CURRENT_TIMESTAMP
    );
    
    RAISE NOTICE 'Acceso de usuario a producto creado con ID: %', io_access_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_user_prd_access(
    p_access_id UUID,             -- ID del registro de acceso a actualizar
    p_user_id UUID,               -- User ID (debe existir)
    p_product_id UUID,            -- Product ID (debe existir)
    p_role_id UUID               -- Nuevo Role ID (debe existir)
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de acceso
    IF NOT EXISTS (SELECT 1 FROM access_user_product WHERE id = p_access_id) THEN
        RAISE EXCEPTION 'ERROR: El registro de acceso a producto con ID % no existe.', p_access_id;
    END IF;

    -- 2. Validación de Llaves Foráneas (Asegurar que los nuevos IDs existan)
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'ERROR: El usuario con ID % no existe.', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'ERROR: El producto con ID % no existe.', p_product_id;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'ERROR: El nuevo rol con ID % no existe.', p_role_id;
    END IF;

    -- 3. ACTUALIZAR la fila
    UPDATE access_user_product
    SET
        user_id = p_user_id,
        product_id = p_product_id,
        role_id = p_role_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_access_id;
        
    RAISE NOTICE 'Registro de acceso a producto % actualizado.', p_access_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_user_prd_access(
    p_access_id UUID   -- ID del registro de acceso a producto a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    -- 1. Intentar la eliminación
    DELETE FROM access_user_product
    WHERE id = p_access_id;

    -- 2. Verificar si se eliminó alguna fila
    GET DIAGNOSTICS v_row_count = ROW_COUNT;

    IF v_row_count = 0 THEN
        -- Si no se eliminó ninguna fila, el registro no existía.
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El registro de acceso a producto con ID % no existe.', p_access_id;
    ELSE
        -- Notificación de éxito
        RAISE NOTICE '✅ Registro de acceso a producto con ID % eliminado exitosamente.', p_access_id;
    END IF;

END;
$$;

-- =======================================================
-- Conexion a Datos
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_data_connection(
    p_organization_id UUID,
    p_name VARCHAR,
    p_type VARCHAR,
    p_configuration JSONB,
    INOUT io_connection_id UUID DEFAULT NULL -- Devuelve el nuevo ID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación: Verificar que la organización exista (llave foránea)
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La organización con ID % no existe. No se puede crear la conexión.', p_organization_id;
    END IF;

    -- 2. Generar ID e Insertar
    io_connection_id := gen_random_uuid();
    
    INSERT INTO data_connections (
        id,
        organization_id,
        name,
        type,
        configuration
    )
    VALUES (
        io_connection_id,
        p_organization_id,
        p_name,
        p_type,
        p_configuration
    );

    RAISE NOTICE 'Conexión "%" (ID: %) creada exitosamente.', p_name, io_connection_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_data_connection(
    p_connection_id UUID,           -- ID de la conexión a actualizar
    p_organization_id UUID,         -- Organization ID (puede usarse para reasignar)
    p_name VARCHAR,
    p_type VARCHAR,
    p_configuration JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de conexión
    IF NOT EXISTS (SELECT 1 FROM data_connections WHERE id = p_connection_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. La conexión con ID % no existe.', p_connection_id;
    END IF;

    -- 2. Validación de existencia de la organización (llave foránea)
    IF NOT EXISTS (SELECT 1 FROM organizations WHERE id = p_organization_id) THEN
        RAISE EXCEPTION 'ERROR: La organización con ID % no existe. No se puede reasignar la conexión.', p_organization_id;
    END IF;
    
    -- 3. ACTUALIZAR la fila
    UPDATE data_connections
    SET
        organization_id = p_organization_id,
        name = p_name,
        type = p_type,
        configuration = p_configuration
        -- Nota: updated_at no existe en tu esquema, pero 'name', 'type', 'configuration' son actualizados.
    WHERE
        id = p_connection_id;
        
    RAISE NOTICE 'Conexión con ID % actualizada exitosamente.', p_connection_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_data_connection(
    p_connection_id UUID -- ID de la conexión a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_connection_name VARCHAR(255);
BEGIN
    -- 1. Validar la existencia de la conexión y obtener su nombre para el mensaje
    SELECT "name" INTO v_connection_name FROM data_connections WHERE id = p_connection_id;

    IF v_connection_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La conexión con ID % no existe.', p_connection_id;
    END IF;

    -- 2. Eliminar la fila
    -- Nota: Si hay tablas que referencian este 'connection_id'
    -- y no tienen ON DELETE CASCADE, esta operación fallará, lo cual es correcto.
    DELETE FROM data_connections
    WHERE id = p_connection_id;
    
    -- 3. Mensaje de éxito
    RAISE NOTICE 'Conexión "%" (ID: %) eliminada exitosamente.', v_connection_name, p_connection_id;

END;
$$;

-- =======================================================
-- Canales de Chatbot
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_channel(
    p_name VARCHAR(100),
    p_description VARCHAR(100) DEFAULT NULL,
    INOUT io_result_id UUID DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Inserción del nuevo canal
    INSERT INTO channels (
        name, 
        description, 
        updated_at
    )
    VALUES (
        p_name,
        p_description,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO io_result_id; -- Captura el UUID generado
    
    RAISE NOTICE 'Canal "%" (ID: %) creado exitosamente.', p_name, io_result_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_channel(
    p_id UUID,
    p_name VARCHAR(100),
    p_description VARCHAR(100) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de canal
    IF NOT EXISTS (SELECT 1 FROM channels WHERE id = p_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. El canal con ID % no existe.', p_id;
    END IF;
    
    -- 2. Actualizar la fila
    UPDATE channels
    SET
        name = p_name,
        description = p_description,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        id = p_id;
        
    RAISE NOTICE 'Canal con ID % actualizado exitosamente.', p_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_channel(
    p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro de canal
    IF NOT EXISTS (SELECT 1 FROM channels WHERE id = p_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El canal con ID % no existe.', p_id;
    END IF;
    
    -- 2. Eliminar la fila
    DELETE FROM channels
    WHERE id = p_id;
        
    RAISE NOTICE 'Canal con ID % eliminado exitosamente.', p_id;

END;
$$;

-- =======================================================
-- Canales por Chatbots Producto
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_channel_product(
    p_channel_id UUID,
    p_product_id UUID,
    p_channel_product_type VARCHAR(100), -- NUEVO CAMPO
    p_configuration JSONB,
    INOUT io_result_id UUID DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validar Llaves Foráneas (Asumiendo que products y channels existen)
    IF NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'ERROR: El producto con ID % no existe.', p_product_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM channels WHERE id = p_channel_id) THEN
        RAISE EXCEPTION 'ERROR: El canal con ID % no existe.', p_channel_id;
    END IF;

    -- 2. Opcional: Validar unicidad (siempre es buena práctica)
    IF EXISTS (
        SELECT 1 FROM channel_product 
        WHERE channel_id = p_channel_id AND product_id = p_product_id
    ) THEN
        RAISE EXCEPTION 'ERROR: La relación entre el canal % y producto % ya existe. Utilice la función de actualización.', p_channel_id, p_product_id;
    END IF;
    
    -- 3. Insertar y capturar el ID generado por DEFAULT
    INSERT INTO channel_product (
        channel_id, 
        product_id,
        channel_product_type, -- NUEVO CAMPO
        configuration
    )
    VALUES (
        p_channel_id,
        p_product_id,
        p_channel_product_type, -- NUEVO VALOR
        p_configuration
    )
    RETURNING id INTO io_result_id;

    RAISE NOTICE 'Nueva relación de canal-producto creada con ID: %', io_result_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_channel_product(
    p_id UUID,
    p_channel_id UUID,
    p_product_id UUID,
    p_channel_product_type VARCHAR(100), -- NUEVO CAMPO
    p_configuration JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro (ID principal)
    IF NOT EXISTS (SELECT 1 FROM channel_product WHERE id = p_id) THEN
        RAISE EXCEPTION 'ERROR: El registro de relación con ID % no existe. No se puede actualizar.', p_id;
    END IF;
    
    -- 2. Validar Llaves Foráneas (Asegurar que los nuevos IDs existan)
    IF NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'ERROR: El producto con ID % no existe.', p_product_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM channels WHERE id = p_channel_id) THEN
        RAISE EXCEPTION 'ERROR: El canal con ID % no existe.', p_channel_id;
    END IF;
    
    -- 3. Actualizar la fila
    UPDATE channel_product
    SET
        channel_id = p_channel_id,
        product_id = p_product_id,
        channel_product_type = p_channel_product_type, -- NUEVO CAMPO
        configuration = p_configuration
    WHERE
        id = p_id;
        
    RAISE NOTICE 'Registro de relación con ID % actualizado exitosamente.', p_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_channel_product(
    p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Validación de existencia del registro
    IF NOT EXISTS (SELECT 1 FROM channel_product WHERE id = p_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El registro de relación con ID % no existe.', p_id;
    END IF;
    
    -- 2. Eliminar la fila
    DELETE FROM channel_product
    WHERE id = p_id;
        
    RAISE NOTICE 'Registro de relación con ID % eliminado exitosamente.', p_id;

END;
$$;

-- =======================================================
-- Registro y Actualizacion de prompts
-- =======================================================
CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_prompt(
    IN p_product_id UUID,
    IN p_name VARCHAR(255),
    IN p_config_prompt JSONB,
    IN p_content_prompt TEXT,
    IN p_path_config_file VARCHAR(255),
    OUT new_prompt_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insertar el nuevo registro
    INSERT INTO "prompts" (
        "product_id",
        "name",
        "config_prompt",
		"prompt_content",
        "path_config_file",
        "updated_at"
    )
    VALUES (
        p_product_id,
        p_name,
        p_config_prompt,
		p_content_prompt,
        p_path_config_file,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO new_prompt_id; -- Capturar el ID generado

END;
$$;


CREATE OR REPLACE PROCEDURE spu_minddash_app_update_prompt(
    IN p_id UUID,
    IN p_product_id UUID DEFAULT NULL,
    IN p_name VARCHAR(255) DEFAULT NULL,
    IN p_config_prompt JSONB DEFAULT NULL,
    IN p_content_prompt TEXT DEFAULT NULL,
    IN p_path_config_file VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Actualizar el registro
    UPDATE "prompts"
    SET
        "product_id" = COALESCE(p_product_id, "product_id"),
        "name" = COALESCE(p_name, "name"),
        "config_prompt" = COALESCE(p_config_prompt, "config_prompt"),
		"prompt_content"= COALESCE(p_content_prompt, "prompt_content"),
        "path_config_file" = COALESCE(p_path_config_file, "path_config_file"),
        "updated_at" = CURRENT_TIMESTAMP
    WHERE
        "id" = p_id;

    -- Nota: A diferencia de la función, un PROCEDURE no devuelve el estado FOUND
    -- (pero se puede acceder a ROW_COUNT si es necesario para el cliente).

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_prompt(
    p_id UUID   -- ID del prompt a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_row_count INTEGER;
BEGIN
    -- 1. Intentar la eliminación
    DELETE FROM "prompts"
    WHERE "id" = p_id;

    -- 2. Verificar si se eliminó alguna fila
    GET DIAGNOSTICS v_row_count = ROW_COUNT;

    IF v_row_count = 0 THEN
        -- Si no se eliminó ninguna fila, el registro no existía.
        RAISE EXCEPTION 'ERROR: El prompt con ID % no existe y no pudo ser eliminado.', p_id;
    ELSE
        -- Notificación de éxito
        RAISE NOTICE '✅ Prompt con ID % eliminado exitosamente.', p_id;
    END IF;

END;
$$;

-- =======================================================
-- Registro y Actualizacion de metricass
-- =======================================================
CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_metric(
    IN p_product_id UUID,
    IN p_name VARCHAR(200),
    IN p_description VARCHAR(200),
    IN p_data_query TEXT,
    IN p_required_params TEXT[], -- Nuevo parámetro
    IN p_optional_params TEXT[], -- Nuevo parámetro
    OUT new_metric_id UUID -- Parámetro OUT para devolver el ID generado
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insertar el nuevo registro. El ID se genera automáticamente.
    INSERT INTO "metrics" (
        "product_id",
        "name",
        "description",
        "data_query",
        "required_params", -- Nueva columna
        "optional_params"  -- Nueva columna
    )
    VALUES (
        p_product_id,
        p_name,
        p_description,
        p_data_query,
        p_required_params, -- Nuevo valor
        p_optional_params  -- Nuevo valor
    )
    RETURNING id INTO new_metric_id; -- Capturar el ID generado en la variable de salida

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_metric(
    IN p_id UUID,
    IN p_product_id UUID DEFAULT NULL,
    IN p_name VARCHAR(200) DEFAULT NULL,
    IN p_description VARCHAR(200) DEFAULT NULL,
    IN p_data_query TEXT DEFAULT NULL,
    IN p_required_params TEXT[] DEFAULT NULL, -- Nuevo parámetro
    IN p_optional_params TEXT[] DEFAULT NULL  -- Nuevo parámetro
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Actualizar el registro
    UPDATE "metrics"
    SET
        "product_id" = COALESCE(p_product_id, "product_id"),
        "name" = COALESCE(p_name, "name"),
        "description" = COALESCE(p_description, "description"),
        "data_query" = COALESCE(p_data_query, "data_query"),
        "required_params" = COALESCE(p_required_params, "required_params"), -- Nueva columna
        "optional_params" = COALESCE(p_optional_params, "optional_params")  -- Nueva columna
    WHERE
        "id" = p_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_metric(
    p_metric_id UUID -- ID de la métrica a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_metric_name VARCHAR(200);
BEGIN
    -- 1. Validar la existencia de la métrica y obtener su nombre para el mensaje
    SELECT "name" INTO v_metric_name FROM metrics WHERE id = p_metric_id;

    IF v_metric_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La métrica con ID % no existe.', p_metric_id;
    END IF;

    -- 2. Eliminar la fila
    -- Nota: Si hay tablas que referencian este 'metric_id'
    -- y no tienen ON DELETE CASCADE, esta operación fallará, lo cual es correcto.
    DELETE FROM metrics
    WHERE id = p_metric_id;
    
    -- 3. Mensaje de éxito
    RAISE NOTICE 'Métrica "%" (ID: %) eliminada exitosamente.', v_metric_name, p_metric_id;

END;
$$;

-- =======================================================
-- Registro y Actualizacion de examples
-- =======================================================


CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_example(
    IN p_product_id UUID,
    IN p_name VARCHAR(255),
    IN p_description  VARCHAR(200),
    IN p_data_query text,
    OUT new_example_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insertar el nuevo registro
    INSERT INTO "examples" (
        "product_id",
        "name",
        "description",
        "data_query",
        "created_at",
		"updated_at"
    )
    VALUES (
        p_product_id,
        p_name,
        p_description,
        p_data_query,
        CURRENT_TIMESTAMP,
		CURRENT_TIMESTAMP
    )
    RETURNING id INTO new_example_id; -- Capturar el ID generado

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_example(
    IN p_id UUID,
    IN p_product_id UUID DEFAULT NULL,
    IN p_name VARCHAR(200) DEFAULT NULL,
    IN p_description VARCHAR(200) DEFAULT NULL,
    IN p_data_query TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Actualizar el registro
    UPDATE "examples"
    SET
        "product_id" = COALESCE(p_product_id, "product_id"),
        "name" = COALESCE(p_name, "name"),
        "description" = COALESCE(p_description, "description"),
        "data_query" = COALESCE(p_data_query, "data_query")
    WHERE
        "id" = p_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_example(
    IN p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Eliminar el registro de la tabla "examples"
    DELETE FROM "examples"
    WHERE
        "id" = p_id;
        
    -- NOTA: Podrías añadir lógica aquí para verificar si se eliminó alguna fila 
    -- o para manejar errores si el ID no existe, si fuera necesario.
END;
$$;

-- =======================================================
-- Registro y Actualizacion de Alertas
-- =======================================================


CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_alerta(
    -- Parámetros IN sin valor por defecto (obligatorios)
    IN p_product_id UUID,
    IN p_prompt_alerta VARCHAR(1500),
    IN p_codigo_cron VARCHAR(100),
    IN p_user_id VARCHAR(150),
    IN p_session_id VARCHAR(150),
    IN p_channel_product_type VARCHAR(100),
    
    -- Parámetro OUT
    OUT new_alerta_id UUID,
    
    -- Parámetros IN con valor por defecto (opcionales al llamar)
    IN p_flg_habilitado BOOLEAN DEFAULT TRUE,
    IN p_fecha_inicio TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    IN p_fecha_fin TIMESTAMP WITH TIME ZONE DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;      -- Variable para almacenar el conteo actual
    v_max_alerts INTEGER := 3; -- Constante: Límite máximo permitido
BEGIN
	-- 0. Asignar la variable de alertas maximo por usuario
	SELECT value_config::INTEGER INTO v_max_alerts FROM config_alerts WHERE key_config = 'MAX_ALERTS_PER_USER';
    
	v_max_alerts := COALESCE(v_max_alerts, 3);

    -- 1. Verificar la cantidad actual de alertas para este usuario y producto
    SELECT COUNT(*) INTO v_count
    FROM alerts_prompts
    WHERE product_id = p_product_id 
      AND user_id = p_user_id;

    -- 2. Validar si supera o iguala el límite (>= 3)
    IF v_count >= v_max_alerts THEN
        RAISE EXCEPTION 'Límite alcanzado: El usuario ya tiene % alertas para este producto. El máximo es %.', v_count, v_max_alerts
        USING ERRCODE = 'P0001'; 
    END IF;

    -- 3. Insertar el nuevo registro si pasó la validación
    INSERT INTO alerts_prompts (
        product_id,
        prompt_alerta,
        user_id,
        session_id,
        codigo_cron,
        channel_product_type,
        flg_habilitado,
        fecha_inicio,
        fecha_fin
    )
    VALUES (
        p_product_id,
        p_prompt_alerta,
        p_user_id,
        p_session_id,
        p_codigo_cron,
        p_channel_product_type,
        p_flg_habilitado, 
        p_fecha_inicio,  
        p_fecha_fin    
    )
    RETURNING id INTO new_alerta_id;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_alerta(
    IN p_id UUID,
    IN p_product_id UUID DEFAULT NULL,
    IN p_prompt_alerta VARCHAR(1500) DEFAULT NULL,
    IN p_codigo_cron VARCHAR(100) DEFAULT NULL,
    IN p_flg_habilitado BOOLEAN DEFAULT NULL,
    IN p_fecha_inicio TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    IN p_fecha_fin TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    IN p_session_id VARCHAR(150) DEFAULT NULL,
    IN p_user_id VARCHAR(150) DEFAULT NULL,
    IN p_channel_product_type VARCHAR(100) DEFAULT NULL -- NUEVO CAMPO
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Actualizar el registro en la tabla "alerts_prompts"
    UPDATE alerts_prompts
    SET
        "product_id" = COALESCE(p_product_id, "product_id"), 
        prompt_alerta = COALESCE(p_prompt_alerta, prompt_alerta),
        codigo_cron = COALESCE(p_codigo_cron, codigo_cron),
        user_id = COALESCE(p_user_id, user_id),
        session_id = COALESCE(p_session_id, session_id),
        channel_product_type = COALESCE(p_channel_product_type, channel_product_type), -- NUEVO
        flg_habilitado = COALESCE(p_flg_habilitado, flg_habilitado),
        fecha_inicio = COALESCE(p_fecha_inicio, fecha_inicio),
        fecha_fin = COALESCE(p_fecha_fin, fecha_fin),
        "updated_at" = NOW()
    WHERE
        id = p_id; 
    
    -- 2. Lógica de validación de existencia
    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. La alerta con ID % no existe.', p_id;
    END IF;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_alerta(
    IN p_id UUID -- ID de la alerta a eliminar
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Eliminar el registro de la tabla "alerts_prompts"
    DELETE FROM alerts_prompts
    WHERE
        id = p_id; 
        
    IF NOT FOUND THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La alerta con ID % no existe.', p_id;
    END IF;
END;
$$;

-- =======================================================
-- Registro y Actualizacion de semantic layer
-- =======================================================

-- =======================================================
-- Registro y Actualizacion de Data Access Roles
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_role_data_access(
    -- 1. Parámetros IN de Datos (5 argumentos)
    IN p_product_id UUID,
    IN p_name VARCHAR,
    IN p_table_names TEXT[],
    IN p_data_access JSONB,
    IN p_metrics_access TEXT[],
    
    -- 2. Parámetro OUT (último)
    OUT new_role_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- [Lógica de validación omitida por espacio]
    -- ...
    
    -- Insertar el nuevo registro
    INSERT INTO roles_data_access (
        product_id,
        name,
        table_names,
        data_access,
        metrics_access, 
        updated_at
    )
    VALUES (
        p_product_id,
        p_name,
        p_table_names,
        p_data_access,
        p_metrics_access,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO new_role_id; -- Captura el ID en el parámetro OUT

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_role_data_access(
    -- Parámetros IN (6 en total)
    IN p_id UUID,
    IN p_product_id UUID, -- << NUEVO PARÁMETRO
    IN p_name VARCHAR,
    IN p_table_names TEXT[],
    IN p_data_access JSONB,
    IN p_metrics_access TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing_product_id UUID; -- Variable para validar si el product_id coincide si es necesario
BEGIN
    -- Verificar si el registro existe
    SELECT product_id INTO v_existing_product_id
    FROM roles_data_access
    WHERE id = p_id;

    IF v_existing_product_id IS NULL THEN
        RAISE EXCEPTION 'No se encontró el rol con ID: %', p_id
        USING HINT = 'Verifica que el ID sea correcto.';
    END IF;

    -- Opcional: Validar si el product_id proporcionado coincide con el existente
    -- if p_product_id IS NOT NULL AND p_product_id <> v_existing_product_id THEN
    --     RAISE EXCEPTION 'El product_id proporcionado (%) no coincide con el del rol existente (%).', p_product_id, v_existing_product_id;
    -- END IF;

    -- Validar que el nuevo nombre no exista para otro rol del mismo producto
    IF EXISTS (
        SELECT 1
        FROM roles_data_access
        WHERE product_id = COALESCE(p_product_id, v_existing_product_id) -- Usa el nuevo o el existente
          AND name = p_name
          AND id <> p_id
    ) THEN
        RAISE EXCEPTION 'Ya existe otro rol con el nombre "%" para el producto %.', p_name, COALESCE(p_product_id, v_existing_product_id)
        USING HINT = 'Por favor, elige un nombre diferente.';
    END IF;

    -- Actualizar el registro
    UPDATE roles_data_access
    SET
        -- Actualiza product_id SOLO si se proporciona uno nuevo (COALESCE)
        product_id = COALESCE(p_product_id, roles_data_access.product_id), 
        name = p_name,
        table_names = p_table_names,
        data_access = p_data_access,
        metrics_access = p_metrics_access,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_id;

END;
$$;


CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_role_data_access(
    IN p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Intentar eliminar el registro
    DELETE FROM roles_data_access
    WHERE id = p_id;

    -- Si no se eliminó ninguna fila, lanzar una advertencia o excepción
    IF NOT FOUND THEN
        -- Cambiado a RAISE EXCEPTION para coincidir con la lógica del router (404)
        RAISE EXCEPTION 'No se puede eliminar. El rol con ID % no existe.', p_id;
    END IF;

END;
$$;

-- =======================================================
-- Registro y Actualizacion de Semantic Layers
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_role_semantic_layer(
    OUT p_new_id UUID,                     -- MOVIDO AL PRINCIPIO
    IN p_product_id UUID,
    IN p_object_path_saved VARCHAR,
    IN p_bucket_name_saved VARCHAR,
    IN p_object_path_deployed VARCHAR DEFAULT NULL,
    IN p_bucket_name_deployed VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insertar el nuevo registro
    INSERT INTO semantic_layer_configs (
        product_id,
        object_path_saved,
        bucket_name_saved,
        object_path_deployed,
        bucket_name_deployed,
        updated_at
    )
    VALUES (
        p_product_id,
        p_object_path_saved,
        p_bucket_name_saved,
        p_object_path_deployed,
        p_bucket_name_deployed,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO p_new_id;
END;
$$;

--CREATE OR REPLACE PROCEDURE spu_minddash_app_update_role_semantic_layer(
--    IN p_id UUID,
--    IN p_product_id UUID,
--    IN p_object_path_saved VARCHAR,
--    IN p_bucket_name_saved VARCHAR,
--    IN p_object_path_deployed VARCHAR,
--    IN p_bucket_name_deployed VARCHAR
--  
    
CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_role_data_access(
    p_role_id UUID -- ID del rol de acceso a datos a eliminar
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_role_name VARCHAR(255);
BEGIN
    -- 1. Validar la existencia del rol y obtener su nombre para el mensaje
    SELECT "name" INTO v_role_name FROM roles_data_access WHERE id = p_role_id;

    IF v_role_name IS NULL THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El rol de acceso a datos con ID % no existe.', p_role_id;
    END IF;

    -- 2. Eliminar la fila
    -- Nota: Si hay tablas que referencian este 'role_id'
    -- y no tienen ON DELETE CASCADE, esta operación fallará, lo cual es correcto.
    DELETE FROM roles_data_access
    WHERE id = p_role_id;
    
    -- 3. Mensaje de éxito
    RAISE NOTICE 'Rol de acceso a datos "%" (ID: %) eliminado exitosamente.', v_role_name, p_role_id;

END;
$$;

-- =======================================================
-- User Data Access
-- =======================================================


CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_user_data_access(
    -- 1. Parámetro OUT
    OUT new_user_data_access_id UUID,
    
    -- 2. Parámetros IN sin DEFAULT (obligatorios)
    IN p_role_data_id UUID,
    
    -- 3. Parámetros IN con DEFAULT (opcionales)
    IN p_user_id UUID DEFAULT NULL,
    IN p_table_names TEXT[] DEFAULT NULL,
    IN p_data_access JSONB DEFAULT NULL,
    IN p_metrics_access TEXT[] DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Validar que el user_id no sea NULL si es necesario
    IF p_user_id IS NULL THEN
        RAISE EXCEPTION 'El ID de usuario (p_user_id) no puede ser NULL.';
    END IF;

    INSERT INTO "user_data_access" (
        "role_data_id",
        "user_id",
        "table_names",
        "data_access",
        "metrics_access",
        "updated_at"
    )
    VALUES (
        p_role_data_id,
        p_user_id,
        COALESCE(p_table_names, '{}'::TEXT[]), -- Usar array vacío si es NULL
        p_data_access,
        p_metrics_access,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO new_user_data_access_id;

END;
$$;
 
CREATE OR REPLACE PROCEDURE spu_minddash_app_update_user_data_access(
    IN p_id UUID,
    IN p_role_data_id UUID DEFAULT NULL,
    IN p_user_id UUID DEFAULT NULL,
    IN p_table_names TEXT[] DEFAULT NULL,
    IN p_data_access JSONB DEFAULT NULL,
    IN p_metrics_access TEXT[] DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Actualizar el registro por ID
    UPDATE "user_data_access"
    SET
        "role_data_id" = COALESCE(p_role_data_id, "role_data_id"),
        "user_id" = COALESCE(p_user_id, "user_id"),
        "table_names" = COALESCE(p_table_names, "table_names"),
        "data_access" = COALESCE(p_data_access, "data_access"),
        "metrics_access" = COALESCE(p_metrics_access, "metrics_access"),
        "updated_at" = CURRENT_TIMESTAMP
    WHERE
        "id" = p_id;

    -- Validar si se actualizó alguna fila
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No se puede actualizar. El acceso de datos de usuario con ID % no existe.', p_id;
    END IF;

END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_user_data_access(
    IN p_user_data_access_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Eliminar la fila
    DELETE FROM user_data_access
    WHERE id = p_user_data_access_id;
    
    -- 2. Validar si se eliminó alguna fila
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No se puede eliminar. El acceso de datos de usuario con ID % no existe.', p_user_data_access_id;
    END IF;

END;
$$;



CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_role_semantic_layer(
    IN p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Intentar eliminar el registro
    DELETE FROM semantic_layer_configs
    WHERE id = p_id;

    -- Verificar si se eliminó una fila
    IF NOT FOUND THEN
        -- Si no se encuentra, emitimos una ADVERTENCIA (WARNING).
        RAISE WARNING 'No se encontró un registro con ID % para eliminar.', p_id;
    END IF;
END;
$$;
  

-- =======================================================
-- Registro y Actualizacion de Data Access
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_client_product_deploy(
    OUT p_new_id UUID,
    IN p_product_id UUID,
    IN p_bucket_config VARCHAR,
    IN p_gs_examples_agent VARCHAR,
    IN p_gs_prompt_agent VARCHAR,
    IN p_gs_prompt_sql VARCHAR,
    IN p_gs_profiling_agent VARCHAR,
    IN p_gs_metrics_config_agent VARCHAR,
    IN p_client TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Insertar el nuevo registro
    INSERT INTO clients_products_deploys (
        product_id,
        bucket_config,
        gs_examples_agent,
        gs_prompt_agent,
        gs_prompt_sql,
        gs_profiling_agent,
        gs_metrics_config_agent,
        client,
        updated_at
    )
    VALUES (
        p_product_id,
        p_bucket_config,
        p_gs_examples_agent,
        p_gs_prompt_agent,
        p_gs_prompt_sql,
        p_gs_profiling_agent,
        p_gs_metrics_config_agent,
        p_client,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO p_new_id;
END;
$$;


-- Asegúrate de que no haya un procedimiento anterior con firma diferente
DROP PROCEDURE IF EXISTS spu_minddash_app_update_client_product_deploy(uuid, uuid, varchar, varchar, varchar, varchar, varchar, varchar, text);

CREATE OR REPLACE PROCEDURE spu_minddash_app_update_client_product_deploy(
    IN p_id UUID,
    IN p_product_id UUID,
    IN p_bucket_config VARCHAR,
    IN p_gs_examples_agent VARCHAR,
    IN p_gs_prompt_agent VARCHAR,
    IN p_gs_prompt_sql VARCHAR,
    IN p_gs_profiling_agent VARCHAR,
    IN p_gs_metrics_config_agent VARCHAR,
    IN p_client TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Actualizar el registro
    UPDATE clients_products_deploys
    SET
        product_id = p_product_id,
        bucket_config = p_bucket_config,
        gs_examples_agent = p_gs_examples_agent,
        gs_prompt_agent = p_gs_prompt_agent,
        gs_prompt_sql = p_gs_prompt_sql,
        gs_profiling_agent = p_gs_profiling_agent,
        gs_metrics_config_agent = p_gs_metrics_config_agent,
        client = p_client,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_id;

    -- Si no se encuentra, emitir una advertencia (o excepción, según tu estándar)
    IF NOT FOUND THEN
        RAISE WARNING 'No se encontró la configuración con ID: % para actualizar.', p_id;
    END IF;
END;
$$;


-- Asegúrate de que no haya un procedimiento anterior con firma diferente
DROP PROCEDURE IF EXISTS spu_minddash_app_delete_client_product_deploy(uuid);

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_client_product_deploy(
    IN p_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Intentar eliminar el registro
    DELETE FROM clients_products_deploys
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE WARNING 'No se encontró un registro con ID % para eliminar.', p_id;
    END IF;
END;
$$;


-- =======================================================
-- Control & validation of metrics
-- =======================================================

CREATE OR REPLACE PROCEDURE spu_minddash_app_control_validation_metrics(
    p_organization_id VARCHAR(50),
    p_metrics_control_id VARCHAR(25),                                                                                                                                                                                                                                                                                                                                                                                                              
    INOUT validation_creation boolean DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- 1. Generar el nuevo UUID y asignarlo al parámetro INOUT
    io_organization_id := uuid_generate_v4();
    
    -- 2. Insertar los datos, usando el ID del parámetro
    INSERT INTO organizations (
        id, name, company_name, description, country, updated_at
    )
    VALUES (
        io_organization_id, -- Usamos el ID asignado
        p_name,
        p_company_name,
        p_description,
        p_country,
        CURRENT_TIMESTAMP
    );
END;
$$;
