from datetime import datetime, timezone

import asyncpg
import xid

from rapidjson import DM_ISO8601, dumps

from ..log import D


class UserHistory(object):
    """
    user history:

    ```python
    {
        'id': string,
        'id_user': string,
        'action': string, # history action
        'source': string, # history source
        'info': dict, # history info
        'removed': boolean,
        'ts_addition': timestamp with timezone,
        'ts_modify': timestamp with timezone,
    }
    ```
    """

    __slots__ = [
        'id',
        'id_user',
        'action',
        'source',
        'info',
        'removed',
        'ts_addition',
        'ts_modify',
    ]

    def __init__(self, row):
        self.id = row.get('id', xid.Xid().string())
        self.id_user = row.get('id_user', '')

        self.action = row.get('action', '')
        self.source = row.get('source', '')
        self.info = row.get('info', {})

        self.removed = row.get('removed', False)

        now = datetime.now(timezone.utc)
        self.ts_addition = now
        self.ts_modify = now

    def __str__(self):
        return r'<UserHistory %s %s>' % (self.id_user, self.action)

    def dump(self):
        return {
            'id': self.id,
            'id_user': self.id_user,
            'action': self.action,
            'source': self.source,
            'info': self.info,
            'removed': self.removed,
            'ts_addition': self.ts_addition,
            'ts_modify': self.ts_modify,
        }

    async def add(self, conn: asyncpg.Connection):
        await conn.execute(
            '''insert user_history(id, id_user, action, source, info, removed, ts_addition, ts_modify) values(
                $1, $2, $3, $4, $5, false, now(), now()
            )''', self.id, self.id_user, self.action, self.source, dumps(self.info, datetime_mode=DM_ISO8601))

        D(f'[UserHistory.add]user {self.id_user} history {self.action}')
