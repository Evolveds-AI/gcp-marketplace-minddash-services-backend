from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.models.product_models import (
    Product,
    ProductByUser,
    ProductCreationAccessResponse,
    ProductCreationResponse,
    ProductDeleteAccessRequest,
    ProductDeleteAccessResponse,
    ProductDeleteRequest,
    ProductDeleteResponse,
    ProductRegisterAccessRequest,
    ProductRegisterRequest,
    ProductUpdateAccessRequest,
    ProductUpdateAccessResponse,
    ProductUpdateRequest,
    ProductUpdateResponse,
)
from api.services.product_service import (
    get_list_product,
    get_list_products_by_prd,
    get_list_products_by_user,
    send_delete_access_product,
    send_delete_product,
    send_register_access_product,
    send_register_product,
    send_update_access_product,
    send_update_product,
)

product_router = APIRouter(prefix="/products")


class GetProductRequest(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las organizaciones."
    )


class GetProductRequestByPrd(BaseModel):
    """
    Modelo para validar el cuerpo de la solicitud que contiene el ID de usuario.
    """

    user_id: str = Field(
        ..., description="UUID del usuario para el cual se buscan las organizaciones."
    )
    product_id: str = Field(
        ..., description="UUID del producto por el que se filtrara la data."
    )


@product_router.get(
    "/getListProduct",
    response_model=List[Product],
    tags=["Products Management"],
    summary="Listar Todos los Productos",
    description="Obtiene una lista completa de todos los productos registrados en el sistema.",
)
def getListProduct() -> List[Product]:
    try:
        return get_list_product()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@product_router.post(
    "/getListProductByUser",
    response_model=List[ProductByUser],
    tags=["Products Management"],
    summary="Listar Productos por Usuario",
    description="Obtiene la lista de productos a los que un `user_id` específico tiene acceso (directo o heredado), filtrando por el ID de usuario proporcionado en el cuerpo de la solicitud.",
)
def getListProductByUser(request_body: GetProductRequest) -> List[ProductByUser]:
    """
    Obtiene todos los productos a los que un usuario tiene acceso (directo o heredado),
    filtrando por el user_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Extrae y valida el user_id del cuerpo
        user_id = request_body.user_id

        # Llama a la función de servicio
        return get_list_products_by_user(user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener productos: {e}")


@product_router.post(
    "/getListProductByPrd",
    response_model=List[Product],
    tags=["Products Management"],
    summary="Obtener Producto por ID",
    description="Recupera los detalles de un producto específico utilizando su `product_id`. Incluye validación de acceso por `user_id`.",
)
def getListProductByPrd(request_body: GetProductRequestByPrd) -> List[Product]:
    """
    Obtiene todos los productos a los que un usuario tiene acceso (directo o heredado),
    filtrando por el user_id proporcionado en el cuerpo de la solicitud.
    """
    try:
        # Extrae y valida el user_id del cuerpo
        product_id = request_body.product_id
        user_id = request_body.user_id

        # Llama a la función de servicio
        return get_list_products_by_prd(product_id=product_id, user_id=user_id)

    except Exception as e:
        # Manejo de errores
        raise HTTPException(status_code=500, detail=f"Error al obtener productos: {e}")


@product_router.post(
    "/sendRegistroProduct",
    response_model=ProductCreationResponse,
    tags=["Products Management"],
    summary="Registrar Nuevo Producto (CREATE)",
    description="Crea un nuevo registro de producto en la base de datos.",
)
def sendRegistroProduct(
    product_data: ProductRegisterRequest,
) -> ProductCreationResponse:
    try:
        # Llama a la función de servicio con los datos de registro
        result_message = send_register_product(product_data)

        # Construir y retornar la respuesta
        return ProductCreationResponse(id_product=result_message)

    except Exception as e:
        # Manejo de errores
        print(f"Error en sendRegistroProduct: {e}")
        # Puedes añadir un manejo específico si el error es de violación de restricción, etc.
        raise HTTPException(
            status_code=500, detail=f"Error al registrar la organización: {e}"
        )


@product_router.put(
    "/updateProduct",
    response_model=ProductUpdateResponse,
    tags=["Products Management"],
    summary="Actualizar Producto (UPDATE)",
    description="Modifica los datos de un producto existente. Devuelve error 404 si el producto no existe.",
)
def updateProduct(product_data: ProductUpdateRequest) -> ProductUpdateResponse:
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe,
        #    lanza una excepción (RAISE EXCEPTION).
        #    Si el ID SÍ existe, devuelve -1 (rowcount).
        rows_affected = send_update_product(product_data)

        # 2. Si llegamos hasta aquí, NO hubo una excepción, por lo que la operación fue exitosa.
        #    No importa si rows_affected es 1 o -1.
        return ProductUpdateResponse(product_id=product_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        # Esto sucede cuando el ID no existe en la BD.
        if "No se puede actualizar. La organización con ID" in error_detail:
            # Aquí usamos el 404. El error_detail contiene el mensaje que generó el SP
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],  # Extrae solo el mensaje
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar la organización: {error_detail}",
        )


@product_router.delete(
    "/deleteProduct",
    response_model=ProductDeleteResponse,
    tags=["Products Management"],
    summary="Eliminar Producto (DELETE)",
    description="Elimina un producto del sistema usando su `id`. Devuelve error 404 si el producto no existe.",
)
def deleteProduct(product_data: ProductDeleteRequest) -> ProductDeleteResponse:
    prd_id = product_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_product(product_data)

        # Si llegamos aquí, NO hubo una excepción, la eliminación fue exitosa (rowcount = -1).
        return ProductDeleteResponse(product_id=prd_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP y convertirlo en 404
        if "No se puede eliminar. La organización con ID" in error_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la organización con ID: {prd_id} para eliminar.",
            )

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar la organización: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar la organización: {error_detail}",
        )


"""
    Bloque de Control a accesos de Productos:
"""


@product_router.post(
    "/sendAccessProduct",
    response_model=ProductCreationAccessResponse,
    tags=["Product Access"],
    summary="Otorgar Acceso a Producto (CREATE Permission)",
    description="Registra el acceso de un `user_id` a un `product_id` específico, asignándole un `role_id`.",
)
def sendAccessProduct(
    access_product_data: ProductRegisterAccessRequest,
) -> ProductCreationAccessResponse:
    """
    Registra el acceso de un usuario a una productos con un rol específico.
    Llama a spu_minddash_app_insert_user_prd_access.
    """
    try:
        # Llama a la función de servicio. Esta devuelve el nuevo UUID del registro.
        product_access_id = send_register_access_product(access_product_data)

        # Construir y retornar la respuesta exitosa
        return ProductCreationAccessResponse(product_access_id=product_access_id)

    except Exception as e:
        error_detail = str(e)

        # Manejo de errores específicos lanzados por el SP (ej. duplicados o FK inválidas)
        if (
            "El usuario con ID" in error_detail
            or "La productos con ID" in error_detail
            or "El rol con ID" in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )
        if (
            "Este usuario ya tiene el rol especificado en esta productos"
            in error_detail
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,  # Conflicto (ya existe)
                detail=error_detail.split("ERROR: ")[-1],
            )

        # Error genérico
        print(f"Error en sendAccessProduct: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar el accesso a la productos: {error_detail}",
        )


@product_router.put(
    "/updateAccessProduct",
    response_model=ProductUpdateAccessResponse,
    tags=["Product Access"],
    summary="Actualizar Acceso a Producto (UPDATE Permission)",
    description="Modifica un registro de acceso existente, permitiendo cambiar el rol (`role_id`) o reasignar el acceso. Devuelve error 404 si el registro de acceso no existe.",
)
def updateAccessProduct(
    access_product_data: ProductUpdateAccessRequest,
) -> ProductUpdateAccessResponse:
    """
    Actualiza el user_id, product_id y/o role_id de un registro de acceso existente.
    Llama a spu_minddash_app_update_user_prd_access.
    """
    try:
        # 1. Ejecutar el servicio. Si el SP encuentra que el ID NO existe, lanza una excepción.
        rows_affected = send_update_access_product(access_product_data)

        # 2. Si llegamos hasta aquí, la operación fue exitosa.
        return ProductUpdateAccessResponse(product_access_id=access_product_data.id)

    except Exception as e:
        error_detail = str(e)

        # 3. Capturar el error del RAISE EXCEPTION del SP (ID no existe o FK inválida)
        if "No se puede actualizar. El registro de acceso con ID" in error_detail:
            # El registro de acceso a actualizar no existe (404)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        elif (
            "El usuario con ID" in error_detail
            or "La productos con ID" in error_detail
            or "El nuevo rol con ID" in error_detail
        ):
            # FK inválida (400)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail.split("ERROR: ")[-1],
            )

        # 4. Cualquier otro error no manejado
        print(f"Error al actualizar el acceso a la productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al actualizar el acceso a la productos: {error_detail}",
        )


@product_router.delete(
    "/deleteAccessProduct",
    response_model=ProductDeleteAccessResponse,
    tags=["Product Access"],
    summary="Revocar Acceso a Producto (DELETE Permission)",
    description="Elimina el registro de acceso, revocando los permisos del usuario para el producto específico. Devuelve error 404 si el registro de acceso no existe.",
)
def deleteAccessProduct(
    access_product_data: ProductDeleteAccessRequest,
) -> ProductDeleteAccessResponse:
    """
    Elimina un registro de acceso de usuario a productos.
    Llama a spu_minddash_app_delete_user_prd_access.
    """
    prd_access_id = access_product_data.id
    try:
        # Llama al servicio. Si el ID no existe, el SP lanza una excepción.
        send_delete_access_product(access_product_data)

        # Si llegamos aquí, la eliminación fue exitosa.
        return ProductDeleteAccessResponse(product_access_id=prd_access_id)

    except Exception as e:
        error_detail = str(e)

        # 1. Capturar el error del RAISE EXCEPTION del SP (Registro no existe)
        if "No se puede eliminar. El registro de acceso con ID" in error_detail:
            # Aquí usamos 404. El error_detail contiene el mensaje que generó el SP.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail.split("ERROR: ")[-1],
            )
        # Nota: Adapté el string de búsqueda al mensaje de error del SP de DELETE proporcionado.

        # 2. Cualquier otro error no manejado
        print(f"Error al eliminar el acceso a la productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al eliminar el acceso a la productos: {error_detail}",
        )
