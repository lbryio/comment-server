USE `social`;
ALTER DATABASE `social`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `CHANNEL`;
CREATE TABLE `CHANNEL` (
        `claimid` VARCHAR(40)  NOT NULL,
        `name`  CHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
        CONSTRAINT `channel_pk` PRIMARY KEY (`claimid`)
    )
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `COMMENT`;
CREATE TABLE `COMMENT` (
        -- should be changed to CHAR(64)
        `commentid`   CHAR(64)   NOT NULL,
        -- should be changed to CHAR(40)
        `lbryclaimid` CHAR(40)   NOT NULL,
        -- can be null, so idk if this should be char(40)
        `channelid`   CHAR(40)              DEFAULT NULL,
        `body`        TEXT
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            NOT NULL,
        `parentid`    CHAR(64)               DEFAULT NULL,
        `signature`   CHAR(128)              DEFAULT NULL,
        -- 22 chars long is prolly enough
        `signingts`   VARCHAR(22)               DEFAULT NULL,

        `timestamp`   INTEGER NOT NULL,
        -- there's no way that the timestamp will ever reach 22 characters
        `ishidden`    BOOLEAN                    DEFAULT FALSE,
        CONSTRAINT `COMMENT_PRIMARY_KEY` PRIMARY KEY (`commentid`)
         -- setting null implies comment is top level
    )
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;


ALTER TABLE COMMENT
    ADD CONSTRAINT `comment_channel_fk` FOREIGN KEY (`channelid`) REFERENCES `CHANNEL` (`claimid`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT `comment_parent_fk` FOREIGN KEY (`parentid`) REFERENCES `COMMENT` (`commentid`)
            ON UPDATE CASCADE ON DELETE CASCADE
;

CREATE INDEX `claim_comment_index` ON `COMMENT` (`lbryclaimid`, `commentid`);
CREATE INDEX `channel_comment_index` ON `COMMENT` (`channelid`, `commentid`);


ALTER TABLE COMMENT ADD CONSTRAINT UNIQUE (`signature`, `channelid`);


