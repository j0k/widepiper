"""
Context processors для передачи глобальных переменных в шаблоны
"""

from .const import (
    MORALIS_API_KEY,
    MATTER_TOKEN_ADDRESS,
    IDEA_TOKEN_ADDRESS,
    WALLETCONNECT_PROJECT_ID,
)


def global_constants(request):
    """
    Передает глобальные константы в контекст всех шаблонов
    """
    return {
        'MORALIS_API_KEY': MORALIS_API_KEY,
        'MATTER_TOKEN_ADDRESS': MATTER_TOKEN_ADDRESS,
        'IDEA_TOKEN_ADDRESS': IDEA_TOKEN_ADDRESS,
        'WALLETCONNECT_PROJECT_ID': WALLETCONNECT_PROJECT_ID,
    }
