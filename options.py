
from tornado.options import define, options  # noqa

# default config path
define('config', default='config.ini', help='main options file path')
define('version', default='0.0.0', help='service version')

# database
define("db", help="database connection dsn")

# defautl setings for http server
define('address', 'localhost', help='service listen address')
define('port', 8080, type=int, help='service listen port')

define('google_pid', help='Google project id')
define('google_cid', help='Google client id')
define('google_secret', help='Google client secret sring')
define('google_token_file', help='Google token file path')
