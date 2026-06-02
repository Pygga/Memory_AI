"""Semantic memory grouper utilizing LLM factory to group memories into logical chapters."""
import json
import re
from loguru import logger
from typing import List, Dict
from db.models import Memory
from bot.services.story_maker import get_llm_client

async def group_memories_semantically(memories: List[Memory], client=None) -> List[Dict]:
    """
    Groups memories into 3-5 logical chapters semantically using LLM.
    
    Returns:
        List of dicts: [{"title": "Chapter Title", "memory_ids": [1, 2, ...]}]
    """
    if not memories:
        return []
        
    if not client:
        client = get_llm_client()
    
    system_prompt = (
        "Ты — профессиональный редактор книг воспоминаний.\n"
        "Твоя задача — проанализировать список воспоминаний пользователя и распределить их на 3-5 логических и последовательных глав.\n"
        "Объединяй воспоминания в одну главу, если они близки по теме, событию, смыслу или эмоциям. "
        "Главы должны идти в логическом хронологическом порядке.\n\n"
        "ВАЖНО: Ответь СТРОГО в формате JSON. Никакого постороннего текста, вводных слов или markdown-оформления (кроме JSON-массива).\n"
        "Формат ответа:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Изящное и поэтичное название первой главы (3-5 слов, отражающих суть)\",\n"
        "    \"memory_ids\": [идентификаторы воспоминаний, входящих в эту главу]\n"
        "  },\n"
        "  ...\n"
        "]"
    )
    
    # Format memories list for the LLM
    memories_data = []
    for m in memories:
        date_str = m.created_at.strftime('%d.%m.%Y %H:%M')
        # Simple content preview
        content_preview = m.content[:150] + "..." if len(m.content or "") > 150 else (m.content or "")
        if m.memory_type == 'photo':
            content_preview = f"[ФОТОГРАФИЯ] {content_preview}"
            
        tags_str = ", ".join(m.tags) if m.tags else "нет"
        memories_data.append(f"- [ID: {m.id}] Дата: {date_str} | Теги: {tags_str} | Текст: {content_preview}")
        
    user_prompt = "Сгруппируй следующие воспоминания по главам:\n\n" + "\n".join(memories_data)
    
    try:
        logger.info(f"Grouping {len(memories)} memories semantically using LLM")
        response = await client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3, # Low temperature for strict JSON output
            max_tokens=2000
        )
        
        # Clean response to parse JSON
        cleaned_response = response.strip()
        # Strip markdown fences if present
        if cleaned_response.startswith("```"):
            # find first [ and last ]
            match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(0)
                
        chapters_data = json.loads(cleaned_response)
        
        # Validate structure
        if isinstance(chapters_data, list) and len(chapters_data) > 0:
            validated_chapters = []
            for item in chapters_data:
                if isinstance(item, dict) and "title" in item and "memory_ids" in item:
                    validated_chapters.append({
                        "title": str(item["title"]).strip().strip('*').strip('_').strip('"').strip("'"),
                        "memory_ids": [int(mid) for mid in item["memory_ids"]]
                    })
            if validated_chapters:
                logger.info(f"Successfully grouped memories into {len(validated_chapters)} semantic chapters")
                return validated_chapters
                
    except Exception as e:
        logger.error(f"Failed to group memories semantically: {e}. Falling back to calendar week grouping.")
        
    return []
