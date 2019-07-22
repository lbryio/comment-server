import re


def validate_channel(channel_id: str, channel_name: str):
    assert channel_id and channel_name
    assert type(channel_id) is str and type(channel_name) is str
    assert re.fullmatch(
        '^@(?:(?![\x00-\x08\x0b\x0c\x0e-\x1f\x23-\x26'
        '\x2f\x3a\x3d\x3f-\x40\uFFFE-\U0000FFFF]).){1,255}$',
        channel_name
    )
    assert re.fullmatch('[a-z0-9]{40}', channel_id)


def validate_base_comment(comment: str, claim_id: str, **kwargs):
    assert 0 < len(comment) <= 2000
    assert re.fullmatch('[a-z0-9]{40}', claim_id)


async def validate_signature(*args, **kwargs):
    pass

