from aiogram import Router

from .help import help_router
from .start import start_router

main_router = Router(name='main_router')
main_router.include_router(start_router)
main_router.include_router(help_router)