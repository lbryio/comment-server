import json
import logging

import math
import timeit

import typing

from peewee import ModelSelect
from playhouse.shortcuts import model_to_dict
from peewee import *


def get_database_connection():
    # for now it's an sqlite database
    db = SqliteDatabase()
    return db


database = get_database_connection()


class BaseModel(Model):
    class Meta:
        database = database


class Channel(BaseModel):
    claim_id = TextField(column_name='ClaimId', primary_key=True)
    name = TextField(column_name='Name')

    class Meta:
        table_name = 'CHANNEL'


class Comment(BaseModel):
    comment = TextField(column_name='Body')
    channel = ForeignKeyField(
        backref='comments',
        column_name='ChannelId',
        field='claim_id',
        model=Channel,
        null=True
    )
    comment_id = TextField(column_name='CommentId', primary_key=True)
    is_hidden = BooleanField(column_name='IsHidden', constraints=[SQL("DEFAULT FALSE")])
    claim_id = TextField(column_name='LbryClaimId')
    parent = ForeignKeyField(
        column_name='ParentId',
        field='comment_id',
        model='self',
        null=True,
        backref='replies'
    )
    signature = TextField(column_name='Signature', null=True, unique=True)
    signing_ts = TextField(column_name='SigningTs', null=True)
    timestamp = IntegerField(column_name='Timestamp')

    class Meta:
        table_name = 'COMMENT'
        indexes = (
            (('author', 'comment_id'), False),
            (('claim_id', 'comment_id'), False),
        )


COMMENT_FIELDS = [
    Comment.comment,
    Comment.comment_id,
    Comment.claim_id,
    Comment.timestamp,
    Comment.signature,
    Comment.signing_ts,
    Comment.is_hidden,
    Comment.parent.alias('parent_id'),
]

CHANNEL_FIELDS = [
    Channel.claim_id.alias('channel_id'),
    Channel.name.alias('channel_name')
]


def get_comment_list(claim_id: str = None, parent_id: str = None,
                     top_level: bool = False, exclude_mode: str = None,
                     page: int = 1, page_size: int = 50, expressions=None) -> dict:
    query = Comment.select(*COMMENT_FIELDS, *CHANNEL_FIELDS)
    if claim_id:
        query = query.where(Comment.claim_id == claim_id)
        if top_level:
            query = query.where(Comment.parent.is_null())

    if parent_id:
        query = query.where(Comment.ParentId == parent_id)

    if exclude_mode:
        show_hidden = exclude_mode.lower() == 'hidden'
        query = query.where((Comment.is_hidden == show_hidden))
    total = query.count()
    query = (query
             .join(Channel, JOIN.LEFT_OUTER)
             .where(expressions)
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


def clean(thing: dict) -> dict:
    return {k: v for k, v in thing.items() if v is not None}


def get_comment(comment_id: str) -> dict:
    try:
        comment: Comment = Comment.get_by_id(comment_id)
    except DoesNotExist as e:
        raise ValueError from e
    else:
        as_dict = model_to_dict(comment)
        if comment.channel:
            as_dict.update({
                'channel_id': comment.channel_id,
                'channel_name': comment.channel.name,
                'signature': comment.signature,
                'signing_ts': comment.signing_ts,
                'channel_url': f'lbry://{comment.channel.name}#{comment.channel_id}'
            })
        if comment.parent:
            as_dict.update({
                'parent_id': comment.parent_id
            })
        return clean(as_dict)


if __name__ == '__main__':
    logger = logging.getLogger('peewee')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    comment_list = get_comment_list(
        page_size=1,
        expressions=(Comment.channel.is_null())
    )

    comment = comment_list['items'].pop()
    print(json.dumps(comment, indent=4))
    other_comment = get_comment(comment['comment_id'])

    print(json.dumps(other_comment, indent=4))
    print(comment == other_comment)
