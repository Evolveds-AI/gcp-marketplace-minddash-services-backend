-- DDL de creacion de tablas
-- 1. TABLA DE PLANES (plans)
CREATE TABLE "plans" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "plan_name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE "plans" ADD CONSTRAINT "unique_plan_name" UNIQUE ("plan_name");

-- 2. TABLA DE CUOTAS POR PLAN (plan_quotas)
CREATE TABLE "plan_quotas" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "id_plan" UUID NOT NULL,
    "metric_name" VARCHAR(100) NOT NULL,
    "level" VARCHAR(50),
    "quota" NUMERIC(15, 2) NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "fk_plan_quotas_plans" 
        FOREIGN KEY ("id_plan") 
        REFERENCES "plans"("id") 
        ON DELETE CASCADE
);

ALTER TABLE "plan_quotas" ADD CONSTRAINT "unique_plan_metric" UNIQUE ("id_plan", "metric_name");

-- 3. TABLA DE RELACIÓN PLAN Y ORGANIZACIÓN (organization_plans)
CREATE TABLE "organization_plans" (
    "id" UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "id_plan" UUID NOT NULL,
    "id_organization" UUID NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "fk_org_plans_plans" 
        FOREIGN KEY ("id_plan") 
        REFERENCES "plans"("id"),
    
    -- Restricción de unicidad para que una organización solo tenga un plan asignado
    CONSTRAINT "unique_organization_plan" UNIQUE ("id_organization")
);


-- ddl para insertar datos

-- Insertar datos a planes
INSERT INTO "plans" ("plan_name", "description")
VALUES 
    ('Free', 'Ideal para pruebas básicas de la plataforma'),
    ('Basic', 'Ideal para freelancers y proyectos pequeños'),
    ('Pro', 'Para equipos en crecimiento con necesidades avanzadas'),
    ('Enterprise', 'Soporte total y cuotas ilimitadas para corporaciones')
ON CONFLICT ("plan_name") 
DO UPDATE SET 
    "description" = EXCLUDED."description",
    "updated_at" = NOW();

---
select * from "plans";

-- Insertar datos a cuotas por planes
INSERT INTO "plan_quotas" ("id_plan", "metric_name", "quota", "level", "updated_at")
VALUES 
    -- PLAN: e8c1b9da-c986-4731-a2bb-0af79ebe942f
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'alerta_producto_usuario', 3, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'alerta_organizacion_usuario', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'alerta_total_organizacion', 40, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'alerta_total_producto', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'roles_access_producto', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'user_access_producto', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'importar_datos_producto', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'importar_datos_organizacion', 30, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'rag_storage_producto', 10737418240, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'rag_organizacion', 10737418240, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'mensajes_producto', 40000, NULL, NOW()),
    ('e8c1b9da-c986-4731-a2bb-0af79ebe942f', 'mensajes_organizacion', 40000, NULL, NOW()),

    -- PLAN: 91a1564e-f1e4-446a-b1ad-2f8abcb53bec
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'alerta_producto_usuario', 3, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'alerta_organizacion_usuario', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'alerta_total_organizacion', 40, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'alerta_total_producto', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'roles_access_producto', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'user_access_producto', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'importar_datos_producto', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'importar_datos_organizacion', 30, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'rag_storage_producto', 10737418240, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'rag_organizacion', 10737418240, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'mensajes_producto', 40000, NULL, NOW()),
    ('91a1564e-f1e4-446a-b1ad-2f8abcb53bec', 'mensajes_organizacion', 40000, NULL, NOW()),

    -- PLAN: 40249cb5-c48a-4378-a4c8-9c0ac97515f2
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'alerta_producto_usuario', 3, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'alerta_organizacion_usuario', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'alerta_total_organizacion', 40, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'alerta_total_producto', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'roles_access_producto', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'user_access_producto', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'importar_datos_producto', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'importar_datos_organizacion', 30, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'rag_storage_producto', 10737418240, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'rag_organizacion', 10737418240, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'mensajes_producto', 40000, NULL, NOW()),
    ('40249cb5-c48a-4378-a4c8-9c0ac97515f2', 'mensajes_organizacion', 40000, NULL, NOW()),

    -- PLAN: 29d09783-2df5-4b1d-956f-a8a2d0437a6e
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'alerta_producto_usuario', 3, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'alerta_organizacion_usuario', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'alerta_total_organizacion', 40, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'alerta_total_producto', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'roles_access_producto', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'user_access_producto', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'importar_datos_producto', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'importar_datos_organizacion', 30, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'rag_storage_producto', 10737418240, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'rag_organizacion', 10737418240, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'mensajes_producto', 40000, NULL, NOW()),
    ('29d09783-2df5-4b1d-956f-a8a2d0437a6e', 'mensajes_organizacion', 40000, NULL, NOW())

ON CONFLICT ("id_plan", "metric_name") 
DO UPDATE SET 
    "quota" = EXCLUDED."quota",
    "level" = EXCLUDED."level",
    "updated_at" = NOW();

--
select * from "plan_quotas"



-- Insertar datos a relacion y organizaciones
INSERT INTO "organization_plans" ("id_plan", "id_organization") 
select '29d09783-2df5-4b1d-956f-a8a2d0437a6e', id from organizations o 
ON CONFLICT ("id_organization") 
DO UPDATE SET 
    "id_plan" = EXCLUDED."id_plan",
    "updated_at" = NOW();


select * from organization_plans
