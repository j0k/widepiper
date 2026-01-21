from .models import Block
from uuid import uuid4

from .dex.dex import get_token_priceBCS
from .const import IDEA_TOKEN_ADDRESS


def get_current_or_create_open_block():
    open_block = Block.objects.filter(state=1).order_by("id").last()
    if open_block is None:
        prev_block = Block.objects.order_by("id").last()
        if prev_block is not None:
            prev_block_hash = prev_block.block_hash
        else:
            prev_block_hash = None
        idea_price = get_token_priceBCS(IDEA_TOKEN_ADDRESS)
        open_block = Block.objects.create(
            block_hash=uuid4().hex,
            prev_block_hash=prev_block_hash,
            idea_price=idea_price,
        )
    return open_block
