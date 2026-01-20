from .get_tickers import *
from .args import *
from .tools import *
from .fundamentals import *
from .insider_trades import update_days
import asyncio

# Alias the function directly rather than redeclaring it
class update_form4_db:
    def __init__(self, *args, **kwargs):
        return asyncio.run(update_days(*args, **kwargs))

# Optionally define what happens on 'from package import *'
# __all__ = []