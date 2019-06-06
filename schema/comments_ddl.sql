
PRAGMA FOREIGN_KEYS = ON;

-- tables
-- DROP TABLE IF EXISTS COMMENT;
-- DROP TABLE IF EXISTS CHANNEL;

-- DROP TABLE IF EXISTS COMMENT;
CREATE TABLE IF NOT EXISTS COMMENT (
    CommentId   TEXT    NOT NULL,
    LbryClaimId TEXT    NOT NULL,
    ChannelId   TEXT                DEFAULT NULL,
    Body        TEXT    NOT NULL,
    ParentId    TEXT                DEFAULT NULL,
    Signature   TEXT                DEFAULT NULL,
    Timestamp   INTEGER NOT NULL,
    CONSTRAINT COMMENT_PRIMARY_KEY PRIMARY KEY (CommentId) ON CONFLICT IGNORE,
    CONSTRAINT COMMENT_SIGNATURE_SK UNIQUE (Signature) ON CONFLICT ABORT,
    CONSTRAINT COMMENT_CHANNEL_FK FOREIGN KEY (ChannelId) REFERENCES CHANNEL(ClaimId)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT COMMENT_PARENT_FK FOREIGN KEY (ParentId) REFERENCES COMMENT(CommentId)
        ON UPDATE CASCADE ON DELETE NO ACTION  -- setting null implies comment is top level
);

ALTER TABLE COMMENT ADD COLUMN SigningTs TEXT DEFAULT NULL;

-- DROP TABLE IF EXISTS CHANNEL;
CREATE TABLE IF NOT EXISTS CHANNEL(
    ClaimId     TEXT    NOT NULL,
    Name        TEXT    NOT NULL,
    PublicKey   TEXT    NOT NULL,
    CONSTRAINT CHANNEL_PK PRIMARY KEY (ClaimId)
        ON CONFLICT IGNORE
);


-- indexes
-- DROP INDEX IF EXISTS COMMENT_CLAIM_INDEX;
CREATE INDEX IF NOT EXISTS COMMENT_CLAIM_INDEX ON COMMENT (LbryClaimId);


-- VIEWS
DROP VIEW IF EXISTS COMMENTS_ON_CLAIMS;
CREATE VIEW IF NOT EXISTS COMMENTS_ON_CLAIMS (comment_id, claim_id, timestamp, channel_name, channel_id, channel_url, signature, signing_ts, parent_id, comment) AS
    SELECT C.CommentId, C.LbryClaimId, C.Timestamp, CHAN.Name, CHAN.ClaimId, 'lbry://' || CHAN.Name || '#' || CHAN.ClaimId, C.Signature, C.SigningTs, C.ParentId, C.Body
    FROM COMMENT AS C
    LEFT OUTER JOIN CHANNEL CHAN on C.ChannelId = CHAN.ClaimId
    ORDER BY C.Timestamp DESC;



DROP VIEW IF EXISTS COMMENT_REPLIES;
CREATE VIEW IF NOT EXISTS COMMENT_REPLIES (Author, CommentBody, ParentAuthor, ParentCommentBody) AS
    SELECT AUTHOR.Name, OG.Body, PCHAN.Name, PARENT.Body FROM COMMENT AS OG
        JOIN  COMMENT AS PARENT
        ON OG.ParentId = PARENT.CommentId
        JOIN CHANNEL AS PCHAN ON PARENT.ChannelId = PCHAN.ClaimId
        JOIN CHANNEL AS AUTHOR ON OG.ChannelId = AUTHOR.ClaimId
        ORDER BY OG.Timestamp;

-- this is the default channel for anyone who wants to publish anonymously
-- INSERT INTO CHANNEL
-- VALUES ('9cb713f01bf247a0e03170b5ed00d5161340c486', '@Anonymous');
