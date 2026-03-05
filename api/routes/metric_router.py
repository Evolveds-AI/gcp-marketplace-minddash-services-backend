from typing import List
import json
import re

from api.models.data_access_models import ClientDeployRegisterRequest
from api.services.data_access_service import send_register_client_deploy_v2
from fastapi import APIRouter, HTTPException, status

from api.models.metric_models import (
    GetMetricsByProductRequest,
    GetMetricsRequest,
    MetricByProduct,
    MetricCreationResponse,
    MetricDeleteRequest,
    MetricDeleteResponse,
    MetricRegisterRequest,
    MetricResponse,
    MetricUpdateRequest,
    MetricUpdateResponse,
    UploadMetricsByProductRequest,
    UploadMetricsByProductResponse,
    UploadMetricsRequest,
    UploadMetricsResponse,
)
from api.services.gcs_client import upload_text_to_gcs
from api.services.metric_service import (
    build_metrics_yaml,
    format_db_metrics_for_yaml,
    get_metrics,
    get_metrics_by_product,
    send_delete_metric,
    send_register_metric,
    send_update_metric,
)

metric_router = APIRouter(prefix="/metrics")


@metric_router.post(
    "/upload",
    response_model=UploadMetricsResponse,
    tags=["Metrics Management"],
    summary="Generar y Subir Metricas yaml a GCS",
    description=(
        "Crea un archivo YAML de metricas (que incluye version, parametros, query_content, etc.) y lo sube a una ruta específica en GCS, devolviendo la URL."
    ),
)
async def upload_prompt(req: UploadMetricsRequest):
    # Ya no hay error de 'str' object has no attribute 'items'
    yaml_output = build_metrics_yaml(
        version=req.version,
        product=req.product,
        metrics_name=req.metrics_name,
        description=req.description,
        metrics_data=req.metrics_data,  # <- Usamos el campo con el tipo corregido
    )

    url = upload_text_to_gcs(
        req.bucket_name, req.object_path, yaml_output, content_type="text/yaml"
    )
    return UploadMetricsResponse(status="success", url=url)


@metric_router.post(
    "/uploadByproduct",
    response_model=UploadMetricsByProductResponse,
    tags=["Metrics Management"],
    summary="Generar y Subir Metricas yaml a GCS",
    description=(
        "Crea un archivo YAML de metricas (que incluye version, parametros, query_content, etc.) y lo sube a una ruta específica en GCS, devolviendo la URL."
    ),
)
async def upload_prompt_by_product(request_body: UploadMetricsByProductRequest):
    # 1. Obtener las métricas de la DB
    db_metrics_list = get_metrics_by_product(
        GetMetricsByProductRequest(product_id=request_body.product_id)
    )

    if not db_metrics_list:
        # Manejo si no se encuentran métricas
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron métricas para el producto ID: {request_body.product_id}",
        )

    # 2. Formatear la lista de la DB al payload de YAML (List[MetricDefinition])
    metrics_yaml_payload = format_db_metrics_for_yaml(db_metrics_list)

    # 3. Obtener metadata necesaria (Product Name y ID)
    # Asumimos que la request tiene los campos version, product, metrics_name, description
    # Opcional: Si solo tienes product_id, puedes obtener product_name de db_metrics_list[0].product_name
    product_name = db_metrics_list[
        0
    ].product_name  # Usamos el nombre del primer registro

    # 4. Generar el YAML final
    yaml_output = build_metrics_yaml(
        version="0.1",
        product="minddash",  # Usamos el nombre del producto
        metrics_name="minddash description",
        description="minddash description",
        metrics_data=metrics_yaml_payload,  # <- El payload formateado
    )

    # 5. Subir a GCS
    url = upload_text_to_gcs(
        request_body.bucket_name,
        request_body.object_path,
        yaml_output,
        content_type="text/yaml",
    )
    insert = ClientDeployRegisterRequest(
        product_id=request_body.product_id,
        bucket_config=None,
        gs_examples_agent=None,
        gs_prompt_agent=None,
        gs_prompt_sql=None,
        gs_profiling_agent=None,
        gs_metrics_config_agent=request_body.object_path,
        gs_semantic_config=None,
        client=None,
    )
    new_deploy_id = send_register_client_deploy_v2(insert)
    return UploadMetricsByProductResponse(status="success", url=url)


@metric_router.post(
    "/getMetricsByProduct",
    response_model=List[MetricByProduct],
    tags=["Metrics Management"],
    summary="Listar Métricas por Producto",
    description="Obtiene todas las métricas que han sido asociadas a un **producto** específico, filtrando por el `product_id` provisto.",
)
def getMetricsByProduct(
    request_body: GetMetricsByProductRequest,
) -> List[MetricByProduct]:
    """
    Obtiene todas las métricas de un producto específico,
    filtrando por el product_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_metrics_by_product(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener métricas: {e}")


@metric_router.post(
    "/getMetrics",
    response_model=List[MetricResponse],
    tags=["Metrics Management"],
    summary="Listar Métricas (Todas o por ID)",
    description="Obtiene una lista de todas las métricas registradas. Opcionalmente, si se proporciona un `metric_id` en el cuerpo, devuelve solo los detalles de esa métrica específica.",
)
def getMetrics(request_body: GetMetricsRequest) -> List[MetricResponse]:
    """
    Obtiene todas las métricas o una específica por ID.
    Si se proporciona metric_id en el body, retorna solo esa métrica.
    Si no se proporciona metric_id, retorna todas las métricas.
    """
    try:
        # Llama a la función de servicio pasando el request completo
        return get_metrics(request_body)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener métricas: {e}")


@metric_router.post(
    "/sendRegisterMetric",
    response_model=MetricCreationResponse,
    tags=["Metrics Management"],
    summary="Registrar Nueva Métrica (CREATE)",
    description="Crea y registra una nueva métrica de negocio en la base de datos.",
)
def sendRegisterMetric(metric_data: MetricRegisterRequest) -> MetricCreationResponse:
    """
    Endpoint para registrar una nueva métrica.
    """
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_metric(metric_data)

        # Construir y retornar la respuesta
        return MetricCreationResponse(id_metric=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroMetric: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la métrica: {e}"
        )


@metric_router.put(
    "/updateMetric",
    response_model=MetricUpdateResponse,
    tags=["Metrics Management"],
    summary="Actualizar Métrica (UPDATE)",
    description="Modifica los detalles de una métrica existente. Devuelve error 404 si el `id` de la métrica no existe.",
)
def updateMetric(metric_data: MetricUpdateRequest) -> MetricUpdateResponse:
    """
    Endpoint para actualizar una métrica existente.
    """
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        #    Si el ID SÍ existe, devuelve -1 (rowcount).
        metric_data.data_query = clean_data_query(metric_data.data_query)
        rows_affected = send_update_metric(metric_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción, por lo que la operación fue exitosa.
        #    No importa si rows_affected es 1 o -1.
        return MetricUpdateResponse(metric_id=metric_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        # Esto sucede cuando el ID no existe en la BD.
        if "No se puede actualizar. La métrica con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar la métrica: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la métrica: {error_detail}",
        )


@metric_router.delete(
    "/deleteMetric",
    response_model=MetricDeleteResponse,
    tags=["Metrics Management"],
    summary="Eliminar Métrica (DELETE)",
    description="Elimina una métrica del sistema. Devuelve error 404 si el `id` de la métrica no existe.",
)
def deleteMetric(metric_data: MetricDeleteRequest) -> MetricDeleteResponse:
    """
    Endpoint para eliminar una métrica existente.
    """
    metric_id = metric_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_metric(metric_data)

        # Si llegamos hasta aquí, NO hubo una excepción, la eliminación fue exitosa (rowcount = -1).
        return MetricDeleteResponse(metric_id=metric_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "No se puede eliminar. La métrica con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la métrica con ID: {metric_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar la métrica: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la métrica: {error_detail}",
        )


def clean_data_query(q: str) -> str:
    if not q:
        return q

    try:
        while isinstance(q, str) and q.startswith('"') and q.endswith('"'):
            q = json.loads(q)
    except Exception:
        pass
    q = q.replace('\\"', '"')
    q = re.sub(r'^"+|"+$', "", q)
    q = q.replace("\\", "")
    return q.strip()
