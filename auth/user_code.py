from datetime import datetime, timezone

import xid
from passlib.hash import argon2

from rapidjson import loads, dumps, DM_ISO8601

from .user_history import UserHistory
from ..log import I


class UserCode(object):
    """

    ```sql
    create table user_codes (
        id varchar(120) primary key,
        id_user varchar(120),
        code varchar(200) not null,
        code_type varchar(200) not null,
        info jsonb default '{}'::jsonb,
        removed boolean default false,
        ts_addition timestamp with time zone default now(),
        ts_modify timestamp with time zone default now(),
        ts_expired timestamp with time zone default null
    );

    create index idx_user_codes_id_user on user_codes(id_user);
    create index idx_user_codes_code on user_codes(code);
    create index idx_user_codes_code_type on user_codes(code_type);
    create index idx_user_codes_removed on user_codes(removed);
    create index idx_user_codes_ts_addition on user_codes(ts_addition);
    create index idx_user_codes_ts_expired on user_codes(ts_expired);
    ```
    """

    supported_types = [
        'telegram',
        '5numbers',
        'password',
    ]

    __slots__ = [
        'id',
        'id_user',
        'code',
        'code_type',
        'info',
        'removed',
        'ts_expired',
        'ts_addition',
        'ts_modify',
    ]

    def __init__(self, row):
        self.id = row.get('id', xid.Xid().string())
        self.id_user = row.get('id_user', '')

        self.code = row.get('code', '')
        self.code_type = row.get('code_type', '5number')

        info = row.get('info', '{}')
        self.info = loads(info, datetime_mode=DM_ISO8601)

        self.removed = row.get('removed', False)

        self.ts_expired = row.get('ts_expired', None)

        now = datetime.now(timezone.utc)
        self.ts_addition = now
        self.ts_modify = now

    def __str__(self):
        return r'<UserCode %s %s>' % (self.id_user, self.code_type)

    def dump(self):
        return {
            'id': self.id,
            'id_user': self.id_user,
            'code': self.code,
            'code_type': self.code_type,
            'info': self.info,
            'removed': self.removed,
            'ts_expired': self.ts_expired,
            'ts_addition': self.ts_addition,
            'ts_modify': self.ts_modify,
        }

    def check(self, raw):
        if self.code_type == 'password':
            return argon2.verify(raw, self.code)

        # check expired timestamp
        if self.ts_expired is not None and datetime.now(
                timezone.utc) > self.ts_expired:
            return False

        return raw == self.code

    async def create(self, conn):
        await conn.execute(
            '''insert into user_codes(id, id_user, code, code_type, info, removed, ts_addition, ts_modify, ts_expired) values(
                $1, $2, $3, $4, $5, $6, $7, $8, $9
            )''',
            self.id, self.id_user,
            self.code, self.code_type,
            dumps(self.info, datetime_mode=DM_ISO8601),
            self.removed,
            self.ts_addition, self.ts_modify,
            self.ts_expired,
        )

        history = UserHistory({'id_user': self.id, 'action': 'code_created', 'source': 'in_code'})
        await history.add(conn)
        I('[UserCode.create]%s created', self)
