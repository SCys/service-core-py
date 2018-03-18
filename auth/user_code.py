from datetime import datetime, timezone

import xid
from passlib.hash import argon2


class UserCode(object):

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
        self.info = row.get('info', {})

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
