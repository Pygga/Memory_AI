from loguru import logger
from db.repositories import UserRepository, LLMLogRepository

async def log_llm_usage(user_id_tg: int, story_id: int, provider: str, model_name: str, prompt_t: int, completion_t: int, session_factory) -> None:
    """Calculates expenses in USD on AI tokens and writes to DB."""
    if provider == "groq":
        # $0.59 input, $0.79 output per million tokens (llama-3.3-70b)
        cost = (prompt_t * 0.59 / 1_000_000) + (completion_t * 0.79 / 1_000_000)
    else:
        # $13 per million tokens (GigaChat Pro)
        cost = ((prompt_t + completion_t) * 13.0 / 1_000_000)

    try:
        async with session_factory() as session:
            user_repo = UserRepository(session)
            user_record = await user_repo.get_by_telegram_id(user_id_tg)
            if not user_record:
                logger.warning(f"Could not find user in database for telegram_id: {user_id_tg}")
                return

            llm_log_repo = LLMLogRepository(session)
            await llm_log_repo.create(
                user_id=user_record.id,
                story_id=story_id,
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                cost_usd=cost
            )
            await session.commit()
            logger.info(f"📊 LLM expense logged for user {user_id_tg}: {prompt_t+completion_t} tokens, cost: ${cost:.6f}")
    except Exception as e:
        logger.error(f"Failed to write LLM usage logs: {e}")
