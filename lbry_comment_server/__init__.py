from lbry_comment_server.settings import config
from lbry_comment_server.database import obtain_connection, validate_input, get_claim_comments
from lbry_comment_server.database import get_comments_by_id, get_comment_ids, create_comment
from lbry_comment_server.handles import api_endpoint
SCHEMA = config['path']['SCHEMA']
DATABASE = config['path']['dev']
BACKUP = config['path']['BACKUP']
ANONYMOUS = config['ANONYMOUS']

