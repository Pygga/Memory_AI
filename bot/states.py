from aiogram.fsm.state import State, StatesGroup

class StoryStates(StatesGroup):
    waiting_for_story_title = State()
    waiting_for_signature = State()
    waiting_for_chapter_edit = State()
