"""Keyboards for the bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



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


def get_back_to_help_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with a back button leading to help menu."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="menu_help")
            ]
        ]
    )
    return keyboard


def get_main_menu_inline_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for main menu."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🆕 Начать новую книгу", callback_data="menu_new_book")
            ],
            [
                InlineKeyboardButton(text="📚 Мои книги", callback_data="menu_book")
            ],
            [
                InlineKeyboardButton(text="👤 Профиль и подписка", callback_data="menu_profile")
            ],
            [
                InlineKeyboardButton(text="❓ Справка", callback_data="menu_help")
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
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_skip_signature_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard to skip final signature."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏩ Пропустить (без подписи)", callback_data="skip_signature")
            ],
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="back")
            ]
        ]
    )
    return keyboard

def get_story_actions_keyboard(story_id: int, is_active: bool = False) -> InlineKeyboardMarkup:
    """Create inline keyboard for book (story) actions cabinet."""
    buttons = [
        [
            InlineKeyboardButton(text="📖 Читать / Редактировать главы", callback_data=f"manage_chaps_{story_id}")
        ]
    ]
    
    if not is_active:
        buttons.append([
            InlineKeyboardButton(text="📌 Сделать книгу текущей", callback_data=f"set_active_{story_id}")
        ])
        
    buttons.extend([
        [
            InlineKeyboardButton(text="🖨️ Сгенерировать PDF-книгу", callback_data=f"select_theme_{story_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 Пересобрать книгу заново", callback_data=f"rebuild_story_{story_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 К списку книг", callback_data="menu_book")
        ]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chapters_list_keyboard(chapters: list, story_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for list of chapters."""
    buttons = []
    for chapter in chapters:
        buttons.append([InlineKeyboardButton(
            text=f"Глава {chapter.chapter_number}. {chapter.title}",
            callback_data=f"view_chap_{chapter.id}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 В меню книги", callback_data=f"select_story_{story_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_chapter_editor_keyboard(chapter_id: int, story_id: int) -> InlineKeyboardMarkup:
    """Create inline keyboard for editing a specific chapter."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_chap_{chapter_id}"),
                InlineKeyboardButton(text="🔄 Перегенерировать ИИ", callback_data=f"regen_chap_{chapter_id}")
            ],
            [
                InlineKeyboardButton(text="🔙 К списку глав", callback_data=f"manage_chaps_{story_id}")
            ]
        ]
    )
    return keyboard
