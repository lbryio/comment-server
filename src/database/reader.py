import sqlite3
import typing
import re



SEARCH_PARAMS = {
    'timestamp': int,
    'is_hidden': bool,  # boolean
    'comment_id': str,  # strings
    'parent_id': str,
    'channel_name': str,
    'channel_url': str,
    'channel_id': str,
    'claim_id': str,
    'signature': str,
    'signing_ts': str,
    'comment': str,
}

TABLE = 'COMMENTS_ON_CLAIMS'


ID_PARAM_LENS = {
    'comment_id': 64,
    'channel_id': 40,
    'claim_id': 40,
    'signature': 128,
    'parent_id': 64
}

IDENTIFIERS = {
    'signature',
    'comment_id',
    'parent_id',
    'channel_id',
    'claim_id'
}

GROUPABLE = {
    'channel_name',
    'channel_url'
} | IDENTIFIERS

GROUP_PARAMS = re.compile(rf"({'|'.join(GROUPABLE)})s")
ID_PARAMS = re.compile(rf"({'|'.join(IDENTIFIERS)})")


OPS = {
    'eq': '=',
    'gt': '>',
    'lt': '<',
    'gte': '>=',
    'lte': '<=',
    'like': 'LIKE',
    'is': 'IS',
    'is_not': 'IS NOT',
    'is_null': 'IS NULL',
    'is_not_null': 'IS NOT NULL',
    'in': 'IN',
    'not_in': 'NOT IN'
}


def create_query(cols=None, **constraints):
    table = 'COMMENTS_ON_CLAIMS'

    ops = {'>': '__gt', '>=': '__gte', '<': '__lt', '<=': '__lte'}
    if 'timestamp' in constraints:
        time = constraints.pop('timestamp')
        prefix = f'{table}.timestamp'
        if isinstance(time, str):
            if len(time) > 2 and time[:2] in ops:
                constraints[f'{prefix}{ops[time[:2]]}'] = int(time[2:])
            elif len(time) > 1 and time[:1] in ops:
                constraints[f'{prefix}{ops[time[:1]]}'] = int(time[1:])
            else:
                constraints[f'{prefix}__eq'] = int(time)
        elif isinstance(time, int):
            constraints[f'{prefix}__eq'] = time

    sql = ['SELECT']
    if isinstance(cols, (list, tuple)):
        sql.append(', '.join(cols))
    elif isinstance(cols, dict):
        sql.append(', '.join(f'{col} AS {cola}' for col, cola in cols.items()))
    else:
        sql.append('*')
    sql += ['FROM', table]
    if len(constraints) > 0:
        conditions, constraints = constraints_to_sql(**constraints)
        sql += ['WHERE', conditions]

    return '\n'.join(sql), constraints


def constraints_to_sql(**constraints):
    sql_params = {}
    sql_stmts = []
    for constraint, value in constraints.items():
        if constraint.find('__'):
            col, op = constraint.split('__')
            param = col.split('.')[1]
            statement = [param, OPS[op]]
            if op[-2:] == 'in' and isinstance(value, (list, tuple, set)):
                param_list = ", ".join(f':{param}{i}' for i in range(len(value)))
                statement.append(f'({param_list})')
                sql_params.update({f'{param}{i}': v for i, v in enumerate(value)})
            elif 'null' not in op:
                statement.append(':' + param)
                sql_params[param] = value
            sql_stmts.append(' '.join(statement))

    inner_where = ' AND '.join(sql_stmts)
    return inner_where, sql_params


def _page_to_limit(**constraints):
    limit = constraints.pop('page_size', None)
    page = constraints.pop('page', None)
    if limit and isinstance(int, limit):
        constraints['LIMIT'] = limit
        if page and isinstance(page, int):
            constraints['OFFSET'] = limit * (page - 1)
    return constraints


