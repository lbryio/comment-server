PRAGMA FOREIGN_KEYS = ON;

-- Although I know this file is unnecessary, I like keeping it around.

-- I'm not gonna remove it.

-- tables
CREATE TABLE IF NOT EXISTS COMMENT
(
    CommentId   TEXT    NOT NULL,
    LbryClaimId TEXT    NOT NULL,
    ChannelId   TEXT                DEFAULT (NULL),
    Body        TEXT    NOT NULL,
    ParentId    TEXT                DEFAULT (NULL),
    Signature   TEXT                DEFAULT (NULL),
    Timestamp   INTEGER NOT NULL,
    SigningTs   TEXT                DEFAULT (NULL),
    IsHidden    BOOLEAN NOT NULL    DEFAULT (FALSE),
    CONSTRAINT COMMENT_PRIMARY_KEY PRIMARY KEY (CommentId) ON CONFLICT IGNORE,
    CONSTRAINT COMMENT_SIGNATURE_SK UNIQUE (Signature) ON CONFLICT ABORT,
    CONSTRAINT COMMENT_CHANNEL_FK FOREIGN KEY (ChannelId) REFERENCES CHANNEL (ClaimId)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT COMMENT_PARENT_FK FOREIGN KEY (ParentId) REFERENCES COMMENT (CommentId)
        ON UPDATE CASCADE ON DELETE NO ACTION -- setting null implies comment is top level
);

-- ALTER TABLE COMMENT ADD COLUMN IsHidden BOOLEAN DEFAULT (FALSE);
-- ALTER TABLE COMMENT ADD COLUMN SigningTs TEXT DEFAULT NULL;

-- DROP TABLE IF EXISTS CHANNEL;
CREATE TABLE IF NOT EXISTS CHANNEL
(
    ClaimId TEXT NOT NULL,
    Name    TEXT NOT NULL,
    CONSTRAINT CHANNEL_PK PRIMARY KEY (ClaimId)
        ON CONFLICT IGNORE
);


-- indexes
-- DROP INDEX IF EXISTS COMMENT_CLAIM_INDEX;
-- CREATE INDEX IF NOT EXISTS CLAIM_COMMENT_INDEX ON COMMENT (LbryClaimId, CommentId);

-- CREATE INDEX IF NOT EXISTS CHANNEL_COMMENT_INDEX ON COMMENT (ChannelId, CommentId);

-- VIEWS
CREATE VIEW IF NOT EXISTS COMMENTS_ON_CLAIMS AS SELECT
        C.CommentId AS comment_id,
        C.Body AS comment,
        C.LbryClaimId AS claim_id,
        C.Timestamp AS timestamp,
        CHAN.Name AS channel_name,
        CHAN.ClaimId AS channel_id,
        ('lbry://' || CHAN.Name || '#' || CHAN.ClaimId) AS channel_url,
        C.Signature AS signature,
        C.SigningTs AS signing_ts,
        C.ParentId AS parent_id,
        C.IsHidden AS is_hidden
    FROM COMMENT AS C
             LEFT OUTER JOIN CHANNEL CHAN ON C.ChannelId = CHAN.ClaimId
    ORDER BY C.Timestamp DESC;


DROP VIEW IF EXISTS COMMENT_REPLIES;
CREATE VIEW IF NOT EXISTS COMMENT_REPLIES (Author, CommentBody, ParentAuthor, ParentCommentBody) AS
SELECT AUTHOR.Name, OG.Body, PCHAN.Name, PARENT.Body
FROM COMMENT AS OG
         JOIN COMMENT AS PARENT
              ON OG.ParentId = PARENT.CommentId
         JOIN CHANNEL AS PCHAN ON PARENT.ChannelId = PCHAN.ClaimId
         JOIN CHANNEL AS AUTHOR ON OG.ChannelId = AUTHOR.ClaimId
ORDER BY OG.Timestamp;

-- this is the default channel for anyone who wants to publish anonymously
-- INSERT INTO CHANNEL
-- VALUES ('9cb713f01bf247a0e03170b5ed00d5161340c486', '@Anonymous');
