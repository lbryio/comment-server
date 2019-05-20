from lbry_comment_server.settings import config
from lbry_comment_server.database import obtain_connection, validate_input, get_claim_comments
from lbry_comment_server.database import get_comments_by_id, get_comment_ids, create_comment
schema = config['path']['schema']
database_fp = config['path']['dev']
backup = config['path']['backup']
anonymous = config['anonymous']

