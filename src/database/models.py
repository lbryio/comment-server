import json
import time

import logging
import math
import typing

from peewee import *
import nacl.hash

from src.server.validation import is_valid_base_comment
from src.misc import clean


class Channel(Model):
    claim_id = CharField(column_name='ClaimId', primary_key=True, max_length=40)
    name = CharField(column_name='Name', max_length=256)

    class Meta:
        table_name = 'CHANNEL'


class Comment(Model):
    comment = CharField(column_name='Body', max_length=2000)
    channel = ForeignKeyField(
        backref='comments',
        column_name='ChannelId',
        field='claim_id',
        model=Channel,
        null=True
    )
    comment_id = CharField(column_name='CommentId', primary_key=True, max_length=64)
    is_hidden = BooleanField(column_name='IsHidden', constraints=[SQL("DEFAULT 0")])
    claim_id = CharField(max_length=40, column_name='LbryClaimId')
    parent = ForeignKeyField(
        column_name='ParentId',
        field='comment_id',
        model='self',
        null=True,
        backref='replies'
    )
    signature = CharField(max_length=128, column_name='Signature', null=True, unique=True)
    signing_ts = TextField(column_name='SigningTs', null=True)
    timestamp = IntegerField(column_name='Timestamp')

    class Meta:
        table_name = 'COMMENT'
        indexes = (
            (('channel', 'comment_id'), False),
            (('claim_id', 'comment_id'), False),
        )


FIELDS = {
    'comment': Comment.comment,
    'comment_id': Comment.comment_id,
    'claim_id': Comment.claim_id,
    'timestamp': Comment.timestamp,
    'signature': Comment.signature,
    'signing_ts': Comment.signing_ts,
    'is_hidden': Comment.is_hidden,
    'parent_id': Comment.parent.alias('parent_id'),
    'channel_id': Channel.claim_id.alias('channel_id'),
    'channel_name': Channel.name.alias('channel_name'),
    'channel_url': ('lbry://' + Channel.name + '#' + Channel.claim_id).alias('channel_url')
}


def comment_list(claim_id: str = None, parent_id: str = None,
                 top_level: bool = False, exclude_mode: str = None,
                 page: int = 1, page_size: int = 50, expressions=None,
                 select_fields: list = None, exclude_fields: list = None) -> dict:
    fields = FIELDS.keys()
    if exclude_fields:
        fields -= set(exclude_fields)
    if select_fields:
        fields &= set(select_fields)
    attributes = [FIELDS[field] for field in fields]
    query = Comment.select(*attributes)

    # todo: allow this process to be more automated, so it can just be an expression
    if claim_id:
        query = query.where(Comment.claim_id == claim_id)
        if top_level:
            query = query.where(Comment.parent.is_null())

    if parent_id:
        query = query.where(Comment.ParentId == parent_id)

    if exclude_mode:
        show_hidden = exclude_mode.lower() == 'hidden'
        query = query.where((Comment.is_hidden == show_hidden))

    if expressions:
        query = query.where(expressions)

    total = query.count()
    query = (query
             .join(Channel, JOIN.LEFT_OUTER)
             .order_by(Comment.timestamp.desc())
             .paginate(page, page_size))
    items = [clean(item) for item in query.dicts()]
    # has_hidden_comments is deprecated
    data = {
        'page': page,
        'page_size': page_size,
        'total_pages': math.ceil(total / page_size),
        'total_items': total,
        'items': items,
        'has_hidden_comments': exclude_mode is not None and exclude_mode == 'hidden',
    }
    return data


def get_comment(comment_id: str) -> dict:
    try:
        comment = comment_list(expressions=(Comment.comment_id == comment_id), page_size=1).get('items').pop()
    except IndexError:
        raise ValueError(f'Comment does not exist with id {comment_id}')
    else:
        return comment


def create_comment_id(comment: str, channel_id: str, timestamp: int):
    # We convert the timestamp from seconds into minutes
    # to prevent spammers from commenting the same BS everywhere.
    nearest_minute = str(math.floor(timestamp / 60))

    # don't use claim_id for the comment_id anymore so comments
    # are not unique to just one claim
    prehash = b':'.join([
        comment.encode(),
        channel_id.encode(),
        nearest_minute.encode()
    ])
    return nacl.hash.sha256(prehash).decode()


def create_comment(comment: str = None, claim_id: str = None,
                   parent_id: str = None, channel_id: str = None,
                   channel_name: str = None, signature: str = None,
                   signing_ts: str = None) -> dict:
    if not is_valid_base_comment(
            comment=comment,
            claim_id=claim_id,
            parent_id=parent_id,
            channel_id=channel_id,
            channel_name=channel_name,
            signature=signature,
            signing_ts=signing_ts
    ):
        raise ValueError('Invalid Parameters given for comment')

    channel, _ = Channel.get_or_create(name=channel_name, claim_id=channel_id)
    if parent_id and not claim_id:
        parent: Comment = Comment.get_by_id(parent_id)
        claim_id = parent.claim_id

    timestamp = int(time.time())
    comment_id = create_comment_id(comment, channel_id, timestamp)
    new_comment = Comment.create(
            claim_id=claim_id,
            comment_id=comment_id,
            comment=comment,
            parent=parent_id,
            channel=channel,
            signature=signature,
            signing_ts=signing_ts,
            timestamp=timestamp
        )
    return get_comment(new_comment.comment_id)


def delete_comment(comment_id: str) -> bool:
    try:
        comment: Comment = Comment.get_by_id(comment_id)
    except DoesNotExist as e:
        raise ValueError from e
    else:
        return 0 < comment.delete_instance(True, delete_nullable=True)


def edit_comment(comment_id: str, new_comment: str, new_sig: str, new_ts: str) -> bool:
    try:
        comment: Comment = Comment.get_by_id(comment_id)
    except DoesNotExist as e:
        raise ValueError from e
    else:
        comment.comment = new_comment
        comment.signature = new_sig
        comment.signing_ts = new_ts

        # todo: add a 'last-modified' timestamp
        comment.timestamp = int(time.time())
        return comment.save() > 0


def set_hidden_flag(comment_ids: typing.List[str], hidden=True) -> bool:
    # sets `is_hidden` flag for all `comment_ids` to the `hidden` param
    update = (Comment
              .update(is_hidden=hidden)
              .where(Comment.comment_id.in_(comment_ids)))
    return update.execute() > 0


if __name__ == '__main__':
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    comments = comment_list(
        page_size=20,
        expressions=((Comment.timestamp < 1583272089) &
                     (Comment.claim_id ** '420%'))
    )

    print(json.dumps(comments, indent=4))
