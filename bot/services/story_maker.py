import os
import hashlib
import redis.asyncio as redis_async
from typing import List
from loguru import logger
from db.models import Memory
from bot.services.llm import GigaChatClient, GroqClient, BaseLLMClient

def get_llm_client() -> BaseLLMClient:
    """Factory to get the configured LLM client."""
    provider = os.getenv("LLM_PROVIDER", "gigachat").lower()
    if provider == "groq":
        return GroqClient()
    return GigaChatClient()

async def generate_chapter_story(memories: List[Memory], week_date_str: str, client: BaseLLMClient = None) -> tuple[str, bool]:
    """
    Generate a cohesive story for a week of memories using an LLM.
    
    Args:
        memories: List of Memory objects for the week.
        week_date_str: Formatted string representing the start of the week.
        
    Returns:
        A tuple of (generated_story_string, is_fallback_boolean).
    """
    # Filter out empty memories unless they are photos
    text_memories = [m for m in memories if (m.content and m.content.strip()) or m.memory_type == 'photo']
    
    if not text_memories:
        return "", False
        
    if not client:
        client = get_llm_client()
    
    system_prompt = (
        "Ты профессиональный писатель, который пишет автобиографическую книгу воспоминаний. "
        "Твоя задача — взять разрозненные заметки, мысли, события и фотографии за неделю и "
        "объединить их в красивый, связный и душевный рассказ.\n\n"
        "Правила:\n"
        "1. Пиши строго от первого лица ('Я', 'Мы', 'Мой').\n"
        "2. Не выдумывай факты и события, которых нет в заметках. Используй только предоставленную информацию.\n"
        "3. Добавляй художественности, эмоций и размышлений.\n"
        "4. Пиши грамотно, дели текст на абзацы для удобства чтения.\n"
        "5. Игнорируй технические теги, если они не несут смысловой нагрузки.\n"
        "6. ВАЖНО: Если в списке есть ФОТОГРАФИИ, ты ОБЯЗАН вставить их в свой текст в подходящих по смыслу местах! "
        "Для вставки фото используй точный маркер, который указан, например: [PHOTO:123]. Не изменяй этот тег.\n"
        "7. ВАЖНО: В самом начале своего ответа напиши красивое, поэтичное и цепляющее название для этой главы, отражающее её суть, "
        "в формате: '# Название главы'. Название должно быть коротким (3-5 слов), без кавычек и без слова 'Глава' или даты."
    )
    
    # Format memories into a text block
    memories_text = f"События за неделю (начиная с {week_date_str}):\n\n"
    for m in text_memories:
        tags = " ".join([f"#{t}" for t in m.tags]) if m.tags else ""
        date_str = m.created_at.strftime('%d.%m.%Y %H:%M')
        if m.memory_type == 'photo':
            caption = f" с подписью: '{m.content}'" if m.content else " без подписи"
            memories_text += f"- [{date_str}] ФОТОГРАФИЯ [PHOTO:{m.id}]{caption} {tags}\n"
        else:
            memories_text += f"- [{date_str}] Текст: {m.content} {tags}\n"
            
    # Hash for caching
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = redis_async.from_url(redis_url)
    
    cache_key = f"story:{hashlib.sha256(memories_text.encode()).hexdigest()}"
    
    try:
        cached_story = await redis_client.get(cache_key)
        if cached_story:
            logger.info(f"Using cached story for week {week_date_str}")
            await redis_client.aclose()
            return cached_story.decode('utf-8'), False
    except Exception as e:
        logger.warning(f"Redis cache error: {e}")
        
    # Adjust max_tokens based on memories count
    # roughly 150 tokens per memory + 500 base
    max_tokens = min(3000, 500 + len(text_memories) * 150)
    
    try:
        logger.info(f"Generating story for week {week_date_str} ({len(text_memories)} memories)")
        story = await client.generate_text(
            system_prompt=system_prompt,
            user_prompt=memories_text,
            temperature=0.7,
            max_tokens=max_tokens
        )
        
        try:
            await redis_client.set(cache_key, story, ex=86400 * 30) # 30 days
            await redis_client.aclose()
        except Exception as e:
            logger.warning(f"Failed to cache story: {e}")
            
        return story, False
    except Exception as e:
        logger.error(f"Failed to generate story for week {week_date_str}: {e}")
        # Fallback to simple text if LLM fails
        logger.info("Using fallback text concatenation.")
        fallback_text = ""
        for m in text_memories:
            date_str = m.created_at.strftime('%d.%m.%Y')
            fallback_text += f"[{date_str}]\n{m.content}\n\n"
        return fallback_text, True
