# middleware.py
import json
from api.utils.db_client import query_one
from fastapi.responses import JSONResponse
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

doct_paths = {
    "path_alert": "/alert/sendRegistroAlerta",
    "path_rag": "/alert/sendRegisterRag",
    "path_access_user": "/user-data-access/sendRegistroUserDataAccess",
    "path_access_rol": "/user-data-access/sendRegistroRoleDataAccess",
}


SQL_QUOTES = """
        select
            pq.quota as quota
        from organization_plans op
        join "plans" p on op.id_plan = p.id
        join plan_quotas pq  on p.id=pq.id_plan 
        where
                op.id_organization = %s
            and pq.metric_name = %s
"""


# Validacion  de usuarios por producto
async def validate_user_access_product(body: dict, org_id: str) -> JSONResponse | None:
    """
    1. Cuota de usuarios con acceso por producto.

    Verifica si el número de usuarios asignados a un producto específico a través de sus roles
    ha alcanzado el límite permitido definido en la tabla de métricas.
    """
    role_id = body.get("role_data_id")

    # BUSCAMOS EL PRODUCT_ID PORQUE NO VIENE EN EL BODY
    p_id = get_product_from_role(role_id)

    if not p_id:
        logger.warning(f"No se encontro producto asociado al rol: {role_id}")
        return None  # O error si prefieres

    logger.info(f"Iniciando validacion de cuota de usuarios para Producto: {p_id}")

    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_q = query_one(sql_quota, ("user_access_producto",))
    res_q = query_one(SQL_QUOTES, (org_id, "user_access_producto"))
    limit = float(res_q["quota"]) if res_q and res_q["quota"] else 5.0

    sql_usage = """
        SELECT COUNT(uda.id) as total 
        FROM user_data_access uda 
        JOIN roles_data_access rda ON uda.role_data_id = rda.id 
        WHERE rda.product_id = %s
    """
    res_u = query_one(sql_usage, (p_id,))
    current = res_u["total"] if res_u else 0

    logger.info(
        f"Metrica: user_access_producto | Producto: {p_id} | Uso actual: {current} | Limite: {limit}"
    )

    if current >= limit:
        logger.error(
            f"Validacion fallida: Limite de usuarios alcanzado para Producto: {p_id}"
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_USER_PRODUCT",
                "message": f"Limite de usuarios para este producto alcanzado ({current}/{limit}).",
            },
        )

    logger.info(
        f"Validacion exitosa: Usuario permitido para acceder al Producto: {p_id}"
    )
    return None


# Validacion de roles por producto
async def validate_roles_access_product(body: dict, org_id: str) -> JSONResponse | None:
    """
    3. Cuota de roles por producto.

    Valida la cantidad máxima de roles de acceso a datos que pueden ser creados para
    un producto específico.
    """
    p_id = body.get("product_id")

    logger.info(f"Iniciando validacion de cuota de roles para Producto: {p_id}")

    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_q = query_one(sql_quota, ("roles_access_producto",))
    res_q = query_one(SQL_QUOTES, (org_id, "roles_access_producto"))
    limit = float(res_q["quota"]) if res_q and res_q["quota"] else 3.0

    sql_usage = "SELECT COUNT(id) as total FROM roles_data_access WHERE product_id = %s"
    res_u = query_one(sql_usage, (p_id,))
    current = res_u["total"] if res_u else 0

    logger.info(
        f"Metrica: roles_access_producto | Producto: {p_id} | Uso actual: {current} | Limite: {limit}"
    )

    if current >= limit:
        logger.error(
            f"Validacion fallida: Limite de roles alcanzado para Producto: {p_id}"
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_ROLES_PRODUCT",
                "message": f"Limite de roles para este producto alcanzado ({current}/{limit}).",
            },
        )

    logger.info(
        f"Validacion exitosa: Creacion de rol permitida para el Producto: {p_id}"
    )
    return None


# Validacion de alertas por organizacion y usuario
async def validate_organization_alert_quota(
    body: dict, org_id: str
) -> JSONResponse | None:
    """
    Validación de alertas por organización y usuario.

    Determina a qué organización pertenece el producto y cuenta cuántas alertas tiene
    el usuario en total dentro de todos los proyectos de esa organización.
    """

    p_id = body.get("product_id")
    u_id = body.get("user_id")

    # 1. Obtener el organization_id a partir del product_id
    sql_get_org = """
        SELECT prj.organization_id 
        FROM products p
        JOIN projects prj ON p.project_id = prj.id
        WHERE p.id = %s
    """
    res_org = query_one(sql_get_org, (p_id,))

    if not res_org or not res_org.get("organization_id"):
        logger.warning(f"No se encontró organización para el producto: {p_id}")
        return None  # O podrías devolver error si es obligatorio

    org_id = res_org["organization_id"]

    # 2. Obtener la Quota para la organización
    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_quota = query_one(sql_quota, ("alerta_organizacion_usuario",))
    res_quota = query_one(SQL_QUOTES, (org_id, "alerta_organizacion_usuario"))
    quota_limit = (
        float(res_quota["quota"]) if res_quota and res_quota["quota"] else 10.0
    )  # Default 10

    # 3. Contar alertas de ese usuario en TODA la organización
    # Cruzamos alerts_prompts -> products -> projects
    sql_usage = """
        SELECT COUNT(ap.id) as total
        FROM alerts_prompts ap
        JOIN products p ON ap.product_id = p.id
        JOIN projects prj ON p.project_id = prj.id
        WHERE prj.organization_id = %s AND ap.user_id = %s
    """
    res_usage = query_one(sql_usage, (org_id, u_id))
    current_count = res_usage["total"] if res_usage else 0

    logger.info(
        f"[CHECK ORG QUOTA] Org: {org_id} | User: {u_id} | Uso: {current_count}/{quota_limit}"
    )

    if current_count >= quota_limit:
        logger.error(
            f"[BLOQUEADO ORG] Organización {org_id} excedió cuota para el usuario {u_id}"
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_ORG_ALERTS_EXCEEDED",
                "message": f"Límite alcanzado: Ya tienes {current_count} alertas para esta organizacion y tu limite es {quota_limit}..",
            },
        )

    return None


# Validacion de alertas por productos y usuario
async def validate_alert_quota(body: dict, org_id: str) -> JSONResponse | None:
    """
    Validación de alertas por productos y usuario.

    Controla el límite individual de alertas que un usuario puede registrar en un
    chatbot o producto específico.
    """

    p_id = body.get("product_id")
    u_id = body.get("user_id")

    if not p_id or not u_id:
        logger.warning("Validación fallida: Faltan product_id o user_id en el body")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "product_id y user_id son requeridos",
            },
        )

    # 1. Obtener Quota
    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_quota = query_one(sql_quota, ("alerta_producto_usuario",))
    res_quota = query_one(SQL_QUOTES, (org_id, "alerta_producto_usuario"))
    quota_limit = float(res_quota["quota"]) if res_quota and res_quota["quota"] else 3.0

    # 2. Obtener Uso Actual
    sql_usage = "SELECT COUNT(*) as total FROM alerts_prompts WHERE product_id = %s AND user_id = %s"
    res_usage = query_one(sql_usage, (p_id, u_id))
    current_count = res_usage["total"] if res_usage else 0

    logger.info(
        f"[CHECK QUOTA] User: {u_id} | Product: {p_id} | Uso: {current_count}/{quota_limit}"
    )

    if current_count >= quota_limit:
        logger.error(
            f"[BLOQUEADO] Usuario {u_id} excedió cuota de alertas ({current_count} >= {quota_limit})"
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_ALERTS_EXCEEDED",
                "message": f"Límite alcanzado: Ya tienes {current_count} alertas para este producto y tu limite es {quota_limit}.",
            },
        )

    logger.info(f"[PERMITIDO] Usuario {u_id} dentro de los límites.")
    return None


# Validacion de alertas totale por producto
async def validate_total_product_alerts(body: dict, org_id: str) -> JSONResponse | None:
    """
    Validación de alertas totales por producto.

    Asegura que la sumatoria de alertas de todos los usuarios para un solo producto
    no exceda la capacidad técnica o comercial del mismo.
    """
    p_id = body.get("product_id")

    # 1. Obtener Quota (Límite total del producto)
    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_quota = query_one(sql_quota, ("alerta_total_producto",))
    res_quota = query_one(SQL_QUOTES, (org_id, "alerta_total_producto"))
    # Definimos un default de 50 si no existe en la tabla
    quota_limit = (
        float(res_quota["quota"]) if res_quota and res_quota["quota"] else 50.0
    )

    # 2. Obtener Uso Actual (Conteo global por product_id)
    sql_usage = "SELECT COUNT(*) as total FROM alerts_prompts WHERE product_id = %s"
    res_usage = query_one(sql_usage, (p_id,))
    current_count = res_usage["total"] if res_usage else 0

    logger.info(
        f"[CHECK TOTAL PRODUCT QUOTA] Product: {p_id} | Uso: {current_count}/{quota_limit}"
    )

    if current_count >= quota_limit:
        logger.error(
            f"[BLOQUEADO TOTAL PRODUCTO] Producto {p_id} alcanzó el límite global de alertas."
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_TOTAL_PRODUCT_ALERTS_EXCEEDED",
                "message": f"Límite global alcanzado: Este producto ya tiene {current_count} alertas registradas en total. Límite permitido: {quota_limit}.",
            },
        )

    return None


# Validacion de alertas totale por organizacion
async def validate_total_organization_alerts(
    body: dict, org_id: str
) -> JSONResponse | None:
    """
    Validación de alertas totales por organización.

    Representa el límite más alto de la jerarquía; valida que la organización entera
    no supere el total de alertas contratadas en su plan global.
    """

    p_id = body.get("product_id")

    # 1. Obtener el organization_id a partir del product_id
    sql_get_org = """
        SELECT prj.organization_id 
        FROM products p
        JOIN projects prj ON p.project_id = prj.id
        WHERE p.id = %s
    """
    res_org = query_one(sql_get_org, (p_id,))

    if not res_org or not res_org.get("organization_id"):
        logger.warning(f"No se encontró organización para el producto: {p_id}")
        return None

    org_id = res_org["organization_id"]

    # 2. Obtener la Quota Global de la Organización
    # sql_quota = "SELECT quota FROM metric_configurations_quota WHERE metrics_name = %s"
    # res_quota = query_one(sql_quota, ("alerta_total_organizacion",))
    res_quota = query_one(SQL_QUOTES, (org_id, "alerta_total_organizacion"))
    # Default de 100 si no existe configuración
    quota_limit = (
        float(res_quota["quota"]) if res_quota and res_quota["quota"] else 100.0
    )

    # 3. Contar TODAS las alertas de la organización
    sql_usage = """
        SELECT COUNT(ap.id) as total
        FROM alerts_prompts ap
        JOIN products p ON ap.product_id = p.id
        JOIN projects prj ON p.project_id = prj.id
        WHERE prj.organization_id = %s
    """
    res_usage = query_one(sql_usage, (org_id,))
    current_count = res_usage["total"] if res_usage else 0

    logger.info(
        f"[CHECK GLOBAL ORG QUOTA] Org: {org_id} | Uso: {current_count}/{quota_limit}"
    )

    if current_count >= quota_limit:
        logger.error(
            f"[BLOQUEADO GLOBAL ORG] La organización {org_id} alcanzó su límite total contratado."
        )
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "code": "LIMIT_GLOBAL_ORG_ALERTS_EXCEEDED",
                "message": f"Límite organizacional alcanzado: Tu empresa tiene {current_count} alertas en total. El límite de tu plan es {quota_limit}.",
            },
        )

    return None


# poder obtener el product_id por el role
def get_product_from_role(role_data_id: str):
    """Obtiene el product_id a partir de un role_data_id."""
    sql = "SELECT product_id FROM roles_data_access WHERE id = %s"
    res = query_one(sql, (role_data_id,))
    return res["product_id"] if res else None


async def run_middleware_logic(request: Request) -> JSONResponse | None:
    path = request.url.path
    logger.info(f"Middleware analizando ruta: {path}")

    body_bytes = await request.body()

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    request._receive = receive

    body = json.loads(body_bytes) if body_bytes else {}

    p_id = body.get("product_id")

    # 1. Obtener el organization_id a partir del product_id
    sql_get_org = """
        SELECT prj.organization_id 
        FROM products p
        JOIN projects prj ON p.project_id = prj.id
        WHERE p.id = %s
    """
    res_org = query_one(sql_get_org, (p_id,))

    if not res_org or not res_org.get("organization_id"):
        logger.warning(f"No se encontró organización para el producto: {p_id}")
        return None  # O podrías devolver error si es obligatorio

    org_id = res_org["organization_id"]

    if path == doct_paths["path_alert"]:
        # VALIDACIÓN 1: Por Producto (la que ya tenías)
        error_product = await validate_alert_quota(body, org_id)
        if error_product:
            return error_product

        # VALIDACIÓN 2: Por Organización (la nueva)
        error_org = await validate_organization_alert_quota(body, org_id)
        if error_org:
            return error_org

        # VALIDACIÓN 3: Por producto (global)
        error_org = await validate_total_product_alerts(body, org_id)
        if error_org:
            return error_org

        # VALIDACIÓN 4: Por Organización (global)
        error_org = await validate_total_organization_alerts(body, org_id)
        if error_org:
            return error_org

    if path == doct_paths["path_access_user"]:
        # VALIDACIÓN 1: Por Producto (la que ya tenías)
        error_product = await validate_user_access_product(body, org_id)
        if error_product:
            return error_product

    if path == doct_paths["path_access_rol"]:
        # VALIDACIÓN 1: Por Producto (la que ya tenías)
        error_product = await validate_roles_access_product(body, org_id)
        if error_product:
            return error_product

    return None
