from fastapi import APIRouter, HTTPException
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
    
    # {field_name: translated_text} 형태로 변환
    result = {row["field_name"]: row["translated_text"] for row in response.data}
    return result