import os
from typing import Dict, List

from api.models.data_access_models import ClientDeployRegisterRequest
from api.services.data_access_service import send_register_client_deploy_v2
from fastapi import APIRouter, HTTPException, status

from api.models.prompt_and_example_models import (
    BuildPromptsExamplesByProductRequest,
    BuildPromptsExamplesRequest,
    BuildPromptsExamplesResponse,
    ExampleCreationResponse,
    ExampleDeleteRequest,
    ExampleDeleteResponse,
    ExampleListRequest,
    ExampleListResponseItem,
    ExampleRegisterRequest,
    ExampleUpdateRequest,
    ExampleUpdateResponse,
    GetPromptsRequestByProduct,
    GetPromptsResponseByProduct,
    PromptCreationResponse,
    PromptDeleteResponse,
    PromptRegisterRequestV2,
    PromptUpdateRequestV2,
    PromptUpdateResponse,
    UploadPromptRequest,
    UploadPromptRequestByProduct,
    UploadPromptResponse,
)
from api.services.gcs_client import upload_bytes_to_gcs, upload_text_to_gcs
from api.services.prompts_and_examples_service import (
    PromptDeleteRequest,
    PromptRegisterRequest,
    PromptUpdateRequest,
    build_examples_yaml,
    build_examples_yaml_by_product,
    build_prompt_yaml,
    build_prompt_yaml_by_product,
    build_prompt_yaml_by_productV2,
    encode_user_queries_with_vertex,
    get_examples_by_product,
    get_prompt_by_product,
    send_delete_example,
    send_delete_prompt,
    send_register_example,
    send_register_prompt,
    send_register_promptV2,
    send_update_example,
    send_update_prompt,
    send_update_promptV2,
)

prompts_and_examples_router = APIRouter(prefix="/prompts_and_examples")

_ENV_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
_ENV_REGION = os.environ.get("GOOGLE_CLOUD_LOCATION")
_ENV_MODEL_NAME = os.environ.get("GOOGLE_GEMINI_MODEL_NAME")

"""
    Secion de Gestion de Prompts
"""


@prompts_and_examples_router.post(
    "/prompts/getPromptsByproduct",
    response_model=List[GetPromptsResponseByProduct],
    tags=["Prompts Mannagement"],
    summary="Subir Prompt General/SQL de Agente a GCS",
    description=(
        "Crea un archivo YAML de prompt (que incluye version, product, prompt_content, etc.) y lo sube a una ruta específica en GCS, devolviendo la URL."
    ),
)
def getListProjectByProduct(
    request_body: GetPromptsRequestByProduct,
) -> List[GetPromptsResponseByProduct]:
    """
    Obtiene todos los proyectos a los que un usuario tiene acceso (directo o heredado),
    filtrando por el user_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Extrae y valida el user_id del cuerpo
        product_id = request_body.product_id

        # Llama a la función de servicio
        return get_prompt_by_product(product_id=product_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener proyectos: {e}")


@prompts_and_examples_router.post(
    "/prompts/upload",
    response_model=UploadPromptResponse,
    tags=["Prompts Mannagement"],
    summary="Subir Prompt General/SQL de Agente a GCS",
    description=(
        "Crea un archivo YAML de prompt (que incluye version, product, prompt_content, etc.) y lo sube a una ruta específica en GCS, devolviendo la URL."
    ),
)
async def upload_prompt(req: UploadPromptRequest):
    yaml_text = build_prompt_yaml(
        req.version, req.product, req.prompt_name, req.description, req.prompt_content
    )
    url = upload_text_to_gcs(
        req.bucket_name, req.object_path, yaml_text, content_type="text/yaml"
    )
    return UploadPromptResponse(status="success", url=url)


@prompts_and_examples_router.post(
    "/prompts/uploadByProduct",
    response_model=UploadPromptResponse,
    tags=["Prompts Mannagement"],
    summary="Generar y Subir Prompt de Agente a GCS por Product ID",
    description=(
        "Extrae la configuración del prompt de la BD por product_id, genera el YAML y lo sube a GCS."
    ),
)
async def upload_prompt_by_product_id(req: UploadPromptRequestByProduct):
    # 1. Extraer el prompt de la BD
    # Usamos la función que devuelve una lista, pero solo tomamos el primer prompt
    prompt_list = get_prompt_by_product(product_id=str(req.product_id))

    if not prompt_list:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró un prompt registrado para el product_id: {req.product_id}",
        )

    # Tomamos el primer prompt de la lista y la metadata
    prompt_data = prompt_list[0]

    # 2. Generar el YAML (Reconstruyendo el prompt a partir del diccionario)
    # Nota: Hardcodeamos la versión por convención, si es necesario, debería ser un campo de la BD
    yaml_text = build_prompt_yaml_by_product(
        version="1.0",
        product=prompt_data.name,  # Usamos el nombre del producto
        prompt_name=prompt_data.prompt_name,
        description=prompt_data.description
        or "Prompt de agente generado a partir de la configuración de BD.",
        config_prompt_dict=prompt_data.config_prompt,  # Pasamos el diccionario JSONB de la DB
        prompt_content=prompt_data.prompt_content,
    )

    # 3. Subir a GCS
    url = upload_text_to_gcs(
        req.bucket_name, req.object_path, yaml_text, content_type="text/yaml"
    )

    insert = ClientDeployRegisterRequest(
        product_id=str(req.product_id),
        bucket_config=req.bucket_name,
        gs_examples_agent=None,
        gs_prompt_agent=req.object_path,
        gs_prompt_sql=None,
        gs_profiling_agent=None,
        gs_metrics_config_agent=None,
        gs_semantic_config=None,
        client=None,
    )

    new_deploy_id = send_register_client_deploy_v2(insert)
    # 4. Devolver la respuesta
    return UploadPromptResponse(status="success", url=url)


@prompts_and_examples_router.post(
    "/prompts/sendRegisterPrompt",
    response_model=PromptCreationResponse,
    tags=["Prompts Mannagement"],
    summary="Registrar un Nuevo Prompt (CREATE)",
    description=(
        "Crea un nuevo registro de prompt en la base de datos. Asocia el prompt a un rol y/o producto específico."
    ),
)
def sendRegisterPrompt(prompt_data: PromptRegisterRequest) -> PromptCreationResponse:
    """Registra un nuevo prompt asociado a un producto."""
    try:
        print("pasoFinal01")
        prompt_id = send_register_prompt(prompt_data)
        print("pasoFinal")
        return PromptCreationResponse(id_prompt=prompt_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK y duplicados
        if "El producto con ID" in error_detail or "El rol con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )
        if "Este prompt ya tiene el rol especificado" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error en sendRegisterPrompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el prompt: {error_detail}",
        )


@prompts_and_examples_router.put(
    "/prompts/sendUpdatePrompt",
    response_model=PromptUpdateResponse,
    tags=["Prompts Mannagement"],
    summary="Actualizar un Prompt existente (Parcial)",
    description=(
        "Modifica los campos de un prompt existente, identificado por su id. Soporta la actualización parcial de los datos."
    ),
)
def updatePrompt(prompt_data: PromptUpdateRequest) -> PromptUpdateResponse:
    """Actualiza un prompt existente. Usa COALESCE en el SP."""
    try:
        rows_affected = send_update_prompt(prompt_data)

        # El SP de actualización (spu_minddash_app_update_prompt) no tiene una validación de 404
        # integrada con RAISE EXCEPTION, por lo que asumimos que si el SP no lanza excepción, es éxito.
        # Si quisieras la validación 404, debes agregar un RAISE EXCEPTION en el SP
        # si ROW_COUNT es 0.

        return PromptUpdateResponse(id_prompt=prompt_data.id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK (si se intenta cambiar el product_id a uno inexistente)
        if "El producto con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al actualizar el prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el prompt: {error_detail}",
        )


@prompts_and_examples_router.delete(
    "/prompts/sendDeletePrompt",
    response_model=PromptDeleteResponse,
    tags=["Prompts Mannagement"],
    summary="Eliminar un Prompt existente (DELETE)",
    description=(
        "Elimina el registro de prompt de la base de datos, identificado por su id."
    ),
)
def deletePrompt(prompt_data: PromptDeleteRequest) -> PromptDeleteResponse:
    """Elimina un prompt existente."""
    prompt_id = prompt_data.id
    try:
        send_delete_prompt(prompt_data)

        return PromptDeleteResponse(id_prompt=prompt_id)

    except Exception as e:
        error_detail = str(e)

        # Capturar el error 404 del RAISE EXCEPTION del SP
        if "El prompt con ID" in error_detail and "no existe" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al eliminar el prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el prompt: {error_detail}",
        )


"""
    Secion de Gestion de ejemplos
"""


@prompts_and_examples_router.post(
    "/examples/upload",
    response_model=BuildPromptsExamplesResponse,
    tags=["Examples Mannagement"],
    summary="Construir y Subir Few-shot Examples + Embeddings",
    description=(
        "Recibe una lista de pares user_query/sql_query, genera YAML de ejemplos y embeddings .npy (a través de Vertex AI), y los sube a GCS, devolviendo sus URLs."
    ),
)
async def build_prompts_examples(req: UploadPromptRequestByProduct):
    # 1) Construir YAML de ejemplos
    list_dicts: List[Dict[str, str]] = [e.model_dump() for e in req.examples]
    yaml_text = build_examples_yaml(list_dicts)

    # 2) Embeddings de user_query
    user_queries = [e.user_query for e in req.examples]
    # npy_bytes, metadata = encode_user_queries_to_npy_bytes(user_queries, model_name=req.model_name or 'paraphrase-multilingual-mpnet-base-v2')
    npy_bytes, metadata = encode_user_queries_with_vertex(
        texts=user_queries,
        project_id=_ENV_PROJECT_ID,
        region=_ENV_REGION,
        model_name=_ENV_MODEL_NAME,
    )
    # 3) Subir a GCS
    examples_yaml_url = upload_text_to_gcs(
        req.bucket_name, req.examples_yaml_path, yaml_text, content_type="text/yaml"
    )
    embeddings_npy_url = upload_bytes_to_gcs(
        req.bucket_name,
        req.embeddings_npy_path,
        npy_bytes,
        content_type="application/octet-stream",
    )

    insert = ClientDeployRegisterRequest(
        product_id=req.product_id,
        bucket_config=None,
        gs_examples_agent=embeddings_npy_url,
        gs_prompt_agent=None,
        gs_prompt_sql=None,
        gs_profiling_agent=None,
        gs_metrics_config_agent=None,
        gs_semantic_config=None,
        client=None,
    )
    new_deploy_id = send_register_client_deploy_v2(insert)

    return BuildPromptsExamplesResponse(
        status="success",
        examples_yaml_url=examples_yaml_url,
        embeddings_npy_url=embeddings_npy_url,
    )


@prompts_and_examples_router.post(
    "/examples/uploadByProduct",
    response_model=BuildPromptsExamplesResponse,
    tags=["Examples Mannagement"],
    summary="Construir y Subir Few-shot Examples + Embeddings por ID de Producto",
    description=(
        "Recibe un product_id, consulta la DB para obtener ejemplos, genera YAML y embeddings, y los sube a GCS, devolviendo sus URLs."
    ),
)
async def build_prompts_examples_by_product(req: BuildPromptsExamplesByProductRequest):
    # 1. Obtener ejemplos de la base de datos por product_id
    db_examples = get_examples_by_product(req.product_id)

    if not db_examples:
        # Manejar el caso de que no haya ejemplos
        return BuildPromptsExamplesResponse(
            status="warning",
            examples_yaml_url="",
            embeddings_npy_url="",
            message=f"No se encontraron ejemplos para el product_id: {req.product_id}",
        )

    # 2. Mapear y Construir YAML de ejemplos
    # Mapeamos 'name' -> 'user_query' y 'data_query' -> 'sql_query'
    list_dicts: List[Dict[str, str]] = [
        {"user_query": e.name, "sql_query": e.data_query} for e in db_examples
    ]
    yaml_text = build_examples_yaml_by_product(list_dicts)

    # 3. Embeddings de user_query
    # Usamos los campos mapeados (e.name)
    user_queries = [e.name for e in db_examples]
    npy_bytes, metadata = encode_user_queries_with_vertex(
        texts=user_queries,
        project_id=_ENV_PROJECT_ID,
        region=_ENV_REGION,
        model_name=_ENV_MODEL_NAME,
    )

    # 4. Subir a GCS
    examples_yaml_url = upload_text_to_gcs(
        req.bucket_name, req.examples_yaml_path, yaml_text, content_type="text/yaml"
    )

    insert = ClientDeployRegisterRequest(
        product_id=req.product_id,
        bucket_config=None,
        gs_examples_agent=req.examples_yaml_path,
        gs_prompt_agent=None,
        gs_prompt_sql=None,
        gs_profiling_agent=None,
        gs_metrics_config_agent=None,
        gs_semantic_config=None,
        client=None,
    )
    new_deploy_id = send_register_client_deploy_v2(insert)

    embeddings_npy_url = upload_bytes_to_gcs(
        req.bucket_name,
        req.embeddings_npy_path,
        npy_bytes,
        content_type="application/octet-stream",
    )

    return BuildPromptsExamplesResponse(
        status="success",
        examples_yaml_url=examples_yaml_url,
        embeddings_npy_url=embeddings_npy_url,
    )


@prompts_and_examples_router.post(
    "/examples/getListExamplesByProduct",
    response_model=List[ExampleListResponseItem],
    tags=["Examples Mannagement"],
    summary="Listar Ejemplos filtrados por ID de Producto",
    description=(
        "Obtiene una lista detallada de todos los ejemplos que están asociados a un product_id específico."
    ),
)
def getListExamplesByProduct(
    porudct_data: ExampleListRequest,
) -> List[ExampleListResponseItem]:
    """
    Obtiene todos los ejemplos asociados a un ID de producto específico.
    """
    product_id = porudct_data.product_id
    try:
        # Llama a la función de servicio para obtener los datos
        data_list = get_examples_by_product(product_id)

        # Si la lista está vacía, puedes devolver 404 o una lista vacía.
        # Devolver una lista vacía (200 OK) es el estándar REST para listas.
        if not data_list:
            # Opcional: Levantar 404 si el producto existe pero no tiene ejemplos
            # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No se encontraron ejemplos para el producto ID: {product_id}")
            return []

        # FastAPI y Pydantic se encargarán automáticamente de convertir
        # la lista de diccionarios (data_list) a la lista de ExampleListResponseItem
        return data_list

    except Exception as e:
        error_detail = str(e)

        # Manejo de error de formato UUID
        if "UUID" in error_detail and "invalid input syntax" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El product_id proporcionado tiene un formato UUID inválido: {product_id}",
            )

        print(f"Error en getListExamplesByProduct: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al obtener la lista de ejemplos: {error_detail}",
        )


@prompts_and_examples_router.post(
    "/examples/sendRegisterExample",
    response_model=ExampleCreationResponse,
    tags=["Examples Mannagement"],
    summary="Registrar un Nuevo Ejemplo asociado a un producto (CREATE)",
    description=(
        "Crea un nuevo registro de ejemplo en la base de datos. Requiere la asociación a un product_id válido."
    ),
)
def sendRegisterExample(
    example_data: ExampleRegisterRequest,
) -> ExampleCreationResponse:
    """Registra un nuevo ejemplo asociado a un producto."""
    try:
        example_id = send_register_example(example_data)
        return ExampleCreationResponse(id_example=example_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK (asumiendo que tu SP valida la FK de product_id y lanza un error)
        if "El producto con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error en sendRegisterExample: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el ejemplo: {error_detail}",
        )


@prompts_and_examples_router.put(
    "/examples/sendUpdateExample",
    response_model=ExampleUpdateResponse,
    tags=["Examples Mannagement"],
    summary="Actualizar un Ejemplo existente (Parcial)",
    description=(
        "Modifica campos de un registro de ejemplo existente, identificado por su id. Soporta actualizaciones parciales."
    ),
)
def updateExample(example_data: ExampleUpdateRequest) -> ExampleUpdateResponse:
    """Actualiza un ejemplo existente. Usa COALESCE en el SP."""
    try:
        # No necesitamos rows_affected si el SP no tiene validación de 404 (RAISE EXCEPTION si ROW_COUNT=0)
        send_update_example(example_data)

        return ExampleUpdateResponse(id_example=example_data.id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK si se intenta cambiar product_id (si el SP lo valida)
        if "El producto con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al actualizar el ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el ejemplo: {error_detail}",
        )


@prompts_and_examples_router.delete(
    "/examples/sendDeleteExample",
    response_model=ExampleDeleteResponse,
    tags=["Examples Mannagement"],
    summary="Eliminar un Ejemplo existente (DELETE)",
    description=(
        "Elimina el registro de ejemplo de la base de datos, identificado por su id."
    ),
)
def deleteExample(example_data: ExampleDeleteRequest) -> ExampleDeleteResponse:
    """Elimina un ejemplo existente."""
    example_id = example_data.id
    try:
        rows_affected = send_delete_example(example_data)

        # Si deseas validar 404 aquí, necesitas que el SP devuelva el ROW_COUNT
        # o que el SP lance una excepción si no se eliminó ninguna fila.
        # Si rows_affected == 0:
        #    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"El ejemplo con ID {example_id} no fue encontrado.")

        return ExampleDeleteResponse(id_example=example_id)

    except Exception as e:
        error_detail = str(e)

        # Si el SP lanza un error de 404 específico (como en tu prompt de prompts)
        if "El ejemplo con ID" in error_detail and "no existe" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al eliminar el ejemplo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el ejemplo: {error_detail}",
        )


@prompts_and_examples_router.post(
    "/prompts/sendRegisterPromptV2",
    response_model=PromptCreationResponse,
    tags=["Prompts Mannagement"],
    summary="Registrar un Nuevo Prompt (CREATE)",
    description=(
        "Crea un nuevo registro de prompt en la base de datos. Asocia el prompt a un rol y/o producto específico."
    ),
)
def sendRegisterPromptV2(
    prompt_data: PromptRegisterRequestV2,
) -> PromptCreationResponse:
    """Registra un nuevo prompt asociado a un producto."""
    try:
        prompt_id = send_register_promptV2(prompt_data)
        return PromptCreationResponse(id_prompt=prompt_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK y duplicados
        if "El producto con ID" in error_detail or "El rol con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )
        if "Este prompt ya tiene el rol especificado" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error en sendRegisterPrompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el prompt: {error_detail}",
        )


@prompts_and_examples_router.put(
    "/prompts/sendUpdatePromptV2",
    response_model=PromptUpdateResponse,
    tags=["Prompts Mannagement"],
    summary="Actualizar un Prompt existente (Parcial)",
    description=(
        "Modifica los campos de un prompt existente, identificado por su id. Soporta la actualización parcial de los datos."
    ),
)
def updatePromptV2(prompt_data: PromptUpdateRequestV2) -> PromptUpdateResponse:
    """Actualiza un prompt existente. Usa COALESCE en el SP."""
    try:
        rows_affected = send_update_promptV2(prompt_data)

        # El SP de actualización (spu_minddash_app_update_prompt) no tiene una validación de 404
        # integrada con RAISE EXCEPTION, por lo que asumimos que si el SP no lanza excepción, es éxito.
        # Si quisieras la validación 404, debes agregar un RAISE EXCEPTION en el SP
        # si ROW_COUNT es 0.

        return PromptUpdateResponse(id_prompt=prompt_data.id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de FK (si se intenta cambiar el product_id a uno inexistente)
        if "El producto con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        print(f"Error al actualizar el prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el prompt: {error_detail}",
        )


@prompts_and_examples_router.post(
    "/prompts/uploadByProductV2",
    response_model=UploadPromptResponse,
    tags=["Prompts Mannagement"],
    summary="Generar y Subir Prompt de Agente a GCS por Product ID",
    description=(
        "Extrae la configuración del prompt de la BD por product_id, genera el YAML y lo sube a GCS."
    ),
)
async def upload_prompt_by_product_idV2(req: UploadPromptRequestByProduct):
    # 1. Extraer el prompt de la BD
    # Usamos la función que devuelve una lista, pero solo tomamos el primer prompt
    prompt_list = get_prompt_by_product(product_id=str(req.product_id))

    if not prompt_list:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró un prompt registrado para el product_id: {req.product_id}",
        )

    # Tomamos el primer prompt de la lista y la metadata
    prompt_data = prompt_list[0]

    # 2. Generar el YAML (Reconstruyendo el prompt a partir del diccionario)
    # Nota: Hardcodeamos la versión por convención, si es necesario, debería ser un campo de la BD
    yaml_text = build_prompt_yaml_by_productV2(
        version="1.0",
        product=prompt_data.name,  # Usamos el nombre del producto
        prompt_name=prompt_data.prompt_name,
        description=prompt_data.description
        or "Prompt de agente generado a partir de la configuracion de BD.",
        config_prompt_dict=prompt_data.config_prompt,  # Pasamos el diccionario JSONB de la DB
        prompt_content=prompt_data.prompt_content,
    )

    # 3. Subir a GCS
    url = upload_text_to_gcs(
        req.bucket_name, req.object_path, yaml_text, content_type="text/yaml"
    )

    insert = ClientDeployRegisterRequest(
        product_id=str(req.product_id),
        bucket_config=req.bucket_name,
        gs_examples_agent=None,
        gs_prompt_agent=req.object_path,
        gs_prompt_sql=None,
        gs_profiling_agent=None,
        gs_metrics_config_agent=None,
        gs_semantic_config=None,
        client=None,
    )
    new_deploy_id = send_register_client_deploy_v2(insert)
    # 4. Devolver la respuesta
    return UploadPromptResponse(status="success", url=url)
