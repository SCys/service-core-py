import xid
import asyncpg
from datetime import datetime, timezone

from rapidjson import dumps, DM_ISO8601, loads
from gcd import Entity

from ..log import I
from .user_code import UserCode
from .user_history import UserHistory


class User(object):
    '''
    User data struct

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

    ```sql
    create table users (
        id varchar(120) primary key,
        name varchar(120),
        email varchar(120),
        phone_primary varchar(120),
        info jsonb default '{}'::jsonb,
        actived boolean default false,
        disabled boolean default false,
        removed boolean default false,
        ts_addition timestamp with time zone default now(),
        ts_modify timestamp with time zone default now()
    );

    create unique index idx_users_name on users(name);
    create unique index idx_users_email on users(email);
    create unique index idx_users_phone_primary on users(phone_primary);

    create index idx_users_ts_addition on users(ts_addition);
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

        info = row.get('info', '{}')
        self.info = loads(info, datetime_mode=DM_ISO8601)

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
            '''insert into users(
                id, name, email, phone_primary, info, 
                actived, disabled, removed, 
                ts_addition, ts_modify
            ) values(
                $1, $2, $3, $4, $5, 
                false, false, false, 
                now(), now()
            )''', self.id, self.name, self.email, self.phone_primary, dumps(self.info, datetime_mode=DM_ISO8601))

        history = UserHistory({'id_user': self.id, 'action': 'created', 'source': source})
        await history.add(conn)
        I('[User.create]%s created', self)

    async def add_code(self, conn: asyncpg.Connection, code_type, code) -> bool:
        uc = UserCode({
            'id_user': self.id,
            'code': code,
            'code_type': code_type,
            'removed': False,
            'tp_expired': datetime(2999, 1, 1, tzinfo=timezone.utc),
        })
        await uc.create(conn)

    @staticmethod
    async def find(conn: asyncpg.Connection, name=None, code=None, code_type=None):
        async with conn.transaction():
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

        return User(dict(row))

    async def create_ds(self, conn, source: str):
        entity = Entity({
            'properties': {
                'name': {'stringValue': self.name},
                'email': {'stringValue': self.email},
                'phone_primary': {'stringValue': self.phone_primary},
                'info': {'textValue': dumps(self.info, datetime_mode=DM_ISO8601)},
                'actived': {'booleanValue': self.actived},
                'disabled': {'booleanValue': self.disabled},
                'removed': {'booleanValue': self.removed},
                'ts_addition': {'timestampValue': self.ts_addition},
                'ts_modify': {'timestampValue': self.ts_modify},
            },
            'key': {
                'path': [{'kind': 'user', 'domain': 'auth'}]
            }
        })

        await conn.insert_entity(entity)

        # not history in google datastore
        # history = UserHistory({'id_user': self.id, 'action': 'created', 'source': source})
        # await history.add(conn)

        I('[User.create]%s created', self)

    async def add_code_ds(self, conn, code_type, code) -> bool:
        uc = UserCode({
            'id_user': self.id,
            'code': code,
            'code_type': code_type,
            'removed': False,
            'tp_expired': datetime(2999, 1, 1, tzinfo=timezone.utc),
        })

        await uc.create_ds(conn)

    @staticmethod
    async def find_ds(conn, code=None, code_type=None):
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

        row = await cursor.fetchrow()
        if row is None:
            return

        return User(dict(row))
