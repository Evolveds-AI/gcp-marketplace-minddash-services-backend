import os
from typing import Dict, List

from fastapi import APIRouter, HTTPException, status

from api.models.billing_models import (
    PlanRegisterRequest,
    PlanUpdateRequest,
    PlanDeleteRequest,
    PlanCreationResponse,
    PlanActionResponse,
    Plan,
    PlanQuota,
    OrgPlanRegisterRequest,
    OrgPlanUpdateRequest,
    OrgPlanDeleteRequest,
    QuotaRegisterRequest,
    QuotaUpdateRequest,
    QuotaDeleteRequest,
    QuotaCreationResponse,
    QuotaActionResponse,
    OrganizationBillingStatus,
    GetQuotasByPlanRequest,
    GetBillingByOrgRequest,
    OrgPlanCreationResponse,
    OrgPlanActionResponse,
)

from api.services.billing_service import (
    send_register_plan,
    send_update_plan,
    send_delete_plan,
    send_register_quota,
    send_update_quota,
    send_delete_quota,
    send_register_org_plan,
    send_update_org_plan,
    send_delete_org_plan,
    get_all_plans,
    get_quotas_by_plan,
    get_billing_status_by_org,
)

_ENV_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
_ENV_REGION = os.environ.get("GOOGLE_CLOUD_LOCATION")
_ENV_MODEL_NAME = os.environ.get("GOOGLE_GEMINI_MODEL_NAME")

billing_router = APIRouter(prefix="/billing", tags=["Billing Management"])


# --- ENDPOINTS: PLANS ---
@billing_router.post("/sendRegistroPlan", response_model=PlanCreationResponse)
def registerPlan(data: PlanRegisterRequest):
    try:
        return PlanCreationResponse(id_plan=send_register_plan(data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar plan: {e}")


@billing_router.put("/updatePlan", response_model=PlanActionResponse)
def updatePlan(data: PlanUpdateRequest):
    try:
        send_update_plan(data)
        return PlanActionResponse(plan_id=data.id)
    except Exception as e:
        if "No se puede actualizar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.delete("/deletePlan", response_model=PlanActionResponse)
def deletePlan(data: PlanDeleteRequest):
    try:
        send_delete_plan(data)
        return PlanActionResponse(
            plan_id=data.id, message="Plan eliminado exitosamente."
        )
    except Exception as e:
        if "No se puede eliminar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS: QUOTAS ---
@billing_router.post("/sendRegistroQuota", response_model=QuotaCreationResponse)
def registerQuota(data: QuotaRegisterRequest):
    try:
        return QuotaCreationResponse(id_quota=send_register_quota(data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar cuota: {e}")


@billing_router.put("/updateQuota", response_model=QuotaActionResponse)
def updateQuota(data: QuotaUpdateRequest):
    try:
        send_update_quota(data)
        return QuotaActionResponse(quota_id=data.id)
    except Exception as e:
        if "No se puede actualizar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.delete("/deleteQuota", response_model=QuotaActionResponse)
def deleteQuota(data: QuotaDeleteRequest):
    try:
        send_delete_quota(data)
        return QuotaActionResponse(quota_id=data.id, message="Cuota eliminada.")
    except Exception as e:
        if "No se puede eliminar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS: ORG PLANS ---
@billing_router.post("/sendRegistroOrgPlan", response_model=OrgPlanCreationResponse)
def registerOrgPlan(data: OrgPlanRegisterRequest):
    try:
        return OrgPlanCreationResponse(id_org_plan=send_register_org_plan(data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al asignar plan: {e}")


@billing_router.put("/updateOrgPlan", response_model=OrgPlanActionResponse)
def updateOrgPlan(data: OrgPlanUpdateRequest):
    try:
        send_update_org_plan(data)
        return OrgPlanActionResponse(org_plan_id=data.id)
    except Exception as e:
        if "No se puede actualizar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.delete("/deleteOrgPlan", response_model=OrgPlanActionResponse)
def deleteOrgPlan(data: OrgPlanDeleteRequest):
    try:
        send_delete_org_plan(data)
        return OrgPlanActionResponse(
            org_plan_id=data.id, message="Asignación eliminada."
        )
    except Exception as e:
        if "No se puede eliminar" in str(e):
            raise HTTPException(status_code=404, detail=str(e).split("ERROR: ")[-1])
        raise HTTPException(status_code=500, detail=str(e))


@billing_router.get(
    "/getListPlans",
    response_model=List[Plan],
    summary="Listar Todos los Planes",
    description="Retorna el catálogo completo de planes (Free, Basic, Pro, Enterprise).",
)
def getListPlans():
    try:
        return get_all_plans()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar planes: {e}")


@billing_router.post(
    "/getListQuotasByPlan",
    response_model=List[PlanQuota],
    summary="Listar Cuotas por Plan",
    description="Obtiene todos los límites y métricas configurados para un plan específico.",
)
def getListQuotasByPlan(request: GetQuotasByPlanRequest):
    try:
        return get_quotas_by_plan(request.plan_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener cuotas: {e}")


@billing_router.post(
    "/getBillingStatusByOrg",
    response_model=OrganizationBillingStatus,
    summary="Estado de Facturación por Organización",
    description="Devuelve el plan actual de la organización y el detalle de todas sus cuotas activas.",
)
def getBillingStatusByOrg(request: GetBillingByOrgRequest):
    try:
        status_data = get_billing_status_by_org(request.organization_id)
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La organización no tiene un plan asignado actualmente.",
            )
        return status_data
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar estado: {e}")
