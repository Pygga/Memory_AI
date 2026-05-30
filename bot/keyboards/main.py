"""Keyboards for the bot."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Create main menu keyboard with reply buttons."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🆕 Начать новую книгу"),
                KeyboardButton(text="📖 Сгенерировать PDF")
            ],
            [
                KeyboardButton(text="📚 Архив книг"),
                KeyboardButton(text="💎 Профиль (Подписка)")
            ],
            [
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for help menu."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Как добавить воспоминание", callback_data="help_add"),
            ],
            [
                InlineKeyboardButton(text="📖 Как создать книгу", callback_data="help_book"),
            ],
            [
                InlineKeyboardButton(text="🏷️ Работа с тегами", callback_data="help_tags"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад в меню", callback_data="main_menu"),
            ]
        ]
    )
    return keyboard


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for confirmation actions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm_no")
            ]
        ]
    )
    return keyboard


def get_memory_actions_keyboard(memory_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for memory actions."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{memory_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{memory_id}")
            ]
        ]
    )
    return keyboard


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Create simple back button."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back")
            ]
        ]
    )
    return keyboard


def get_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for main menu (for edit_text compatibility)."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Добавить воспоминание", callback_data="menu_add"),
                InlineKeyboardButton(text="📚 Мои воспоминания", callback_data="menu_list")
            ],
            [
                InlineKeyboardButton(text="📖 Создать книгу", callback_data="menu_book"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")
            ]
        ]
    )
    return keyboard

def get_theme_selection_keyboard(story_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for selecting book theme."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📖 Классический (Строгий)", callback_data=f"generate_book_{story_id}_classic")
            ],
            [
                InlineKeyboardButton(text="✨ Современный (Яркий)", callback_data=f"generate_book_{story_id}_modern")
            ],
            [
                InlineKeyboardButton(text="👔 Деловой (Минимализм)", callback_data=f"generate_book_{story_id}_business")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="back")
            ]
        ]
    )
    return keyboard

def get_stories_keyboard(stories: list) -> InlineKeyboardMarkup:
    """Create inline keyboard for selecting a story."""
    buttons = []
    for story in stories:
        status = "🟢" if story.is_active else "⚪"
        buttons.append([InlineKeyboardButton(text=f"{status} {story.title}", callback_data=f"select_story_{story.id}")])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
