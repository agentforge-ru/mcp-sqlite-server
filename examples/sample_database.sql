-- A minimal example database to play with.
-- Build it with:  sqlite3 sample.db < examples/sample_database.sql

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_occurred_at ON events(occurred_at);

INSERT INTO users (email, name) VALUES
    ('alice@example.com', 'Alice'),
    ('bob@example.com', 'Bob'),
    ('carol@example.com', 'Carol');

INSERT INTO events (user_id, event_type, metadata) VALUES
    (1, 'signup', '{"source": "organic"}'),
    (1, 'login', '{"device": "mobile"}'),
    (2, 'signup', '{"source": "referral"}'),
    (3, 'signup', '{"source": "ads"}'),
    (3, 'login', '{"device": "desktop"}'),
    (3, 'purchase', '{"amount": 29.99, "currency": "USD"}');
