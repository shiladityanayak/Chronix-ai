CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    balance BIGINT DEFAULT 0,
    bank BIGINT DEFAULT 0,
    xp BIGINT DEFAULT 0,
    level INTEGER DEFAULT 1,
    last_daily TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE IF NOT EXISTS warns (
    warn_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    reason TEXT,
    moderator_id BIGINT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    log_channel_id BIGINT,
    ticket_category_id BIGINT,
    automod_enabled BOOLEAN DEFAULT FALSE,
    starboard_channel_id BIGINT,
    starboard_limit INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS inventory (
    user_id BIGINT,
    item_id TEXT,
    amount INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, item_id)
);
