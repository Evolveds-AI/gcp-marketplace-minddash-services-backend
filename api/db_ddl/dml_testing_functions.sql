-- =======================================================
-- Crear Elementos Organizacion
-- =======================================================

DO $$
DECLARE
    org_id_temp UUID;
BEGIN
    -- Llama al SP, pasando el ID temporal para que reciba el valor de salida
    CALL spu_minddash_app_insert_organization(
        p_name := 'SoftDev Solutions Beta2',
        p_company_name := 'Horizon Tech Corp.',
        p_description := 'Desarrollo de software empresarial y consultoría en la nube.',
        p_country := 'Canadá',
        io_organization_id := org_id_temp -- Asigna el valor generado a esta variable
    );
    
    -- Muestra el valor de salida
    RAISE NOTICE 'Nuevo ID generado: %', org_id_temp;
END $$;


{
  "id": "a4456faf-d83d-4226-a4e6-370a4d1c9828",
  "name": "SoftDev Solutions Beta2 Update",
  "company_name": "Horizon Tech Corp.",
  "description": "Horizon Tech Corp.",
  "country": "Peru"
}





select * from organizations o  where id='904b6615-a885-4be6-9ca0-135a6ed0857f'

-- =======================================================
-- Crear Elementos Projecto
-- =======================================================
DO $$
DECLARE
    -- Declara una variable para capturar el UUID de salida
    new_project_id UUID; 
    
    -- Variables de ejemplo para los parámetros
    v_org_id UUID := 'e7c77bdf-8f8e-438c-b038-5ea9253e0ad7'; -- Reemplazar con un ID de organización válido
    v_name VARCHAR(50) := 'Proyecto Alfa';
    v_label VARCHAR(50) := 'ALFA-2025';
    v_color VARCHAR(20) := '#007bff';
    v_desc VARCHAR(200) := 'Este es el primer proyecto insertado de prueba.';
    
BEGIN
    -- Ejecuta el procedimiento, pasando la variable como INOUT
    CALL spu_minddash_app_insert_project(
        p_organization_id => v_org_id,
        p_name => v_name,
        p_label => v_label,
        p_label_color => v_color,
        p_description => v_desc,
        io_project_id => new_project_id -- Aquí se captura el ID
    );
    
    -- Muestra el ID devuelto
    RAISE NOTICE 'ID del Proyecto Creado: %', new_project_id;
    
END $$;

CALL spu_minddash_app_update_project(
    p_project_id      => '46c1189b-0670-47db-b764-5b5df74d0ace', -- Reemplazar con el ID del proyecto a modificar
    p_organization_id => 'e7c77bdf-8f8e-438c-b038-5ea9253e0ad7', -- Reemplazar con un ID de organización válido
    p_name            => 'Proyecto Alfa (Revisado)',
    p_label           => 'ALFA-REV',
    p_label_color     => '#28a745', -- Nuevo color (verde)
    p_description     => 'Descripción actualizada del proyecto.'
);

CALL spu_minddash_app_delete_project(
    p_project_id => '46c1189b-0670-47db-b764-5b5df74d0ace' -- Reemplazar con el ID del proyecto a eliminar
);

/*
 {
  "description": "Desarrollo de la fase inicial de la plataforma de datos.",
  "label": "ALFA-2025",
  "label_color": "#ffc107",
  "name": "Proyecto Alfa testing",
  "organization_id": "e7c77bdf-8f8e-438c-b038-5ea9253e0ad7"
}
*/
select * from projects
where id ='28f7f6ae-9b2b-4c85-9008-6f11e45f18ef'


---


-- =======================================================
-- Crear Elementos Producto
-- =======================================================

DO $$
DECLARE
    new_product_id UUID; 
    v_project_id UUID := 'a6f38618-4308-4dfc-83d7-4f98651649c1'; -- Reemplazar con ID de Proyecto válido
    v_config JSONB := '{"model": "gpt-4o", "temperature": 0.5}'::jsonb;
    
BEGIN
    CALL spu_minddash_app_insert_product(
        p_project_id          => v_project_id,
        p_name                => 'Chatbot de Soporte Web Test SQL',
        p_description         => 'Asistente para la web principal de la empresa.',
        p_language            => 'es',
        p_tipo                => 'chatbot',
        p_config              => v_config,
        p_welcome_message     => 'Hola, ¿en qué puedo ayudarte hoy?',
        p_label               => 'WEB-BOT-01',
        p_label_color         => '#ff6347',
        p_max_users           => 500,
        p_is_active_rag       => TRUE,
        p_is_active_alerts    => FALSE,
        p_is_active_insight   => TRUE,
        io_product_id         => new_product_id 
    );
    
    RAISE NOTICE 'ID del Producto Creado: %', new_product_id;
    
END $$;

CALL spu_minddash_app_update_product(
    p_product_id          => '1ee67952-ef83-4038-ae9d-d95d2f16c32e', -- Reemplazar con ID de Producto existente
    p_project_id          => 'a6f38618-4308-4dfc-83d7-4f98651649c1', -- Reemplazar con ID de Proyecto válido
    p_name                => 'Chatbot de Soporte Web (Producción)',
    p_description         => 'Asistente para la web principal, ahora en producción estable.',
    p_language            => 'es',
    p_tipo                => 'chatbot',
    p_config              => '{"model": "gpt-4o", "temperature": 0.8}'::jsonb, -- Cambiar configuración
    p_welcome_message     => '¡Bienvenido! ¿Cómo puedo asistirte?',
    p_label               => 'WEB-PROD-01',
    p_label_color         => '#1e90ff',
    p_max_users           => 1000,
    p_is_active           => TRUE,
    p_is_active_rag       => TRUE,
    p_is_active_alerts    => TRUE,
    p_is_active_insight   => TRUE
);

CALL spu_minddash_app_delete_product(
    p_product_id => '1ee67952-ef83-4038-ae9d-d95d2f16c32e' -- Reemplazar con el ID del producto a eliminar
);

select * from products
where id='faeebf31-030e-49b6-9a32-8ef70dbdd163';

select * from products p where id='1ee67952-ef83-4038-ae9d-d95d2f16c32e'



-- =======================================================
-- Generar Accesos Nivel Organizacion
-- =======================================================

SELECT * FROM roles r ;
-- a6f996d3-1911-4818-b22a-3870127cad69	SuperAdmin
-- ee7376a8-d934-4936-91fa-2bda2949b5b8	Admin

select * from users u;

select * from organizations;


DO $$
DECLARE 
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'a6f996d3-1911-4818-b22a-3870127cad69';
	v_organization UUID := 'deb385a8-ea08-4d9e-99b5-0952e0a0d971';
    v_access_id_temp UUID;
BEGIN
    RAISE NOTICE '--- 1. Asignando SuperAdmin (Cesar) a Organización ---';

    -- NOTA: Los argumentos deben coincidir en orden con la definición del SP
    CALL spu_minddash_app_insert_user_org_access(
        v_user,             -- 1. p_user_id
        v_organization,     -- 2. p_organization_id
        v_role,             -- 3. p_role_id
        v_access_id_temp    -- 4. io_access_id (INOUT)
    );
    
    RAISE NOTICE '✅ Acceso Org creado: %', v_access_id_temp;
END $$;

DO $$
DECLARE 
    -- Variables de IDs de ejemplo (asumidas existentes)
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'ee7376a8-d934-4936-91fa-2bda2949b5b8';
	v_organization UUID := 'deb385a8-ea08-4d9e-99b5-0952e0a0d971';
    v_access_id_temp UUID := 'dc55acdd-1089-4000-a4d0-cbee4bf4e93e';
BEGIN
    RAISE NOTICE '--- 1. Asignando SuperAdmin (Cesar) a TODAS las Organizaciones ---';

    -- 1. Gestión Patrimonial Segura
     CALL spu_minddash_app_update_user_org_access(
        p_access_id 		:= v_access_id_temp,           
        p_user_id 			:= v_user,                         
        p_organization_id 	:= v_organization,         
        p_role_id 		:= v_role                   
    );
    RAISE NOTICE 'Acceso ID % actualizado', v_access_id_temp;
END $$;

CALL spu_minddash_app_delete_user_org_access(
    p_access_id => 'ff38b022-fcfc-4e3e-9130-c366891f3ceb' -- Reemplazar con el ID del producto a eliminar
);


select * from access_user_organization auo
where id='ff38b022-fcfc-4e3e-9130-c366891f3ceb';
--deb385a8-ea08-4d9e-99b5-0952e0a0d971

-- =======================================================
-- Registro y Actualizacion de Alertas
-- =======================================================

SELECT * FROM "products";

DO $$
DECLARE
    -- 1. Declara la variable para capturar la salida (el nuevo ID)
    v_new_id UUID; 
BEGIN
    -- 2. Llama al procedimiento, asignando los valores por nombre
    CALL spu_minddash_app_insert_alerta(
        p_product_id := '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3', -- Reemplaza con un UUID real
        p_prompt_alerta := 'Monitorear la BD cada 10 minutos',
        p_codigo_cron := '*/10 * * * *',
        new_alerta_id := v_new_id, -- El parámetro OUT se enlaza a la variable
        p_flg_habilitado := FALSE,
        p_fecha_inicio := '2025-11-01 00:00:00+00',
        p_fecha_fin := NULL
    );
    
    -- 3. Usa o muestra el resultado capturado
    RAISE NOTICE 'Alerta creada con ID: %', v_new_id;
END $$;

-- Ejemplo 2: Cambiar solo el prompt de la alerta
CALL spu_minddash_app_update_alerta(
    p_id    => '17356355-5049-437b-ad31-24abae406a95'::UUID,        
	p_product_id    => '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3'::UUID,
    p_prompt_alerta => 'Nuevo prompt actualizado para verificar logs de error.'::TEXT -- <--- Sin (1500)
);

-- Ejemplo: Eliminar una alerta específica por su ID
CALL spu_minddash_app_delete_alerta(
    p_id=> '17356355-5049-437b-ad31-24abae406a95' -- Reemplaza con el ID real de la alerta que quieres borrar
);


{
  "id": "17c03358-ebad-4818-b9e5-6d5c0b758787",
  "product_id": "72a7c5c5-dcbb-4f08-8016-ae1ca63230a3",
  "prompt_alerta": "Ejecutar proceso de cierre de día para Perú.",
  "codigo_cron": "33 15 * * *",
  "session_id": "sess_alerta_3_20pm",
  "flg_habilitado": true
}


SELECT 
    id, product_id, prompt_alerta, codigo_cron, session_id id
FROM 
    alerts_prompts 
WHERE 
    flg_habilitado = TRUE;

SELECT * FROM alerts_prompts where id = '17c03358-ebad-4818-b9e5-6d5c0b758787'

-- =======================================================
-- Generar Accesos Nivel Proyectos
-- =======================================================

SELECT * FROM roles r ;
-- a6f996d3-1911-4818-b22a-3870127cad69	SuperAdmin
-- ee7376a8-d934-4936-91fa-2bda2949b5b8	Admin

select * from users u;

select * from projects p 
-- a6f38618-4308-4dfc-83d7-4f98651649c1


DO $$
DECLARE 
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'a6f996d3-1911-4818-b22a-3870127cad69';
	v_product UUID := 'a6f38618-4308-4dfc-83d7-4f98651649c1';
    v_access_id_temp UUID;
BEGIN
    RAISE NOTICE '--- 1. Asignando SuperAdmin (Cesar) a Organización ---';

    -- NOTA: Los argumentos deben coincidir en orden con la definición del SP
    CALL spu_minddash_app_insert_user_project_access(
        v_user,             -- 1. p_user_id
        v_product,     -- 2. p_organization_id
        v_role,             -- 3. p_role_id
        v_access_id_temp    -- 4. io_access_id (INOUT)
    );
    
    RAISE NOTICE '✅ Acceso Org creado: %', v_access_id_temp;
END $$;

-- Acceso Org creado: f651b767-8d81-436b-ae34-756785fea3e8

DO $$
DECLARE 
    -- Variables de IDs de ejemplo (asumidas existentes)
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'ee7376a8-d934-4936-91fa-2bda2949b5b8';
	v_product UUID := 'a6f38618-4308-4dfc-83d7-4f98651649c1';
    v_access_id_temp UUID := '46e9203c-1d10-4285-82c8-6be3ab91b3e0';
BEGIN
    RAISE NOTICE '--- 1. Asignando SuperAdmin (Cesar) a TODAS las Organizaciones ---';

    -- 1. Gestión Patrimonial Segura
     CALL spu_minddash_app_update_user_project_access(
        p_access_id 		:= v_access_id_temp,           
        p_user_id 			:= v_user,                         
        p_product_id 	:= v_product,         
        p_role_id 		:= v_role                   
    );
    RAISE NOTICE 'Acceso ID % actualizado', v_access_id_temp;
END $$;

CALL spu_minddash_app_delete_user_project_access(
    p_access_id => '46e9203c-1d10-4285-82c8-6be3ab91b3e0' -- Reemplazar con el ID del producto a eliminar
);


select * from access_user_project aup 
where id='46e9203c-1d10-4285-82c8-6be3ab91b3e0';

-- =======================================================
-- Generar Accesos Nivel Productos
-- =======================================================

SELECT * FROM roles r ;
-- a6f996d3-1911-4818-b22a-3870127cad69	SuperAdmin
-- ee7376a8-d934-4936-91fa-2bda2949b5b8	Admin
select * from users u;
select * from products p;
-- 72a7c5c5-dcbb-4f08-8016-ae1ca63230a3

DO $$
DECLARE 
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'a6f996d3-1911-4818-b22a-3870127cad69';
	v_product UUID := '6a3de6f7-c878-41e5-a710-6e44881c5cef';
    v_access_id_temp UUID;
BEGIN
    RAISE NOTICE '--- 1. Asignando SuperAdmin (Cesar) a Organización ---';

    -- NOTA: Los argumentos deben coincidir en orden con la definición del SP
    CALL spu_minddash_app_insert_user_prd_access(
        v_user,
        v_product,    
        v_role,           
        v_access_id_temp    
    );
    
    RAISE NOTICE 'Acceso Org creado: %', v_access_id_temp;
END $$;
--
-- Acceso Org creado: 2640aaa1-2149-48e4-8ed9-cd30c6a0e32a


DO $$
DECLARE 
    -- Variables de IDs de ejemplo (asumidas existentes)
    v_user UUID := '8fad0ddd-83bb-4a25-8c2b-e7c4da4365f3';
    v_role UUID := 'ee7376a8-d934-4936-91fa-2bda2949b5b8';
	v_product UUID := '6a3de6f7-c878-41e5-a710-6e44881c5cef';
    v_access_id_temp UUID := '2640aaa1-2149-48e4-8ed9-cd30c6a0e32a';
BEGIN
    RAISE NOTICE '--- 1. Asignando Rol a Producto (Actualizando) ---';

     CALL spu_minddash_app_update_user_prd_access(
        p_access_id 		:= v_access_id_temp,           
        p_user_id 			:= v_user,                         
        p_product_id 	    := v_product,         -- 🟢 CORRECCIÓN AQUÍ: p_product_id
        p_role_id 		    := v_role                   
    );
    RAISE NOTICE '✅ Acceso ID % actualizado.', v_access_id_temp;
END $$;

CALL spu_minddash_app_delete_user_prd_access(
    p_access_id => '2640aaa1-2149-48e4-8ed9-cd30c6a0e32a' -- Reemplazar con el ID del producto a eliminar
);


select * from access_user_product aup 
where id='af146a74-2aa8-4da7-bdb8-8c69723d5a2c';



-- =======================================================
-- Generar Prompts
-- =======================================================

select 
	*
from  products

DO $$
DECLARE 
    -- REEMPLAZAR con un UUID EXISTENTE de la tabla 'products'
    v_product_id_test UUID := '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3';
    v_prompt_id_new UUID;
    v_name_initial VARCHAR(255) := 'Prompt Inicial';
BEGIN
    
    -- ** ASUME QUE LOS UUIDS SON VÁLIDOS PARA EVITAR ERRORES DE FK **

    -- 1. INSERCIÓN
    RAISE NOTICE E'\n--- INICIO: PRUEBA INSERT ---';
    CALL spu_minddash_app_insert_prompt(
        p_product_id => v_product_id_test,
        p_name => v_name_initial,
        p_config_prompt => '{"model": "gpt-4"}',
        p_path_config_file => '/configs/prompt_v1.json',
        new_prompt_id => v_prompt_id_new
    );
    RAISE NOTICE 'Insertado. Nuevo Prompt ID: %', v_prompt_id_new;
END $$;

DO $$
DECLARE 
    -- REEMPLAZAR con un UUID EXISTENTE de la tabla 'products'
    v_product_id_test UUID := '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3';
    v_prompt_id_new UUID:= '44e650ac-95a1-40e6-b6c3-d8911fa9cdf2';
    v_name_updated VARCHAR(255) := 'Prompt Actualizado por PUT v2';
BEGIN
    
    -- 2. ACTUALIZACIÓN (Solo el nombre)
    RAISE NOTICE E'\n--- INICIO: PRUEBA UPDATE ---';
    CALL spu_minddash_app_update_prompt(
        p_id => v_prompt_id_new,
        p_name => v_name_updated
        -- Los demás campos (product_id, config_prompt, path_config_file) se dejan NULL y no cambian
    );
    RAISE NOTICE '✅ ctualizado. Nuevo nombre: %', v_name_updated;
END $$;

   

-- 3. ELIMINACIÓN
CALL spu_minddash_app_delete_prompt(p_id => '44e650ac-95a1-40e6-b6c3-d8911fa9cdf2');

select * from prompts where id='44e650ac-95a1-40e6-b6c3-d8911fa9cdf2'

-- ------------------------------------------
-- Gestion de Ejemplos 
-- ------------------------------------------

select * from products p ;

DO $$
DECLARE 
    -- ... (UUID y nombres omitidos por brevedad)
    v_example_id_new UUID;
    v_name_initial VARCHAR(200) := 'Ejemplo Inicial de Pruebas';
	v_product_id_test UUID := '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3';     
	v_description_test VARCHAR(200) := 'Descripción inicial para el test.';
    v_query_sql TEXT := 'SELECT region, sum(sales) FROM transactions WHERE date > current_date - interval ''1 month'' GROUP BY region'; 
BEGIN
    
    --------------------------------------------------
    -- 1. INSERCIÓN (spu_minddash_app_insert_example)
    --------------------------------------------------
    RAISE NOTICE E'\n--- INICIO: PRUEBA INSERT ---';
    
    CALL spu_minddash_app_insert_example(
        p_product_id    => v_product_id_test,
        p_name          => v_name_initial,
        p_description   => v_description_test,
        p_data_query    => v_query_sql,
        new_example_id  => v_example_id_new 
    );
    
    RAISE NOTICE 'Insertado. Nuevo Example ID: %', v_example_id_new;

END $$;


DO $$
DECLARE 
    -- ... (UUID y nombres omitidos por brevedad)
    v_example_id_new UUID:= '28ee4346-f397-4607-85ff-f83fdb56b293';
    v_name_initial VARCHAR(200) := 'Ejemplo Inicial de Pruebas';
	v_product_id_test UUID := '72a7c5c5-dcbb-4f08-8016-ae1ca63230a3';     
	v_description_test VARCHAR(200) := 'Descripción inicial para el test v2.';
    v_query_sql TEXT := 'SELECT region, sum(sales) FROM transactions WHERE date > current_date - interval ''1 month'' GROUP BY region'; 
BEGIN
    
    --------------------------------------------------
    -- 1. INSERCIÓN (spu_minddash_app_insert_example)
    --------------------------------------------------
    RAISE NOTICE E'\n--- INICIO: PRUEBA INSERT ---';
    
    CALL spu_minddash_app_update_example(
		p_id			=> v_example_id_new,
        p_product_id    => v_product_id_test,
        p_name          => v_name_initial,
        p_description   => v_description_test,
        p_data_query    => v_query_sql
    );
    
    RAISE NOTICE 'Insertado. Nuevo Example ID: %', v_example_id_new;

END $$;


CALL spu_minddash_app_delete_example(
    p_id => '28ee4346-f397-4607-85ff-f83fdb56b293' -- Eliminamos el registro que acabamos de actualizar
);

--Insertado. Nuevo Example ID: 28ee4346-f397-4607-85ff-f83fdb56b293

select * from examples where id='2209cb4b-a09e-464f-b367-87838d948c23'
-- ------------------------------------------
-- Prueba de Tabla Deploy
-- ------------------------------------------

DO $$
DECLARE
    new_deploy_id UUID;
    v_product_id UUID := 'b7f3d5e8-1c4b-4a9f-8d2c-7e6a5f4d3b2a'; -- ¡REEMPLAZA CON UN PRODUCT_ID VÁLIDO!
BEGIN
    -- Llamar al procedimiento de inserción
    CALL spu_minddash_app_insert_client_product_deploy(
        p_new_id => new_deploy_id,                 -- Parámetro OUT para capturar el ID
        p_product_id => v_product_id,
        p_bucket_config => 'config_bucket_test',
        p_gs_examples_agent => 'gs://agents/v1/examples',
        p_gs_prompt_agent => 'gs://agents/v1/prompt',
        p_gs_prompt_sql => 'gs://agents/v1/prompt_sql',
        p_gs_profiling_agent => 'gs://agents/v1/profiling',
        p_gs_metrics_config_agent => 'gs://agents/v1/metrics',
        p_client => 'Cliente de Prueba 1'
    );

    -- Imprimir el nuevo ID para usarlo en las siguientes pruebas
    RAISE NOTICE '✅ Nuevo ID de Despliegue insertado: %', new_deploy_id;
END $$;

DO $$
DECLARE
    existing_deploy_id UUID := 'C0DE1234-5678-ABCD-EF01-23456789ABCD'; -- ¡USA UN ID VÁLIDO DE TU TABLA!
    v_product_id UUID := 'b7f3d5e8-1c4b-4a9f-8d2c-7e6a5f4d3b2a'; -- ¡DEBE SER UN PRODUCT_ID VÁLIDO!
BEGIN
    -- Llamar al procedimiento de actualización
    CALL spu_minddash_app_update_client_product_deploy(
        p_id => existing_deploy_id,
        p_product_id => v_product_id,
        p_bucket_config => 'config_bucket_test_UPDATED', -- Valor actualizado
        p_gs_examples_agent => 'gs://agents/v2/examples',
        p_gs_prompt_agent => 'gs://agents/v2/prompt',
        p_gs_prompt_sql => 'gs://agents/v2/prompt_sql',
        p_gs_profiling_agent => 'gs://agents/v2/profiling',
        p_gs_metrics_config_agent => 'gs://agents/v2/metrics',
        p_client => 'Cliente de Prueba 1 - Actualizado'
    );

    RAISE NOTICE '✅ Procedimiento de actualización ejecutado para ID: %', existing_deploy_id;
END $$;


DO $$
DECLARE
    deploy_id_to_delete UUID := 'C0DE1234-5678-ABCD-EF01-23456789ABCD'; -- ¡USA UN ID VÁLIDO DE TU TABLA!
BEGIN
    -- Llamar al procedimiento de eliminación
    CALL spu_minddash_app_delete_client_product_deploy(
        p_id => deploy_id_to_delete
    );

    RAISE NOTICE '✅ Procedimiento de eliminación ejecutado para ID: %', deploy_id_to_delete;
END $$;

-- Puedes verificar la eliminación con:
-- SELECT * FROM clients_products_deploys WHERE id = 'C0DE1234-5678-ABCD-EF01-23456789ABCD'; -- Debe retornar 0 filas

-- Puedes verificar el resultado con:
-- SELECT * FROM clients_products_deploys WHERE id = 'C0DE1234-5678-ABCD-EF01-23456789ABCD';

-- ------------------------------------------
-- Prueba de Semantic Layers
-- ------------------------------------------

select * from products;

-- 1. Declarar una variable para capturar el nuevo ID
DO $$
DECLARE
    new_semantic_config_id UUID;
    v_product_id UUID := '6a3de6f7-c878-41e5-a710-6e44881c5cef'; -- ¡REEMPLAZA CON UN PRODUCT_ID REAL!
BEGIN
    -- 2. Llamar al procedimiento de inserción
    CALL spu_minddash_app_insert_role_semantic_layer(
        p_new_id => new_semantic_config_id,          -- Parámetro OUT para capturar el ID
        p_product_id => v_product_id,
        p_object_path_saved => 'semantic_layers/test/config_v1.yaml',
        p_bucket_name_saved => 'mindash_saved_bucket',
        p_object_path_deployed => NULL,              -- Omitimos, o ponemos NULL
        p_bucket_name_deployed => NULL
    );

    -- 3. Imprimir el nuevo ID para usarlo en la prueba de actualización/borrado
    RAISE NOTICE 'Nuevo ID de configuración insertado: %', new_semantic_config_id;
END $$;

-- 1. Definir el ID que deseas actualizar (Reemplaza con un ID REAL)
DO $$
DECLARE
    existing_config_id UUID := '543414f5-5f98-46c7-a000-3b01c7a2401a'; -- ¡USA UN ID VÁLIDO DE TU TABLA!
    v_product_id UUID := '6a3de6f7-c878-41e5-a710-6e44881c5cef'; -- ¡REEMPLAZA CON UN PRODUCT_ID REAL!
BEGIN
    -- 2. Llamar al procedimiento de actualización
    CALL spu_minddash_app_update_role_semantic_layer(
        p_id => existing_config_id,
        p_product_id => v_product_id,
        p_object_path_saved => 'semantic_layers/test/config_v1_UPDATED.yaml', -- Nuevo valor
        p_bucket_name_saved => 'mindash_saved_bucket',
        p_object_path_deployed => 'semantic_layers/prod/config_v1_DEPLOYED.yaml', -- Ahora desplegado
        p_bucket_name_deployed => 'mindash_deployed_prod_saved'
    );

    RAISE NOTICE 'Procedimiento de actualización ejecutado para ID: %', existing_config_id;
END $$;


-- 1. Definir el ID que deseas eliminar (Reemplaza con un ID REAL)
DO $$
DECLARE
    config_id_to_delete UUID := '543414f5-5f98-46c7-a000-3b01c7a2401a'; -- ¡USA UN ID VÁLIDO DE TU TABLA!
BEGIN
    -- 2. Llamar al procedimiento de eliminación
    CALL spu_minddash_app_delete_role_semantic_layer(
        p_id => config_id_to_delete
    );

    RAISE NOTICE 'Procedimiento de eliminación ejecutado para ID: %', config_id_to_delete;
END $$;

select * from semantic_layer_configs;


-- ------------------------------------------
-- ------
-- ------------------------------------------
ALTER TABLE users
ADD COLUMN IF NOT EXISTS role_id UUID NOT NULL DEFAULT '4648f54f-9139-40a2-96d7-c1ac4e936bbf'::UUID;

CREATE INDEX IF NOT EXISTS idx_users_iam_role ON users(iam_role);

select * from roles r  --- crear endpoint


sele

update users
set	role_id='ee7376a8-d934-4936-91fa-2bda2949b5b8'
where email  in ('bayer@bayer.com'
'cintac@cintac.com',
'mecanic@mecánicaexpress.com',
'usuarioadminprueba@test.com',
'restobar@restobarcentral.com',
'lisit@lisit.com',
'minddash@minddashanalytics.com')


select * from view_list_organizations;

select * from view_list_projects;

select * from view_list_products;

DO $$
DECLARE 
    -- IDs de ejemplo (deben existir en sus respectivas tablas)
    v_user_id UUID := '45fd8678-a7f4-4547-9bd7-499ac951cab3'; -- Cesar SuperAdmin
    v_project_id UUID := 'a6f38618-4308-4dfc-83d7-4f98651649c1'; -- ERP Cloud Migration
    v_role_project_manager_id UUID := 'b80e722c-a0b5-41e9-98e3-08573428d0e1'; -- Rol de Project Manager (ejemplo)
    v_access_id_temp UUID;
BEGIN
    RAISE NOTICE '--- 2. Ejemplo de Asignación de Project Manager a un Proyecto ---';

    CALL create_user_project_access(
        p_user_id := v_user_id,
        p_project_id := v_project_id,
        p_role_id := v_role_project_manager_id,
        io_access_id := v_access_id_temp
    );

    RAISE NOTICE 'Acceso Project creado con ID: %', v_access_id_temp;

END $$;



DO $$
DECLARE 
    -- IDs de ejemplo (deben existir en sus respectivas tablas)
    v_user_maria_id UUID := 'c2f1c8a9-b3e7-4c0a-9d2f-4a3b5c6d7e8f';
    v_product_id UUID := '94e45d39-2f35-440e-a103-3b8c652c2d83'; -- Portfolio Q&A
    v_role_editor_id UUID := 'd0a8b9e7-f6c4-4e1b-9a0c-3b4e5f6d7a8b'; -- Rol de Editor (ejemplo)
    v_access_id_temp UUID;
BEGIN
    RAISE NOTICE '--- 3. Ejemplo de Asignación de Editor a un Producto ---';

    CALL create_user_product_access(
        p_user_id := v_user_maria_id,
        p_product_id := v_product_id,
        p_role_id := v_role_editor_id,
        p_data_role_id := NULL, -- Sin Data Role ID por ahora
        io_access_id := v_access_id_temp
    );

    RAISE NOTICE 'Acceso Product creado con ID: %', v_access_id_temp;

END $$;


-- =======================================================
-- Conexion a Datos
-- =======================================================

DO $$ 
DECLARE 
    v_org_id UUID := 'e7c77bdf-8f8e-438c-b038-5ea9253e0ad7'; -- ID de una organización existente (ej. SoftDev Solutions)
    v_new_connection_id UUID;
BEGIN
    CALL create_data_connection(
        p_organization_id := v_org_id,
        p_name := 'Postgres_Warehouse',
        p_type := 'PostgreSQL',
        p_configuration := '{"host": "db.corp.local", "user": "read_only", "port": 5432}'::JSONB,
        io_connection_id := v_new_connection_id
    );
    RAISE NOTICE 'Nueva conexión registrada con ID: %', v_new_connection_id;
END $$;


select * from data_connections dc where id='34c51e15-7df8-402a-a262-404a4430a3e1'

select * from organizations o 


-- =======================================================
-- Canales de Chatbot
-- =======================================================

DO $$
DECLARE 
    v_channel_uuid_temp UUID; -- Variable para capturar el UUID generado
BEGIN
    RAISE NOTICE '--- Insertando Canales de Comunicación ---';

    -- 1. WEB
    CALL create_channel(
        p_name := 'Web Chat Widget',
        p_description := 'Chatbot integrado en el sitio web de la organización.',
        io_result_id := v_channel_uuid_temp
    );
    RAISE NOTICE 'Canal "WEB" creado con ID: %', v_channel_uuid_temp;

    -- 2. WHATSAPP
    CALL create_channel(
        p_name := 'WhatsApp Business API',
        p_description := 'Conexión a la plataforma oficial de WhatsApp Business.',
        io_result_id := v_channel_uuid_temp
    );
    RAISE NOTICE 'Canal "WHATSAPP" creado con ID: %', v_channel_uuid_temp;

    -- 3. MICROSOFT TEAMS (El que faltaba)
    CALL create_channel(
        p_name := 'Microsoft Teams App',
        p_description := 'Aplicación para integrar el chatbot en Microsoft Teams.',
        io_result_id := v_channel_uuid_temp
    );
    RAISE NOTICE 'Canal "MS Teams" creado con ID: %', v_channel_uuid_temp;
    
    -- 4. SLACK (El que faltaba)
    CALL create_channel(
        p_name := 'Slack Integration',
        p_description := 'Integración del chatbot como una aplicación en Slack.',
        io_result_id := v_channel_uuid_temp
    );
    RAISE NOTICE 'Canal "Slack" creado con ID: %', v_channel_uuid_temp;

    RAISE NOTICE '¡Inserción de los 4 canales completada exitosamente!';
END $$;

---

-- Verificación de los datos insertados
SELECT id, name, description FROM "channels";

-- =======================================================
-- Prompts de Chatbot
-- =======================================================


CALL sp_insert_prompt(
    'a1b2c3d4-e5f6-7890-1234-567890abcdef'::UUID, -- Reemplaza con un product_id existente
    'Prompt de Bienvenida V2',
    '{"temperature": 0.8, "max_tokens": 1024}'::JSONB,
    '/configs/v2/welcome.txt',
    NULL -- Espacio reservado para el valor de salida (new_prompt_id)
);


CALL sp_update_prompt(
    'fedcba98-7654-3210-fedc-ba9876543210'::UUID, -- Reemplaza con un prompt id existente
    p_name := 'Nombre Actualizado por SP',
    p_config_prompt := '{"temperature": 0.9, "max_tokens": 2048}'::JSONB
);


-- =======================================================
-- Metricas de Chatbot
-- =======================================================

CALL sp_insert_metric(
    'a1b2c3d4-e5f6-7890-1234-567890abcdef'::UUID, -- Reemplaza con un product_id existente
    'Tasa de Conversión',
    'Mide el porcentaje de visitantes que completan una compra',
    '{"sql": "SELECT COUNT(*)...", "params": ["conversion"]}'::JSONB,
    NULL -- Espacio reservado para el valor de salida (new_metric_id)
);

CALL sp_update_metric(
    'fedcba98-7654-3210-fedc-ba9876543210'::UUID, -- Reemplaza con un metric id existente
    p_description := 'Métrica actualizada para incluir sesiones móviles.',
    p_data_query := '{"sql": "SELECT COUNT(*)...", "params": ["mobile_sessions"]}'::JSONB
);


-- =======================================================
-- Examples de Chatbot
-- =======================================================

CALL sp_insert_example(
    '1a2b3c4d-5e6f-7080-910a-bcdef0123456'::UUID, -- Reemplaza con un product_id existente
    'Ejemplo de Caso de Uso A',
    'Datos de prueba para el modelo A',
    '{"input": "Describe el producto X", "output": "Es el mejor producto..."}'::JSONB,
    NULL -- Espacio reservado para el valor de salida (new_example_id)
);

CALL sp_update_example(
    '11223344-5566-7788-9900-aabbccddeeff'::UUID, -- Reemplaza con un example id existente
    p_description := 'Descripción revisada y optimizada.',
    p_data_query := '{"input": "Pregunta frecuente V2", "output": "Respuesta revisada"}'::JSONB
);


-- =======================================================
-- Conexion a Datos
-- =======================================================

CALL spu_minddash_app_insert_data_connection(
    p_connection_id := 'e7c77bdf-8f8e-438c-b038-5ea9253e0ad7',
);
