import logging
from typing import List

from api.models.user_models import (
    UserBaseInfoResponse,
)
from api.utils.db_client import query_all

logger = logging.getLogger(__name__)


def get_list_info_by_user(user_id: str) -> List[UserBaseInfoResponse]:
    """
    Obtiene la lista consolidada de proyectos a los que un usuario tiene acceso
    (directo, o heredado de producto).
    """
    query_str = f"""
        select 
            user_id,username,email,password_hash,email_verified,
            is_active,failed_attempts,locked_until,created_at,
            updated_at,primary_chatbot_id,can_manage_users,
            phone_number,is_active_whatsapp,role_acceso_data_id,
            role_id,role_name,role_type,role_description
        from view_info_user_details
        WHERE
            user_id = '{user_id}'
    """
    rows = query_all(query_str)

    # Mapeo de los resultados de la DB al modelo Pydantic
    return [UserBaseInfoResponse(**r) for r in rows]
