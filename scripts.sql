ATTACH DATABASE 'comments.db' AS Comments;

PRAGMA FOREIGN_KEYS = ON;

SELECT * FROM CLAIM WHERE LbryClaimId LIKE '1ed866252f80e48f2496acec72a69a5ad85497AC';

SELECT * FROM CLAIM;

DROP TABLE CLAIM;
CREATE TABLE IF NOT EXISTS CLAIM (
	ClaimIndex    INTEGER NOT NULL,
	LbryClaimId   TEXT    NOT NULL,
	Time_added    INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
	CONSTRAINT CLAIM_PK PRIMARY KEY (ClaimIndex)
	    ON CONFLICT ROLLBACK,
	CONSTRAINT LBRY_CLAIMID_CK UNIQUE (LbryClaimId)
	    ON CONFLICT IGNORE,
	CONSTRAINT LBRY_CLAIM_ID CHECK (length(LbryClaimId) = 40)
);
INSERT INTO CLAIM(LbryClaimId)
VALUES  ('1ed866252f80e48f2496acec72a69a5ad85497ac'),
        ('3128b0f0e9b4b18e33fc8e2a586a66da40f617c4'),
        ('ce09230acc7b0037ddc9a1ac01f03baab8a23b1b');
--         ('0c37b593d4d7e9a00e1bd69f305d0241eac3f4ad');

SELECT * FROM COMMENT;
DROP TABLE COMMENT;
CREATE TABLE IF NOT EXISTS COMMENT (
    CommentId  INTEGER NOT NULL PRIMARY KEY ,
    ClaimIndex INTEGER NOT NULL,
    ChannelName  TEXT    NOT NULL,
    ParentId   INTEGER          DEFAULT NULL,
    Timestamp  INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    Comment       TEXT    NOT NULL,
    CONSTRAINT COMMENT_CLAIM_FK
        FOREIGN KEY (ClaimIndex) REFERENCES CLAIM(ClaimIndex)
            ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT COMMENT_PARENT_FK
        FOREIGN KEY (ParentId) REFERENCES COMMENT(CommentId)
            ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT COMMENT_LEN CHECK(1 < length(Comment) AND length(Comment) <= 2000),
    CONSTRAINT CHANNEL_NAME_LEN CHECK ( 0 < length(ChannelName) AND length(ChannelName) <= 120),
    CONSTRAINT COMMENT_SK UNIQUE (ChannelName, Comment, ParentId)
                                   ON CONFLICT IGNORE
);



INSERT INTO COMMENT(ClaimIndex, ChannelName, ParentId, Comment)
SELECT 2 , 'Flatness Flatness LA', 1, 'sick bike tricks'
FROM CLAIM AS C
WHERE C.ClaimIndex = ClaimIndex AND EXISTS (
    SELECT * FROM Comments.COMMENT AS P
    WHERE P.CommentId = P.ParentId
);

-- first three should fail
INSERT INTO CLAIM(LbryClaimId)
VALUES  ('1ed866252f80e48f2496acec72a69a5ad85497ac'),
        ('3128b0f0e9b4b18e33fc8e2a586a66da40f617c4'),
        ('ce09230acc7b0037ddc9a1ac01f03baab8a23b1b'),
        ('0c37b593d4d7e9a00e1bd69f305d0241eac3f4ad');


-- gets the top level comments for a given claim id
SELECT * FROM COMMENT AS C, CLAIM AS D
WHERE C.ParentId IS NULL
  AND C.ClaimIndex = D.ClaimIndex
  AND D.LbryClaimId LIKE 'some shit here';

SELECT SQLITE_VERSION();



SELECT * FROM CLAIM;
INSERT INTO COMMENT(ClaimIndex, ChannelName, Comment)
SELECT
    C.ClaimIndex, 'doge loard', 'nice ass'
FROM CLAIM AS C WHERE C.LbryClaimId = '1ed866252f80e48f2496acec72a69a5ad85497ac';

SELECT C.ChannelId, C.Comment, C.Timestamp, D.LbryClaimId, D.Time_added
FROM COMMENT AS C NATURAL JOIN CLAIM AS D;

	 INSERT INTO backups(creation_time, totalcomments, totalclaims, size_kb)
	 VALUES (]] .. time .. ", " .. com_count .. ", " .. claim_count ..

	SELECT last_insert_rowid();

SELECT _rowid_ FROM CLAIM UNION ALL
SELECT _rowid_ FROM COMMENT;

INSERT INTO claims (lbry_perm_uri, Time_added) VALUES ('" ..
	 accouts:escape(claim_uri) .. "', " .. get_unix_time() .. ");"

		 "UPDATE claims SET upvotes = " .. votes ..
		 " WHERE lbry_perm_uri = '" .. data.lbry_perm_uri .. "';"


		 "UPDATE claims SET downvotes = " .. votes ..
		 " WHERE lbry_perm_uri = '" .. data.lbry_perm_uri .. "';"

	 "SELECT lbry_perm_uri FROM claims WHERE ClaimId = " ..

	 "SELECT * FROM comments WHERE parent_com IS NULL AND ClaimId = " ..

		 "INSERT INTO comments (ClaimId, poster_name, post_time," ..
		 " message) VALUES (" .. ClaimId .. ", '" .. poster_name ..
		 "', " .. post_time .. ", '" .. message .. "');"

INSERT INTO comments (ClaimId, poster_name, " ..
		 "parent_com, post_time, message) VALUES (" .. ClaimId ..
		 ", '" .. poster_name .. "', " .. parent_id .. ", " ..
		 post_time .. ", '" .. message .. "');"

	 "SELECT * FROM comments WHERE CommentId = '" .. comment_id .. "';"
	 "SELECT * FROM comments WHERE parent_com = '" .. comment_id .. "';"

UPDATE comments SET upvotes = " .. votes ..
		 " WHERE CommentId = '" .. comment_id .. "';"

UPDATE comments SET downvotes = " .. votes ..
		 " WHERE CommentId = '" .. comment_id .. "';"