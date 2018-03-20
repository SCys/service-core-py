
from tornado.options import define, options # noqa

# default config path
define('config', default='config.ini', help='main options file path')
define('version', default='0.0.0', help='service version')

# database
define("db", help="database connection dsn")

# defautl setings for http server
define('address', 'localhost', help='service listen address')
define('port', 8080, type=int, help='service listen port')
