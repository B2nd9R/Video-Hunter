from .commands import setup as setup_commands
from .messages import setup as setup_messages
from .callbacks import setup as setup_callbacks

__all__ = [
    'setup_commands',
    'setup_messages',
    'setup_callbacks'
]

def setup_all(application):
    """تسجيل جميع ال handlers"""
    setup_commands(application)
    setup_messages(application)
    setup_callbacks(application)