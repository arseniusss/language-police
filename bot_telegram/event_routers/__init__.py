from aiogram import Router
from .chat_events import chat_events_router

main_event_router = Router(name='main_event_router')
main_event_router.include_router(chat_events_router)