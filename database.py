import sqlite3
import typing

connection = sqlite3.connect('example.db')

connection.execute("""
    CREATE TABLE IF NOT EXISTS TEST(
        NAME TEXT  NOT NULL,
        CONSTRAINT TEST_PK PRIMARY KEY(NAME)
            ON CONFLICT IGNORE
    )
""")


def get_claim_comments(claim_id: str, parent_id: int = None, page: int = 1, page_size: int = 50):
    pass


def create_comment(claim_id: str, message: str, channel_name: str = None,
                   channel_claim_id: str = None, reply_to: int = None) -> typing.Union[int, dict, None]:
    pass


def get_comment_ids(claim_id: str, parent_id: int = None, get_all: bool = False):
    """ Just return a list of the comment IDs that are associated with the given claim_id.
    If get_all is specified then it returns all the IDs, otherwise only the IDs at that level.
    if parent_id is left null then it only returns the top level comments.
    """
    pass


def get_comment_data(comment_ids: list) -> typing.Union[dict, None]:
    """ Returns a list containing the comment data associated with each ID within the list"""
    pass

if __name__ == '__main__':
    connection.execute("INSERT INTO TEST VALUES (?), (?), (?)", ['Don Hockett', 'james cayo', 'MERIANNA'])
    connection.commit()
    curs = connection.execute('SELECT * FROM TEST')
    print(curs.fetchall())
    connection.close()


