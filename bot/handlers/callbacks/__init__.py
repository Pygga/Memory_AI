"""Callback handlers package — split by domain for maintainability.

Submodules:
    navigation  — help screens, back button, main menu, confirmations
    stories     — story list, story cabinet selection
    chapters    — chapter viewing, editing, regeneration, rebuild
    generation  — theme selection, signature, PDF enqueue
"""
from aiogram import Dispatcher

from bot.handlers.callbacks.navigation import register_navigation_handlers
from bot.handlers.callbacks.stories import register_stories_handlers
from bot.handlers.callbacks.chapters import register_chapters_handlers
from bot.handlers.callbacks.generation import register_generation_handlers

# Re-export start_book_generation so text.py can import it
from bot.handlers.callbacks.generation import start_book_generation  # noqa: F401


def register_callback_handlers(dp: Dispatcher) -> None:
    """Register all callback query handlers from submodules.
    
    This is the single entry point called from bot/main.py.
    No changes to main.py are required.
    """
    register_navigation_handlers(dp)
    register_stories_handlers(dp)
    register_chapters_handlers(dp)
    register_generation_handlers(dp)
