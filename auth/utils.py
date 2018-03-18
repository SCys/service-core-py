
import asyncpg

from ..log import E

from .user import User
from .user_code import UserCode
from .user_history import UserHistory


def user_add_code(conn, user, code_type, code):
    code = UserCode({
        'id_user': self.id,
        'code_type': code_type,
        'code': code,
    })
    await conn.execute('insert users values()')
    I('%s add code %s', self, code)

