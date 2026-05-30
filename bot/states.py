from aiogram.fsm.state import State, StatesGroup

class StoryStates(StatesGroup):
    waiting_for_story_title = State()
