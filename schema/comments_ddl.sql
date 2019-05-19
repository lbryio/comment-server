
PRAGMA FOREIGN_KEYS = ON;

-- tables
-- DROP TABLE IF EXISTS COMMENT;
-- DROP TABLE IF EXISTS CHANNEL;

CREATE TABLE IF NOT EXISTS CHANNEL(
    ClaimId     TEXT    NOT NULL,
    Name        TEXT    NOT NULL,
    CONSTRAINT CHANNEL_PK PRIMARY KEY (ClaimId)
        ON CONFLICT IGNORE
);


DROP TABLE IF EXISTS COMMENT;
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

-- indexes
DROP INDEX IF EXISTS COMMENT_CLAIM_INDEX;
CREATE INDEX COMMENT_CLAIM_INDEX ON COMMENT (LbryClaimId);


-- VIEWS
DROP VIEW IF EXISTS COMMENTS_ON_CLAIMS;
CREATE VIEW COMMENTS_ON_CLAIMS (comment_id, claim_id, timestamp, channel_name, channel_id, channel_uri, comment, parent_id) AS
    SELECT C.CommentId, C.LbryClaimId, C.Timestamp, CHAN.Name, CHAN.ClaimId, 'lbry://' || CHAN.Name || '#' || CHAN.ClaimId, C.Body, C.ParentId
    FROM CHANNEL AS CHAN
    INNER JOIN COMMENT C on CHAN.ClaimId = C.ChannelId
    ORDER BY C.Timestamp;



DROP VIEW IF EXISTS COMMENT_REPLIES;
CREATE VIEW COMMENT_REPLIES (Author, CommentBody, ParentAuthor, ParentCommentBody) AS
    SELECT AUTHOR.Name, OG.Body, PCHAN.Name, PARENT.Body FROM COMMENT AS OG
        JOIN  COMMENT AS PARENT
        ON OG.ParentId = PARENT.CommentId
        JOIN CHANNEL AS PCHAN ON PARENT.ChannelId = PCHAN.ClaimId
        JOIN CHANNEL AS AUTHOR ON OG.ChannelId = AUTHOR.ClaimId
        ORDER BY OG.Timestamp;

-- this is the default channel for anyone who wants to publish anonymously
INSERT INTO CHANNEL
VALUES ('9cb713f01bf247a0e03170b5ed00d5161340c486', '@Anonymous');