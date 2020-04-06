USE `social`;
ALTER DATABASE `social`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `CHANNEL`;
CREATE TABLE `CHANNEL` (
        `claimid` VARCHAR(40)  NOT NULL,
        -- i cant tell if max name length is 255 or 256
        `name`  VARCHAR(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
        CONSTRAINT `channel_pk` PRIMARY KEY (`claimid`)
    )
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

DROP TABLE IF EXISTS `COMMENT`;
CREATE TABLE `COMMENT` (
        `commentid`   VARCHAR(64)   NOT NULL,
        `lbryclaimid` VARCHAR(40)   NOT NULL,
        `channelid`   VARCHAR(40)              DEFAULT NULL,
        `body`        VARCHAR(5000)
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            NOT NULL,
        `parentid`    VARCHAR(64)               DEFAULT NULL,
        `signature`   VARCHAR(128)              DEFAULT NULL,
        `signingts`   VARCHAR(22)               DEFAULT NULL,

        `timestamp`   INTEGER NOT NULL,
        -- there's no way that the timestamp will ever reach 22 characters
        `ishidden`    BOOLEAN                    DEFAULT FALSE,
        CONSTRAINT `COMMENT_PRIMARY_KEY` PRIMARY KEY (`commentid`),
        CONSTRAINT `comment_signature_sk` UNIQUE (`signature`),
        CONSTRAINT `comment_channel_fk` FOREIGN KEY (`channelid`) REFERENCES `CHANNEL` (`claimid`)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT `comment_parent_fk` FOREIGN KEY (`parentid`) REFERENCES `COMMENT` (`commentid`)
            ON UPDATE CASCADE ON DELETE CASCADE, -- setting null implies comment is top level
        CONSTRAINT `channel_signature`
            CHECK ( `signature` IS NOT NULL AND `signingts` IS NOT NULL)
    )
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE INDEX `claim_comment_index` ON `COMMENT` (`lbryclaimid`, `commentid`);
CREATE INDEX `channel_comment_index` ON `COMMENT` (`channelid`, `commentid`);



