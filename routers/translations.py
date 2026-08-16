from fastapi import APIRouter, HTTPException, Query
from database import supabase

router = APIRouter()


@router.get("/api/translations/{entity_type}/{entity_id}")
def get_translations(entity_type: str, entity_id: str, lang: str = "en"):
    if entity_type not in ["hospital", "tourist", "accommodation"]:
        raise HTTPException(status_code=400, detail="잘못된 entity_type")

    response = supabase.table("translate")\
        .select("field_name, translated_text")\
        .eq("entity_type", entity_type)\
        .eq("entity_id", entity_id)\
        .eq("lang_code", lang)\
        .execute()

    result = {row["field_name"]: row["translated_text"] for row in response.data}
    return result


@router.get("/api/translations/{entity_type}")
def get_translations_bulk(entity_type: str, ids: str = Query(...), lang: str = "en"):
    if entity_type not in ["hospital", "tourist", "accommodation"]:
        raise HTTPException(status_code=400, detail="잘못된 entity_type")

    id_list = ids.split(",")
    response = supabase.table("translate")\
        .select("entity_id, field_name, translated_text")\
        .eq("entity_type", entity_type)\
        .in_("entity_id", id_list)\
        .eq("lang_code", lang)\
        .execute()

    result = {}
    for row in response.data:
        result.setdefault(row["entity_id"], {})[row["field_name"]] = row["translated_text"]
    return result