-- =============================================================================
-- MindDash Marketplace - DB Init Script
-- Aplica todas las Views y SPs necesarios sobre las tablas ya existentes.
-- Idempotente: usa CREATE OR REPLACE / DROP IF EXISTS.
-- =============================================================================

-- -----------------------------------------------------------------------
-- VIEWS
-- -----------------------------------------------------------------------

DROP VIEW IF EXISTS view_list_organizations CASCADE;
CREATE VIEW view_list_organizations AS
    WITH organization_access_by_user AS (
        SELECT auo.user_id, auo.organization_id, auo.role_id
        FROM access_user_organization auo
        UNION DISTINCT
        SELECT aup.user_id, p.organization_id, '0bdd08da-f52a-47f9-acea-df709199b687'::uuid role_id
        FROM access_user_project aup
        JOIN projects p ON aup.project_id = p.id
        LEFT JOIN access_user_organization auo ON auo.organization_id = p.organization_id
        WHERE auo.organization_id IS NULL
        UNION DISTINCT
        SELECT aupd.user_id, p.organization_id, '0bdd08da-f52a-47f9-acea-df709199b687'::uuid role_id
        FROM access_user_product aupd
        JOIN products pd ON aupd.product_id = pd.id
        JOIN projects p ON pd.project_id = p.id
        LEFT JOIN access_user_organization auo ON auo.organization_id = p.organization_id
        WHERE auo.organization_id IS NULL
    )
    SELECT DISTINCT
        ua.user_id,
        r.name AS user_role_name,
        u.username AS user_name,
        u.phone_number AS user_phone,
        u.email AS user_email,
        o.id AS organization_id,
        o.name AS organization_name
    FROM organization_access_by_user ua
    JOIN organizations o ON ua.organization_id = o.id
    JOIN users u ON ua.user_id = u.id
    JOIN roles r ON u.role_id = r.id;


DROP VIEW IF EXISTS view_list_projects CASCADE;
CREATE VIEW view_list_projects AS
    WITH project_access_by_user AS (
        SELECT aup.user_id, aup.project_id, aup.role_id
        FROM access_user_project aup
        UNION DISTINCT
        SELECT aupd.user_id, pd.project_id, '0bdd08da-f52a-47f9-acea-df709199b687'::uuid role_id
        FROM access_user_product aupd
        JOIN products pd ON aupd.product_id = pd.id
        LEFT JOIN access_user_project aup ON aup.project_id = pd.project_id
        WHERE aup.project_id IS NULL
    )
    SELECT DISTINCT
        ua.user_id,
        r.name AS user_role_name,
        u.username AS user_name,
        u.phone_number AS user_phone,
        u.email AS user_email,
        o.id AS organization_id,
        o.name AS organization_name,
        p.id AS project_id,
        p.name AS project_name
    FROM project_access_by_user ua
    JOIN projects p ON ua.project_id = p.id
    JOIN organizations o ON p.organization_id = o.id
    JOIN users u ON ua.user_id = u.id
    JOIN roles r ON u.role_id = r.id;


DROP VIEW IF EXISTS view_list_products CASCADE;
CREATE VIEW view_list_products AS
    WITH products_access_by_user AS (
        SELECT aupd.user_id, aupd.product_id, aupd.role_id
        FROM access_user_product aupd
        UNION DISTINCT
        SELECT aup.user_id, pd.id AS product_id, '0bdd08da-f52a-47f9-acea-df709199b687'::uuid role_id
        FROM access_user_project aup
        JOIN products pd ON pd.project_id = aup.project_id
        LEFT JOIN access_user_product aupd ON aupd.product_id = pd.id AND aupd.user_id = aup.user_id
        WHERE aupd.product_id IS NULL
    )
    SELECT DISTINCT
        ua.user_id,
        r.name AS user_role_name,
        u.username AS user_name,
        u.phone_number AS user_phone,
        u.email AS user_email,
        o.id AS organization_id,
        o.name AS organization_name,
        p.id AS project_id,
        p.name AS project_name,
        pd.id AS product_id,
        pd.name AS product_name,
        pd.description AS product_description
    FROM products_access_by_user ua
    JOIN products pd ON ua.product_id = pd.id
    JOIN projects p ON pd.project_id = p.id
    JOIN organizations o ON p.organization_id = o.id
    JOIN users u ON ua.user_id = u.id
    JOIN roles r ON u.role_id = r.id;


DROP VIEW IF EXISTS view_list_products_all CASCADE;
CREATE VIEW view_list_products_all AS
    WITH products_access_by_user AS (
        SELECT
            p.id AS project_id,
            p.name AS project_name,
            o.id AS organization_id,
            o.name AS organization_name,
            pd.id AS product_id,
            pd.name AS product_name,
            pd.description AS product_description
        FROM products pd
        LEFT JOIN projects p ON pd.project_id = p.id
        LEFT JOIN organizations o ON p.organization_id = o.id
    )
    SELECT DISTINCT * FROM products_access_by_user;


DROP VIEW IF EXISTS view_info_user_details CASCADE;
CREATE VIEW view_info_user_details AS
    SELECT
        u.id AS user_id,
        username,
        email,
        password_hash,
        email_verified,
        is_active,
        failed_attempts,
        locked_until,
        u.created_at,
        u.updated_at,
        primary_chatbot_id,
        can_manage_users,
        phone_number,
        is_active_whatsapp,
        role_acceso_data_id,
        r.id AS role_id,
        r.name AS role_name,
        r.type_role AS role_type,
        r.description AS role_description
    FROM users u
    JOIN roles r ON u.role_id = r.id;


-- data_connections no tiene product_id ni company_name/country en organizations
DROP VIEW IF EXISTS view_list_data_connections CASCADE;
CREATE VIEW view_list_data_connections AS
    SELECT
        dc.id AS connection_id,
        dc.name AS connection_name,
        dc.type AS connection_type,
        dc.configuration AS connection_configuration,
        o.name AS organization_name,
        o.id AS organization_id
    FROM data_connections dc
    LEFT JOIN organizations o ON dc.organization_id = o.id
    ORDER BY dc.name;


-- metrics no tiene required_params ni optional_params en esta DB
DROP VIEW IF EXISTS view_list_metrics CASCADE;
CREATE VIEW view_list_metrics AS
    SELECT
        m.id AS metric_id,
        m.name AS metric_name,
        m.description AS metric_description,
        m.data_query AS metric_data_query,
        m.product_id,
        p.name AS product_name
    FROM metrics m
    LEFT JOIN products p ON m.product_id = p.id
    ORDER BY m.name;


DROP VIEW IF EXISTS view_list_roles_data_access CASCADE;
CREATE VIEW view_list_roles_data_access AS
    SELECT
        rda.id AS role_id,
        rda.name AS role_name,
        rda.table_names AS role_table_names,
        rda.data_access AS role_data_access,
        rda.metrics_access AS role_metrics_access,
        rda.product_id,
        p.name AS product_name,
        rda.created_at,
        rda.updated_at
    FROM roles_data_access rda
    LEFT JOIN products p ON rda.product_id = p.id
    ORDER BY rda.name;


DROP VIEW IF EXISTS view_list_user_data_access CASCADE;
CREATE VIEW view_list_user_data_access AS
    SELECT
        uda.id AS user_data_access_id,
        uda.role_data_id,
        rda.name AS role_name,
        uda.user_id,
        u.username AS user_name,
        u.email AS user_email,
        uda.table_names AS user_table_names,
        uda.data_access AS user_data_access,
        uda.metrics_access AS user_metrics_access,
        uda.created_at,
        uda.updated_at
    FROM user_data_access uda
    LEFT JOIN roles_data_access rda ON uda.role_data_id = rda.id
    LEFT JOIN users u ON uda.user_id = u.id
    ORDER BY uda.created_at DESC;


DROP VIEW IF EXISTS view_info_prompt_product CASCADE;
CREATE VIEW view_info_prompt_product AS
    SELECT
        p.id AS prompt_id,
        p.name AS prompt_name,
        p.config_prompt,
        p.path_config_file,
        prd.id AS product_id,
        prd.name,
        prd.description
    FROM prompts p
    JOIN products prd ON p.product_id = prd.id;


-- clients_products_deploys no tiene gs_semantic_config en esta DB
DROP VIEW IF EXISTS view_info_to_agent CASCADE;
CREATE VIEW view_info_to_agent AS
    SELECT
        vlp.user_id,
        vlp.user_name,
        vlp.product_id,
        vlp.product_name,
        vlp.organization_id,
        vlp.organization_name,
        vlp.project_id,
        vlp.project_name,
        u.email,
        u.is_active_whatsapp,
        u.phone_number,
        rda.name AS name_rol_datos,
        array_remove(COALESCE(uda.table_names, ARRAY[]::text[]) || COALESCE(rda.table_names, ARRAY[]::text[]), '') AS tables_name,
        COALESCE(uda.metrics_access, '{}'::JSONB) || COALESCE(rda.metrics_access, '{}'::JSONB) AS metrics_access,
        COALESCE(uda.data_access, '{}'::JSONB) || COALESCE(rda.data_access, '{}'::JSONB) AS data_access,
        cpd.bucket_config,
        cpd.gs_examples_agent,
        cpd.gs_profiling_agent,
        cpd.gs_metrics_config_agent,
        cpd.gs_prompt_agent,
        cpd.gs_prompt_sql,
        cpd.client,
        dc.configuration::jsonb || jsonb_build_object('id', dc.id, 'engine', dc.type) AS config_connection,
        json_build_object('rag_active', p.is_active_rag) AS search_knowledge_config
    FROM view_list_products vlp
    LEFT JOIN user_data_access uda ON uda.user_id = vlp.user_id
    LEFT JOIN roles_data_access rda ON rda.id = uda.role_data_id AND vlp.product_id = rda.product_id
    LEFT JOIN clients_products_deploys cpd ON vlp.product_id = cpd.product_id
    LEFT JOIN users u ON vlp.user_id = u.id
    LEFT JOIN products AS p ON p.id = vlp.product_id
    LEFT JOIN data_connections dc ON dc.organization_id = vlp.organization_id
    WHERE
        cpd.id IS NOT NULL
        AND rda.id IS NOT NULL
        AND u.is_active = TRUE;


DROP VIEW IF EXISTS view_info_products_channels CASCADE;
CREATE VIEW view_info_products_channels AS
    SELECT
        prd.id,
        prd.name,
        p.organization_id,
        p.id AS project_id,
        ch.name AS name_channel,
        chp.configuration AS configuration_channel
    FROM products prd
    JOIN projects p ON prd.project_id = p.id
    LEFT JOIN channel_product chp ON chp.product_id = prd.id
    LEFT JOIN channels ch ON chp.channel_id = ch.id;


-- -----------------------------------------------------------------------
-- STORED PROCEDURES - productos (insert es el crítico, los demás ya existen)
-- -----------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_product(
    p_project_id UUID,
    p_name VARCHAR(200),
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
    INOUT io_product_id UUID DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id) THEN
        RAISE EXCEPTION 'ERROR: El proyecto con ID % no existe. No se puede crear el producto.', p_project_id;
    END IF;
    io_product_id := uuid_generate_v4();
    INSERT INTO products (
        id, project_id, name, description, language, tipo, config,
        welcome_message, label, label_color, max_users,
        is_active_rag, is_active_alerts, is_active_insight, updated_at
    ) VALUES (
        io_product_id, p_project_id, p_name, p_description, p_language,
        p_tipo, p_config, p_welcome_message, p_label, p_label_color,
        p_max_users, p_is_active_rag, p_is_active_alerts, p_is_active_insight,
        CURRENT_TIMESTAMP
    );
END;
$$;


-- -----------------------------------------------------------------------
-- TABLAS FALTANTES (schema drift dev→marketplace)
-- Creadas con IF NOT EXISTS: seguro correr múltiples veces.
-- -----------------------------------------------------------------------

-- Usada por el RAG API (middleware de validación de cuota de storage).
-- Si está vacía, el middleware permite el acceso por defecto (comportamiento correcto).
CREATE TABLE IF NOT EXISTS metric_configurations_quota (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metrics_name VARCHAR(200) NOT NULL,
    level VARCHAR(50) NOT NULL,
    organization_id UUID NOT NULL,
    dimension VARCHAR(100) NOT NULL,
    quota NUMERIC(18,2) NOT NULL
);

-- Usada por el RAG API para trackear documentos subidos por producto.
CREATE TABLE IF NOT EXISTS rag_uploaded_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL,
    filename VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    uri VARCHAR NOT NULL,
    size BIGINT DEFAULT 0,
    status VARCHAR DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);

-- -----------------------------------------------------------------------
-- BILLING SPs
-- -----------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE spu_billing_insert_plan(
    p_plan_name VARCHAR(255),
    p_description TEXT DEFAULT NULL,
    INOUT io_plan_id UUID DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    io_plan_id := uuid_generate_v4();
    INSERT INTO plans (id, plan_name, description, created_at, updated_at)
    VALUES (io_plan_id, p_plan_name, p_description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
END;
$$;

-- -----------------------------------------------------------------------
-- SEMANTIC LAYER (schema drift: tabla no existía en marketplace DB)
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS semantic_layer_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL,
    object_path_saved VARCHAR(255) NOT NULL,
    bucket_name_saved VARCHAR(255) NOT NULL,
    object_path_deployed VARCHAR(255) NULL,
    bucket_name_deployed VARCHAR(255) NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT products_semantic_layer_configs_fkey FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Garantizar columnas por si la tabla existía con schema viejo (idempotente)
ALTER TABLE semantic_layer_configs
  ADD COLUMN IF NOT EXISTS object_path_saved VARCHAR(255),
  ADD COLUMN IF NOT EXISTS bucket_name_saved VARCHAR(255),
  ADD COLUMN IF NOT EXISTS object_path_deployed VARCHAR(255),
  ADD COLUMN IF NOT EXISTS bucket_name_deployed VARCHAR(255),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE OR REPLACE PROCEDURE spu_minddash_app_insert_role_semantic_layer(
    OUT p_new_id UUID,
    IN p_product_id UUID,
    IN p_object_path_saved VARCHAR,
    IN p_bucket_name_saved VARCHAR,
    IN p_object_path_deployed VARCHAR DEFAULT NULL,
    IN p_bucket_name_deployed VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO semantic_layer_configs (
        product_id, object_path_saved, bucket_name_saved,
        object_path_deployed, bucket_name_deployed, updated_at
    ) VALUES (
        p_product_id, p_object_path_saved, p_bucket_name_saved,
        p_object_path_deployed, p_bucket_name_deployed, CURRENT_TIMESTAMP
    )
    RETURNING id INTO p_new_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_minddash_app_delete_role_semantic_layer(
    IN p_id UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM semantic_layer_configs WHERE id = p_id;
    IF NOT FOUND THEN
        RAISE WARNING 'No se encontró un registro con ID % para eliminar.', p_id;
    END IF;
END;
$$;

-- -----------------------------------------------------------------------
-- FIN
-- -----------------------------------------------------------------------
