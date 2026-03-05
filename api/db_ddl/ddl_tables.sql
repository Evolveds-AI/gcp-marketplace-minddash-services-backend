-- #############################################################################
-- ## Script DDL para Mindash Agent DB
-- ## Base de Datos: PostgreSQL
-- ##
-- ## Nota: PostgreSQL no tiene 'CREATE OR REPLACE TABLE'. En su lugar,
-- ## se utiliza 'DROP TABLE IF EXISTS ... CASCADE' para asegurar que el script
-- ## se pueda ejecutar múltiples veces sin errores, eliminando la tabla
-- ## y sus dependencias si ya existen.
-- #############################################################################

-- ------------------------------------------
-- Tablas Principales y de Acceso
-- ------------------------------------------

DROP TABLE IF EXISTS "users" CASCADE;
CREATE TABLE "users" (
	"id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "username" TEXT NOT NULL UNIQUE,
    "email" TEXT UNIQUE,
    "password_hash" TEXT,
    "role_id" UUID NOT NULL,
    "email_verified" BOOLEAN NOT NULL DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "is_active" BOOLEAN NOT NULL DEFAULT true, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "failed_attempts" INTEGER NOT NULL DEFAULT 0, --*/ Tipo de dato ajustado de 'int4' a 'INTEGER'.
    "locked_until" TIMESTAMP(3),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP, --*/ Corregido typo 'tsimestamp' y sintaxis de default.
    "updated_at" TIMESTAMP(3),
    "primary_chatbot_id" VARCHAR(255),
    "can_manage_users" BOOLEAN DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "phone_number" TEXT,
    "is_active_whatsapp" BOOLEAN DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "role_acceso_data_id" UUID,
    "role_id" UUID
);

drop table if exists "organizations" cascade;
CREATE TABLE "organizations" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name"  VARCHAR(50) NOT NULL,
    "company_name"  VARCHAR(100) NOT null,
    "description"  VARCHAR(200),
    "country" VARCHAR(25),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL
 );


DROP TABLE IF EXISTS "projects" CASCADE;
CREATE TABLE "projects" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "organization_id" UUID, --*/ Corregido nombre de columna de 'organizations_id' a 'organization_id' para consistencia.
    "name"  VARCHAR(50) NOT NULL,
    "label" varchar(50),
    "label_color" varchar(20),
    "description"  VARCHAR(200),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "projects_organizations_fkey" FOREIGN KEY("organization_id") REFERENCES "organizations"("id")
);

DROP TABLE IF EXISTS "products" CASCADE;
CREATE TABLE "products" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name"  VARCHAR(200) NOT NULL,
    "project_id" UUID NOT NULL, --*/ Tipo de dato ajustado de 'text' a 'UUID' para coincidir con la llave primaria de 'projects'.
    "is_active" BOOLEAN NOT NULL DEFAULT true, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "description"  VARCHAR(200),
    "language" VARCHAR(50), --*/ Corregido typo de 'lenguage' a 'language'.
    "tipo" VARCHAR(20) NOT NULL DEFAULT 'chatbot', --*/ Limpiada la sintaxis del default.
    "config" JSONB DEFAULT '{}'::jsonb,
    "mensajes_mes" INTEGER DEFAULT 0, --*/ Tipo de dato ajustado de 'int4' a 'INTEGER'.
    "welcome_message" varchar(100),
    "label" varchar(50),
    "label_color" varchar(20),
    "max_users" INTEGER DEFAULT 100, --*/ Tipo de dato ajustado de 'int4' a 'INTEGER'.
    "is_active_rag" BOOLEAN NOT NULL DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "is_active_alerts" BOOLEAN NOT NULL DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.
    "is_active_insight" BOOLEAN NOT NULL DEFAULT false, --*/ Tipo de dato ajustado de 'bool' a 'BOOLEAN'.

    CONSTRAINT "PRODUCT_projects_fkey" FOREIGN KEY("project_id") REFERENCES "projects"("id")
);
CREATE INDEX "idx_product_tipo" ON "products"("tipo");


DROP TABLE IF EXISTS "roles" CASCADE;
CREATE TABLE "roles" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "name" VARCHAR(50),
    "type_role" VARCHAR(50),
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3)
);

DROP TABLE IF EXISTS "access_user_organization" CASCADE; --*/ Corregido typo en nombre de tabla 'cliens' a 'organizations'.
CREATE TABLE "access_user_organization" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "user_id" UUID,
    "organization_id" UUID,
    "role_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3),

    CONSTRAINT "users_roles_fkey" FOREIGN KEY("user_id") REFERENCES "users"("id"),
    CONSTRAINT "organization_roles_fkey" FOREIGN KEY("organization_id") REFERENCES "organizations"("id"),
    CONSTRAINT "roles_organization_fkey" FOREIGN KEY("role_id") REFERENCES "roles"("id")

);

DROP TABLE IF EXISTS "access_user_project" CASCADE;
CREATE TABLE "access_user_project" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "user_id" UUID,
    "project_id" UUID, --*/ Se renombró 'organization_id' a 'project_id' para reflejar que se relaciona con la tabla 'projects'.
    "role_id" UUID,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3),

    CONSTRAINT "users_roles_users_projects_fkey" FOREIGN KEY("user_id") REFERENCES "users"("id"),
    CONSTRAINT "projects_roles_users_projects_fkey" FOREIGN KEY("project_id") REFERENCES "projects"("id"),
    CONSTRAINT "roles_project_fkey" FOREIGN KEY("role_id") REFERENCES "roles"("id")
);

DROP TABLE IF EXISTS "access_user_product" CASCADE;
CREATE TABLE "access_user_product" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "user_id" UUID NOT NULL, --*/ Tipo de dato ajustado de 'text' a 'UUID' para coincidir con la llave primaria de 'users'.
    "product_id" UUID NOT NULL, --*/ Tipo de dato ajustado de 'text' a 'UUID' para coincidir con la llave primaria de 'products'.
    "created_at" TIMESTAMP NOT NULL DEFAULT now(),
    "role_id" UUID,
    "updated_at" TIMESTAMP(3),

    CONSTRAINT "user_access_user_fkey" FOREIGN KEY("user_id") REFERENCES "users"("id"),
    CONSTRAINT "user_access_product_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id"),
    CONSTRAINT "roles_product_fkey" FOREIGN KEY("role_id") REFERENCES "roles"("id")
);

DROP TABLE IF EXISTS "message_whatsapp" CASCADE;
CREATE TABLE "message_whatsapp" (
    "id" UUID PRIMARY KEY,
    "text" TEXT,
    "user_id" UUID, --*/ Tipo de dato ajustado de 'text' a 'UUID'. Se recomienda agregar una FK a la tabla 'users'.
    "created_at" TIMESTAMP,
    "updated_at" TIMESTAMP,
    "conversation_id" TEXT,
    "role" TEXT,
    "message_type" TEXT DEFAULT 'text'
);

-- ------------------------------------------
-- Tablas para Flujo de Prompts
-- ------------------------------------------

DROP TABLE IF EXISTS "flujos_prompt" CASCADE;
CREATE TABLE "flujos_prompt" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Tipo de dato cambiado a UUID para consistencia.
    "product_id" UUID, --*/ Tipo de dato cambiado a UUID para coincidir con 'products.id'.
    "response_strategy" VARCHAR(50),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "flujos_de_prompt_product_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")
);

DROP TABLE IF EXISTS "prompts" CASCADE;
CREATE TABLE "prompts" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Tipo de dato cambiado a UUID para consistencia.
    "product_id" UUID,
    "name" VARCHAR(255),
    "config_prompt" JSONB,
    "path_config_file" VARCHAR(255),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "products_prompts_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")
);

-- ------------------------------------------
-- Channel Teams
-- ------------------------------------------

DROP TABLE IF EXISTS "channels" CASCADE;
CREATE TABLE "channels" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Se asignó una longitud (255) al VARCHAR, ya que no tenerla puede ser problemático.
    "name" VARCHAR(100),
    "description" VARCHAR(100),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL
);

DROP TABLE IF EXISTS "channel_product" CASCADE;
CREATE TABLE "channel_product" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Tipo de dato ajustado de 'int' a 'SERIAL' para autoincremento.
    "channel_id" UUID, --*/ Tipo de dato ajustado para coincidir con 'channels.id'.
    "product_id" UUID, --*/ Tipo de dato ajustado de 'varchar' a 'UUID' para coincidir con 'products.id'.
    "configuration" JSONB,

    CONSTRAINT "channel_product_prodpromptsucts_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id"),
    CONSTRAINT "channel_product_channels_fkey" FOREIGN KEY("channel_id") REFERENCES "channels"("id") --*/ Se renombró la FK para evitar duplicados.
);

DROP TABLE IF EXISTS "insight_results" CASCADE;
CREATE TABLE "insight_results" (
    "id" SERIAL PRIMARY KEY, --*/ Tipo de dato ajustado de 'int' a 'SERIAL' para autoincremento.
    "channel_id" VARCHAR(255),
    "product_id" UUID, --*/ Tipo de dato ajustado de 'varchar' a 'UUID' para coincidir con 'products.id'.
    "configuration" JSON,

    CONSTRAINT "insight_results_products_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id") --*/ Se renombró la FK para evitar duplicados y se eliminó la FK a 'channel_id' que no estaba en el diagrama.
);

-- ------------------------------------------
-- Data Source Tables
-- ------------------------------------------

DROP TABLE IF EXISTS "data_connections" CASCADE;
CREATE TABLE "data_connections" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Tipo de dato cambiado a UUID para consistencia.
    "organization_id" UUID, --*/ Tipo de dato cambiado a UUID para coincidir con 'organizations.id'.
    "name" VARCHAR(255),
    "type" VARCHAR(50),
    "configuration" JSONB,

    CONSTRAINT "data_connections_organizations_fkey" FOREIGN KEY("organization_id") REFERENCES "organizations"("id")
);


DROP TABLE IF EXISTS "roles_data_access" CASCADE;
CREATE TABLE "roles_data_access" (
	"id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	"product_id" UUID not NULL,
	"name" varchar(255) not NULL,
	"table_names" _text not NULL,
	"data_access" jsonb NULL,
	"metrics_access" _text null,
	"is_active_rag" BOOLEAN NOT NULL DEFAULT false, 
    "is_active_alerts" BOOLEAN NOT NULL DEFAULT false, 
    "is_active_insight" BOOLEAN NOT NULL DEFAULT false, 
	"created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT null,
    
    
	CONSTRAINT "roles_data_access_products_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")

);

DROP TABLE IF EXISTS "user_data_access" CASCADE;
CREATE TABLE "user_data_access" (
	"id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	"role_data_id" UUID not null,
	"user_id" UUID NULL,
	"table_names" _text NULL,
	"data_access" jsonb NULL,
	"metrics_access" _text null,
	"created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT null,
    "is_active_rag" BOOLEAN NOT NULL DEFAULT false, 
    "is_active_alerts" BOOLEAN NOT NULL DEFAULT false, 
    "is_active_insight" BOOLEAN NOT NULL DEFAULT false, 
    
    CONSTRAINT "user_data_access_users_fkey" FOREIGN KEY("user_id") REFERENCES "users"("id"),
    CONSTRAINT "roles_data_access_users_fkey" FOREIGN KEY("role_data_id") REFERENCES "roles_data_access"("id")
);



CREATE TABLE public.clients_products_deploys(
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	product_id UUID NOT NULL,
	bucket_config varchar(200) NULL NULL,
	gs_examples_agent varchar(200) NULL NULL,
	gs_prompt_agent varchar(200) NULL NULL,
	gs_prompt_sql varchar(200) NULL NULL,
	gs_profiling_agent varchar(200) NULL NULL,
	gs_metrics_config_agent varchar(200) NULL,
	client text NULL,
	"created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT null,
	
	CONSTRAINT "user_data_access_users_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")
);


CREATE TABLE public.user_product_active_wsp(
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	product_id UUID NOT NULL,
	bucket_config varchar(200) NULL NULL,
	user_id UUID not null,
	"created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT null,
	
	CONSTRAINT "product_product_active_wsp_fk" FOREIGN KEY("product_id") REFERENCES "products"("id"),
	CONSTRAINT "user_product_active_wsp_fk" FOREIGN KEY("user_id") REFERENCES "users"("id")
);


-- ------------------------------------------
-- Creación de Semantic Layers
-- ------------------------------------------

DROP TABLE IF EXISTS "semantic_layer_configs" CASCADE;
CREATE TABLE "semantic_layer_configs" (
    -- ID primario autogenerado (UUID)
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "product_id" UUID not null,
    "object_path_saved" VARCHAR(255) NOT NULL,
    "bucket_name_saved" VARCHAR(255) NOT NULL,
    "object_path_deployed" VARCHAR(255) NULL,       -- Puede ser NULL si aún no se ha desplegado
    "bucket_name_deployed" VARCHAR(255) NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT "products_semantic_layer_configs_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")
);

-- ------------------------------------------
-- Creación de Semantic Layer
-- ------------------------------------------




-- ------------------------------------------
-- Creación de Métricas & Ejemplos
-- ------------------------------------------

DROP TABLE IF EXISTS "metrics" CASCADE;
CREATE TABLE "metrics" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4()
    , "product_id" UUID
    , "name" varchar(200)
    , "description" varchar(200)
    , "data_query" TEXT
    , "required_params" TEXT[]
    , optional_params TEXT[]
    
    , CONSTRAINT "metrics_products_fkey" FOREIGN KEY("product_id") REFERENCES "products"("id")
);

DROP TABLE IF EXISTS "metrics_data_sources" CASCADE;
CREATE TABLE "metrics_data_sources" (
    "id" UUID PRIMARY KEY,
    "metric_id" UUID,
    "data_access_item_id" UUID, --*/ Tipo de dato ajustado para coincidir con 'data_access_items.id'.

    CONSTRAINT "metrics_metrics_data_sources_fkey" FOREIGN KEY("metric_id") REFERENCES "metrics"("id"),
    CONSTRAINT "data_access_items_metrics_data_sources_fkey" FOREIGN KEY("data_access_item_id") REFERENCES "data_access_items"("id")
);

DROP TABLE IF EXISTS "examples" CASCADE;
CREATE TABLE "examples" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "product_id" UUID, --*/ Tipo de dato cambiado a UUID para coincidir con 'products.id'. Se recomienda agregar la FK.
    "name" varchar(200),
    "description" varchar(200),
    "data_query" TEXT,
    "created_at" TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at" TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------
-- Alertas de métricas
-- ------------------------------------------

drop table if exists alerts_prompts;
CREATE TABLE alerts_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
    "product_id" UUID,
    prompt_alerta varchar(1500) NOT NULL,                         
    codigo_cron VARCHAR(100) NOT NULL,  
    session_id varchar(250) null,
    flg_habilitado BOOLEAN NOT NULL DEFAULT TRUE,      
    fecha_inicio TIMESTAMP WITH TIME ZONE,
    fecha_fin TIMESTAMP WITH TIME ZONE,
    "created_at" TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT "alertas_products_fk" FOREIGN KEY("product_id") REFERENCES "products"("id")
);



DROP TABLE IF EXISTS "alert_thresholds" CASCADE;
CREATE TABLE "alert_thresholds" (
    "id" UUID PRIMARY KEY,
    "metric_id" UUID, --*/ Tipo de dato cambiado a UUID para coincidir con 'metrics.id'.
    "condition" VARCHAR(10),
    "value" DECIMAL,
    "frecuency" DECIMAL,
    "date_start_control" TIMESTAMP, --*/ Tipo de dato 'datetime' no existe en PostgreSQL, se usa 'TIMESTAMP'.
    "date_end_control" TIMESTAMP, --*/ Tipo de dato 'datetime' no existe en PostgreSQL, se usa 'TIMESTAMP'.
    "created_at" TIMESTAMP NOT NULL DEFAULT now(),
    "updated_at" TIMESTAMP NOT NULL DEFAULT now(),
    "channel_id" UUID, --*/ Corregido typo 'chanel_id'.

    CONSTRAINT "metrics_alert_thresholds_fkey" FOREIGN KEY("metric_id") REFERENCES "metrics"("id")
);

DROP TABLE IF EXISTS "notification_channels" CASCADE;
CREATE TABLE "notification_channels" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(), --*/ Tipo de dato cambiado a UUID para consistencia.
    "alert_id" UUID, --*/ Tipo de dato cambiado a UUID para coincidir con 'alert_thresholds.id'.
    "type" VARCHAR(50),
    "destination_webhook" VARCHAR(255), --*/ Corregido typo 'weebhok'.

    CONSTRAINT "alert_thresholds_notification_channels_fkey" FOREIGN KEY("alert_id") REFERENCES "alert_thresholds"("id")
);