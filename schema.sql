-- Applied on every run; every statement must be safe to repeat.

-- One row per picture file found in the scanned folder.
CREATE TABLE IF NOT EXISTS images (
    id          bigserial PRIMARY KEY,
    path        text NOT NULL UNIQUE,          -- full path of the file
    place       text NOT NULL,                 -- name of the place folder the file is in
    name        text NOT NULL,                 -- path of the file inside the place folder
    bytes       bigint NOT NULL,
    modified_at double precision NOT NULL,     -- file modification time; a changed file is fingerprinted again
    width       integer,
    height      integer,
    sha256      text NOT NULL,                 -- fingerprint of the file's bytes: equal = the same file
    phash       text,                          -- fingerprint of how the picture looks, 64 bits as 16 hex digits;
                                               -- NULL when the file could not be opened as a picture
    group_id    integer,                       -- duplicate group the file belongs to, NULL when it has no duplicate
    scanned_at  timestamptz NOT NULL DEFAULT now()
);

-- Rebuilt from scratch on every run.
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id      integer PRIMARY KEY,
    level   integer NOT NULL,                  -- 1: all files byte-identical; 2: same picture, the files differ;
                                               -- 3: similar frame, a candidate to check by eye
    images  integer NOT NULL,                  -- files in the group
    places  integer NOT NULL                   -- different places those files are in
);
