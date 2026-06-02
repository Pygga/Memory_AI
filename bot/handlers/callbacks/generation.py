"""PDF generation callback handlers: theme selection, signature, book generation."""
from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from loguru import logger

from bot.config import settings
from bot.keyboards.main import get_story_actions_keyboard
from bot.states import StoryStates


async def start_book_generation(message: Message, user_tg_id: int, story_id: int, theme: str, signature: str = None) -> None:
    """Helper to enqueue book generation task using arq."""
    status_msg = await message.answer(
        "⏳ <b>Запрос поставлен в очередь...</b>\n\n"
        "Ожидаем освобождения ИИ-воркера на сервере сборки."
    )
    
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        arq_pool = await create_pool(redis_settings)
        
        # Enqueue the background task
        await arq_pool.enqueue_job(
            'generate_book_task',
            user_tg_id,
            story_id,
            theme,
            signature,
            status_msg.message_id
        )
        logger.info(f"Enqueued generate_book_task for user {user_tg_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}")
        await status_msg.edit_text("❌ Ошибка при отправке книги в очередь. Попробуйте еще раз.")


async def handle_select_theme(callback: CallbackQuery) -> None:
    """Handle selecting theme after choosing PDF generation."""
    story_id = int(callback.data.replace("select_theme_", ""))
    from bot.keyboards.main import get_theme_selection_keyboard
    from bot.services.book_generator import validate_story_memories
    from db.database import get_session_factory
    
    session_factory = get_session_factory()
    is_valid, err_msg = await validate_story_memories(story_id, callback.from_user.id, session_factory)
    if not is_valid:
        await callback.message.edit_text(
            err_msg,
            reply_markup=get_story_actions_keyboard(story_id)
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🎨 <b>Выберите дизайн вашей книги:</b>\n\n"
        "• <b>Классический</b> - строгий стиль, шрифты с засечками.\n"
        "• <b>Современный</b> - яркий, с градиентами и закруглениями.\n"
        "• <b>Деловой</b> - строгий минимализм.",
        reply_markup=get_theme_selection_keyboard(story_id)
    )
    await callback.answer()


async def handle_generate_book_theme(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle theme selection and ask for custom signature."""
    # data is like 'generate_book_{story_id}_{theme}'
    parts = callback.data.split('_')
    story_id = int(parts[2])
    theme = parts[3]
    
    # Store in FSM state
    await state.update_data(story_id=story_id, theme=theme)
    await state.set_state(StoryStates.waiting_for_signature)
    
    from bot.keyboards.main import get_skip_signature_keyboard
    
    await callback.message.edit_text(
        "✍️ <b>Добавьте финальную подпись для вашей книги!</b>\n\n"
        "Она будет напечатана на последней странице вместо статистики.\n"
        "Например: <i>«С любовью, твоя семья»</i>, <i>«Жизнь измеряется не количеством вдохов, а моментами, от которых захватывает дух»</i> или просто ваши имена.\n\n"
        "<b>Напишите текст подписи прямо в чат</b> или нажмите кнопку ниже, чтобы пропустить этот шаг.",
        reply_markup=get_skip_signature_keyboard()
    )
    await callback.answer()
    logger.info(f"User {callback.from_user.id} selected theme {theme} for story {story_id}, waiting for signature")


async def handle_skip_signature(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle skipping the custom signature and starting book generation."""
    state_data = await state.get_data()
    story_id = state_data.get("story_id")
    theme = state_data.get("theme")
    
    if not story_id or not theme:
        await callback.message.edit_text("❌ Произошла ошибка. Пожалуйста, начните генерацию заново.")
        await state.clear()
        await callback.answer()
        return
        
    await state.clear()
    
    # Delete the prompt message to keep chat clean
    await callback.message.delete()
    
    # Start generation with signature = None
    await start_book_generation(callback.message, callback.from_user.id, story_id, theme, signature=None)
    await callback.answer()


def register_generation_handlers(dp: Dispatcher) -> None:
    """Register PDF generation callback handlers."""
    dp.callback_query.register(handle_select_theme, F.data.startswith("select_theme_"))
    dp.callback_query.register(handle_generate_book_theme, F.data.startswith("generate_book_"))
    dp.callback_query.register(handle_skip_signature, F.data == "skip_signature")
