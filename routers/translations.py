from fastapi import APIRouter, HTTPException, Query
from database import supabase

router = APIRouter()

VALID_ENTITY_TYPES = ["hospital", "tourist", "accommodation"]


@router.get("/api/translations/{entity_type}/{entity_id}")
def get_translations(entity_type: str, entity_id: str, lang: str = "en"):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="잘못된 entity_type")

    # DB(translate 테이블)에는 translate.py 배치가 저장할 때 entity_type을 대문자
    # (예: "HOSPITAL")로 넣어놨다 - 프론트/이 API는 소문자("hospital")로 주고받으므로,
    # 조회 직전에만 대문자로 바꿔서 DB와 맞춘다. API 계약(소문자)은 그대로 유지한다.
    response = supabase.table("translate")\
        .select("field_name, translated_text")\
        .eq("entity_type", entity_type.upper())\
        .eq("entity_id", entity_id)\
        .eq("lang_code", lang)\
        .execute()

    result = {row["field_name"]: row["translated_text"] for row in response.data}
    return result


@router.get("/api/translations/{entity_type}")
def get_translations_bulk(entity_type: str, ids: str = Query(...), lang: str = "en"):
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="잘못된 entity_type")

    id_list = ids.split(",")
    response = supabase.table("translate")\
        .select("entity_id, field_name, translated_text")\
        .eq("entity_type", entity_type.upper())\
        .in_("entity_id", id_list)\
        .eq("lang_code", lang)\
        .execute()

    result = {}
    for row in response.data:
        result.setdefault(row["entity_id"], {})[row["field_name"]] = row["translated_text"]
    return result