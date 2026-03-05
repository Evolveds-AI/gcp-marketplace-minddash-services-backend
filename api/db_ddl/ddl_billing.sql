-- =============================================================================
-- PROCEDIMIENTOS PARA TABLA: plans
-- =============================================================================

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
    
    RAISE NOTICE 'Plan "%" creado exitosamente.', p_plan_name;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_update_plan(
    p_plan_id UUID,
    p_plan_name VARCHAR(255),
    p_description TEXT
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plans WHERE id = p_plan_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. El plan con ID % no existe.', p_plan_id;
    END IF;

    UPDATE plans
    SET plan_name = p_plan_name,
        description = p_description,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_plan_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_delete_plan(
    p_plan_id UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plans WHERE id = p_plan_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. El plan con ID % no existe.', p_plan_id;
    END IF;

    DELETE FROM plans WHERE id = p_plan_id;
END;
$$;

-- =============================================================================
-- PROCEDIMIENTOS PARA TABLA: plan_quotas
-- =============================================================================

CREATE OR REPLACE PROCEDURE spu_billing_insert_quota(
    p_id_plan UUID,
    p_metric_name VARCHAR(100),
    p_level VARCHAR(50),
    p_quota NUMERIC(15, 2),
    INOUT io_quota_id UUID DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plans WHERE id = p_id_plan) THEN
        RAISE EXCEPTION 'ERROR: El plan con ID % no existe. No se puede crear la cuota.', p_id_plan;
    END IF;

    io_quota_id := uuid_generate_v4();

    INSERT INTO plan_quotas (id, id_plan, metric_name, level, quota, created_at, updated_at)
    VALUES (io_quota_id, p_id_plan, p_metric_name, p_level, p_quota, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_update_quota(
    p_quota_id UUID,
    p_id_plan UUID,
    p_metric_name VARCHAR(100),
    p_level VARCHAR(50),
    p_quota NUMERIC(15, 2)
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plan_quotas WHERE id = p_quota_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. La cuota con ID % no existe.', p_quota_id;
    END IF;

    UPDATE plan_quotas
    SET id_plan = p_id_plan,
        metric_name = p_metric_name,
        level = p_level,
        quota = p_quota,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_quota_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_delete_quota(
    p_quota_id UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plan_quotas WHERE id = p_quota_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La cuota con ID % no existe.', p_quota_id;
    END IF;

    DELETE FROM plan_quotas WHERE id = p_quota_id;
END;
$$;

-- =============================================================================
-- PROCEDIMIENTOS PARA TABLA: organization_plans
-- =============================================================================

CREATE OR REPLACE PROCEDURE spu_billing_insert_org_plan(
    p_id_plan UUID,
    p_id_organization UUID,
    INOUT io_org_plan_id UUID DEFAULT NULL
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM plans WHERE id = p_id_plan) THEN
        RAISE EXCEPTION 'ERROR: El plan con ID % no existe.', p_id_plan;
    END IF;

    io_org_plan_id := uuid_generate_v4();

    INSERT INTO organization_plans (id, id_plan, id_organization, created_at, updated_at)
    VALUES (io_org_plan_id, p_id_plan, p_id_organization, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_update_org_plan(
    p_org_plan_id UUID,
    p_id_plan UUID,
    p_id_organization UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM organization_plans WHERE id = p_org_plan_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede actualizar. La asignación con ID % no existe.', p_org_plan_id;
    END IF;

    UPDATE organization_plans
    SET id_plan = p_id_plan,
        id_organization = p_id_organization,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_org_plan_id;
END;
$$;

CREATE OR REPLACE PROCEDURE spu_billing_delete_org_plan(
    p_org_plan_id UUID
)
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM organization_plans WHERE id = p_org_plan_id) THEN
        RAISE EXCEPTION 'ERROR: No se puede eliminar. La asignación con ID % no existe.', p_org_plan_id;
    END IF;

    DELETE FROM organization_plans WHERE id = p_org_plan_id;
END;
$$;