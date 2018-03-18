import xid
import asyncpg
from datetime import datetime, timezone

from rapidjson import dumps, DM_ISO8601

from ..log import E, I
from .user_code import UserCode
from .user_history import UserHistory


class User(object):
    '''
    user history:

    ```python
    {
        'id': string,
        'name': string, # username
        'email': string, # email address
        'phone_primary': string, # mobile phone
        'info': dict,
        'actived': boolean,
        'disabled': boolean,
        'removed': boolean,
        'ts_addition': timestamp with timezone,
        'ts_modify': timestamp with timezone,
    }
    ```
    '''

    __slots__ = [
        'id',
        'name',
        'email',
        'phone_primary',
        'info',
        'actived',
        'disabled',
        'removed',
        'ts_addition',
        'ts_modify',
    ]

    def __init__(self, row):
        self.id = row.get('id', xid.Xid().string())

        self.name = row.get('name', '')
        self.email = row.get('email', None)
        self.phone_primary = row.get('phone_primary', None)
        self.info = row.get('info', {})

        self.actived = row.get('actived', False)
        self.disabled = row.get('disabled', False)
        self.removed = row.get('removed', False)

        now = datetime.now(timezone.utc)
        self.ts_addition = now
        self.ts_modify = now

    def __str__(self):
        return r'<User %s %s(%s:%s:%s)>' % (self.name, self.id, self.actived, self.disabled, self.removed)

    def __eq__(self, other):
        return other.id == self.id

    def dump(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone_primary': self.phone_primary,
            'info': self.info,
            'actived': self.actived,
            'disabled': self.disabled,
            'removed': self.removed,
            'ts_addition': self.ts_addition,
            'ts_modify': self.ts_modify,
        }

    async def create(self, conn: asyncpg.Connection, source: str):
        await conn.execute(
            '''insert users(id, name, email, phone, info, actived, disabled, removed, ts_addition, ts_modify) values(
                $1, $2, $3, $4, $5, false, false, false, now(), now()
            )''', self.id, self.name, self.email, self.phone_primary, dumps(self.info, datetime_mode=DM_ISO8601))

        history = UserHistory({'id_user': self.id, 'action': 'created', 'source': source})
        await history.add()
        I('[User.create]%s created', self)

    @staticmethod
    async def find(conn: asyncpg.Connection, name=None, code=None, code_type=None):
        if code_type and code:
            cursor = await conn.cursor("""select
                a.id,
                a.name,
                a.email,
                a.phone_primary,
                a.info,
                a.actived,
                a.disabled,
                a.removed,
                a.ts_addition,
                a.ts_modify
            from users a
            join user_codes b on b.id_user = a.id
            where
                b.code = $1 and
                b.code_type = $2 and
                b.removed = false
            order by a.ts_addition desc""", code, code_type)

        elif name:
            cursor = await conn.cursor("""select
                a.id,
                a.name,
                a.email,
                a.phone_primary,
                a.info,
                a.actived,
                a.disabled,
                a.removed,
                a.ts_addition,
                a.ts_modify
            from users a
            where a.name = $1
            order by a.ts_addition desc""", name)

        row = await cursor.fetchrow()
        if row is None:
            return None

        return User(row)
