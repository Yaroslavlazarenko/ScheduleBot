from .common import common_router
from .user import user_router
from .schedule import schedule_router
from .inline import inline_router
from .teacher import teacher_router
from .settings import settings_router
from .subject import subject_router
from .admin import admin_router

__all__ = [
    'common_router',
    'user_router',
    'schedule_router',
    'inline_router',
    'teacher_router',
    'settings_router',
    'subject_router',
    'admin_router'
]