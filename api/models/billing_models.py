from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime


logger = logging.getLogger(__name__)

# ==========================================
# 1. MODELOS EXISTENTES (CRUD)
# ==========================================


# --- MODELS: PLANS ---
class PlanRegisterRequest(BaseModel):
    plan_name: str = Field(
        ..., max_length=255, description="Nombre del plan comercial."
    )
    description: Optional[str] = Field(
        None, description="Descripción de los beneficios del plan."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_name": "Pro",
                "description": "Plan avanzado para equipos.",
            }
        }


class PlanUpdateRequest(BaseModel):
    id: str = Field(..., description="UUID del plan a actualizar.")
    plan_name: str = Field(..., max_length=255, description="Nuevo nombre del plan.")
    description: Optional[str] = Field(None, description="Nueva descripción.")


class PlanDeleteRequest(BaseModel):
    id: str = Field(..., description="UUID del plan a eliminar.")


class PlanCreationResponse(BaseModel):
    id_plan: str


class PlanActionResponse(BaseModel):
    message: str = "Operación de plan exitosa."
    plan_id: str


# --- MODELS: QUOTAS ---
class QuotaRegisterRequest(BaseModel):
    id_plan: str = Field(..., description="ID del plan al que se asigna la cuota.")
    metric_name: str = Field(..., max_length=100, description="Nombre de la métrica.")
    level: Optional[str] = Field(
        None, max_length=50, description="Nivel (Silver, Gold, etc.)."
    )
    quota: float = Field(..., description="Límite numérico máximo.")


class QuotaUpdateRequest(BaseModel):
    id: str = Field(..., description="ID del registro de cuota.")
    id_plan: str = Field(..., description="ID del plan.")
    metric_name: str = Field(..., max_length=100)
    level: Optional[str] = None
    quota: float


class QuotaDeleteRequest(BaseModel):
    id: str = Field(..., description="ID de la cuota a eliminar.")


class QuotaCreationResponse(BaseModel):
    id_quota: str


class QuotaActionResponse(BaseModel):
    message: str = "Operación de cuota exitosa."
    quota_id: str


# --- MODELS: ORGANIZATION PLANS ---
class OrgPlanRegisterRequest(BaseModel):
    id_plan: str = Field(..., description="Plan a asignar.")
    id_organization: str = Field(..., description="Organización receptora.")


class OrgPlanUpdateRequest(BaseModel):
    id: str = Field(..., description="ID del registro de asignación.")
    id_plan: str
    id_organization: str


class OrgPlanDeleteRequest(BaseModel):
    id: str = Field(..., description="ID de la asignación a eliminar.")


class OrgPlanCreationResponse(BaseModel):
    id_org_plan: str


class OrgPlanActionResponse(BaseModel):
    message: str = "Asignación actualizada/eliminada exitosamente."
    org_plan_id: str


# ==========================================
# 2. NUEVOS MODELOS PARA LECTURA (READ)
# ==========================================


class Plan(BaseModel):
    """Representa la información básica de un plan de servicio para listas."""

    id: str = Field(..., description="UUID único del plan.")
    plan_name: str = Field(
        ..., description="Nombre del plan (ej. Free, Pro, Enterprise)."
    )
    description: Optional[str] = Field(None, description="Resumen de beneficios.")

    class Config:
        from_attributes = True


class PlanQuota(BaseModel):
    """Representa un límite asignado a una métrica técnica."""

    id: str = Field(..., description="UUID del registro de cuota.")
    metric_name: str = Field(
        ..., description="Nombre de la métrica (ej. rag_storage_producto)."
    )
    level: Optional[str] = Field(None, description="Nivel de la métrica.")
    quota: float = Field(..., description="Límite máximo permitido.")

    class Config:
        from_attributes = True


class OrganizationBillingStatus(BaseModel):
    """Estructura consolidada que une el plan y sus cuotas para una organización."""

    organization_id: str = Field(..., description="UUID de la organización.")
    plan_details: Plan = Field(
        ..., description="Objeto con los detalles del plan asignado."
    )
    quotas: List[PlanQuota] = Field(
        default_factory=list, description="Lista de cuotas activas para este plan."
    )

    class Config:
        from_attributes = True


class GetQuotasByPlanRequest(BaseModel):
    """Cuerpo de solicitud para filtrar cuotas por un plan específico."""

    plan_id: str = Field(..., description="UUID del plan consultado.")

    class Config:
        json_schema_extra = {
            "example": {"plan_id": "5a316e8e-d6d7-4963-9b78-9c2b315038e6"}
        }


class GetBillingByOrgRequest(BaseModel):
    """Cuerpo de solicitud para consultar el estado de facturación de una organización."""

    organization_id: str = Field(..., description="UUID de la organización consultada.")

    class Config:
        json_schema_extra = {
            "example": {"organization_id": "deb385a8-ea08-4d9e-99b5-0952e0a0d971"}
        }
