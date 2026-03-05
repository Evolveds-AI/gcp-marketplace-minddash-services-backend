from typing import Optional, List

# try:
#     from sentence_transformers import SentenceTransformer
# except Exception:
#     SentenceTransformer = None
from api.models.billing_models import (
    PlanRegisterRequest,
    PlanUpdateRequest,
    PlanDeleteRequest,
    Plan,
    PlanQuota,
    OrgPlanRegisterRequest,
    OrgPlanUpdateRequest,
    OrgPlanDeleteRequest,
    QuotaRegisterRequest,
    QuotaUpdateRequest,
    QuotaDeleteRequest,
    OrganizationBillingStatus,
)

from api.utils.db_client import execute, execute_procedure_with_out, query_all


# --- SERVICES: PLANS ---
def send_register_plan(data: PlanRegisterRequest) -> str:
    query = "CALL spu_billing_insert_plan(%s, %s, %s);"
    result = execute_procedure_with_out(query, (data.plan_name, data.description, None))
    return str(result["io_plan_id"])


def send_update_plan(data: PlanUpdateRequest) -> int:
    query = "CALL spu_billing_update_plan(%s, %s, %s);"
    return execute(query, (data.id, data.plan_name, data.description))


def send_delete_plan(data: PlanDeleteRequest) -> int:
    query = "CALL spu_billing_delete_plan(%s);"
    return execute(query, (data.id,))


# --- SERVICES: QUOTAS ---
def send_register_quota(data: QuotaRegisterRequest) -> str:
    query = "CALL spu_billing_insert_quota(%s, %s, %s, %s, %s);"
    result = execute_procedure_with_out(
        query, (data.id_plan, data.metric_name, data.level, data.quota, None)
    )
    return str(result["io_quota_id"])


def send_update_quota(data: QuotaUpdateRequest) -> int:
    query = "CALL spu_billing_update_quota(%s, %s, %s, %s, %s);"
    return execute(
        query, (data.id, data.id_plan, data.metric_name, data.level, data.quota)
    )


def send_delete_quota(data: QuotaDeleteRequest) -> int:
    query = "CALL spu_billing_delete_quota(%s);"
    return execute(query, (data.id,))


# --- SERVICES: ORG PLANS ---
def send_register_org_plan(data: OrgPlanRegisterRequest) -> str:
    query = "CALL spu_billing_insert_org_plan(%s, %s, %s);"
    result = execute_procedure_with_out(
        query, (data.id_plan, data.id_organization, None)
    )
    return str(result["io_org_plan_id"])


def send_update_org_plan(data: OrgPlanUpdateRequest) -> int:
    query = "CALL spu_billing_update_org_plan(%s, %s, %s);"
    return execute(query, (data.id, data.id_plan, data.id_organization))


def send_delete_org_plan(data: OrgPlanDeleteRequest) -> int:
    query = "CALL spu_billing_delete_org_plan(%s);"
    return execute(query, (data.id,))


# Servicios para leer tablas
def get_all_plans() -> List[Plan]:
    """Obtiene la lista maestra de todos los planes disponibles."""
    query = "SELECT id, plan_name, description FROM plans ORDER BY plan_name ASC"
    rows = query_all(query)
    return [Plan(**r) for r in rows]


def get_quotas_by_plan(plan_id: str) -> List[PlanQuota]:
    """Recupera todas las métricas y límites configurados para un plan específico."""
    query = """
        SELECT id, metric_name, level, quota 
        FROM plan_quotas 
        WHERE id_plan = %s 
        ORDER BY metric_name ASC
    """
    rows = query_all(query, params=(plan_id,))
    return [PlanQuota(**r) for r in rows]


def get_billing_status_by_org(org_id: str) -> Optional[OrganizationBillingStatus]:
    """
    Obtiene el plan asignado a una organización y desglosa todas sus cuotas.
    """
    # 1. Obtener el plan de la organización
    plan_query = """
        SELECT p.id, p.plan_name, p.description
        FROM organization_plans op
        INNER JOIN plans p ON op.id_plan = p.id
        WHERE op.id_organization = %s
    """
    plan_row = query_all(plan_query, params=(org_id,))

    if not plan_row:
        return None

    # 2. Obtener las cuotas asociadas a ese plan
    plan_info = Plan(**plan_row[0])
    quotas = get_quotas_by_plan(plan_info.id)

    return OrganizationBillingStatus(
        organization_id=org_id, plan_details=plan_info, quotas=quotas
    )
