from .common import common_router
from .user import user_router
from .schedule import schedule_router
from .inline import inline_router

__all__ = [
    'common_router',
    'user_router',
    'schedule_router',
    'inline_router'
]