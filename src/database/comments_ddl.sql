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

CREATE TABLE `COMMENTOPINION` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `commentid` char(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `channelid` char(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `signature` char(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `signingts` varchar(22) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `timestamp` int NOT NULL,
  `rating` tinyint DEFAULT '1',

  PRIMARY KEY (`id`),
  KEY `comment_channel_fk` (`channelid`),
  CONSTRAINT `comment_fk` FOREIGN KEY (`commentid`) REFERENCES `COMMENT` (`commentid`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `comment_channel_fk` FOREIGN KEY (`channelid`) REFERENCES `CHANNEL` (`claimid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci

CREATE TABLE `CONTENTOPINION` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `claimid` char(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `channelid` char(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `signature` char(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `signingts` varchar(22) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `timestamp` int NOT NULL,
  `rating` tinyint DEFAULT '1',

  PRIMARY KEY (`id`),
  KEY `comment_channel_fk` (`channelid`),
  KEY `lbryclaimid` (`lbryclaimid`),
  CONSTRAINT `comment_channel_fk` FOREIGN KEY (`channelid`) REFERENCES `CHANNEL` (`claimid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci