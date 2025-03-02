from aiogram import Router
from .help import help_router
from .start import start_router
from .message import message_router
from .stats import stats_router
from .top import top_router

main_router = Router(name='main_router')
main_router.include_router(start_router)
main_router.include_router(help_router)
main_router.include_router(stats_router)
main_router.include_router(top_router)

# should be the last one to trigger after all commands

main_router.include_router(message_router)