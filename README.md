# mcp-sqlite-server

A minimal but production-safe **MCP server for SQLite** — lets Claude (or any MCP client) talk to a local SQLite database with read/write tools and built-in safety guards against destructive operations.

> Connect Claude to your local SQLite database in 30 seconds. No external services, no API keys, no recurring cost — just a local Python server.

---

## 🇷🇺 На русском

**Кому это подойдёт:**
- У тебя есть **локальная SQLite-база** и ты хочешь чтобы Claude/Cursor мог её читать/писать без копипасты в чат
- Ты indie-developer и ищешь **production-ready пример MCP-сервера** для своего проекта
- Тебе нужна **кастомная версия** под твою специфическую базу/таблицу/workflow

**Что входит в проект:** рабочий код на Python (~250 строк), безопасность (запрет DROP/TRUNCATE по умолчанию), pyproject.toml для установки одной командой, готовый config для Claude Desktop, sample-база для теста.

**Заказать кастомную версию** (под твою БД, твои tools, твою специфику): [Kwork → agentforge_ru](https://kwork.ru/user/agentforge_ru) — от 3 500 ₽, сроки 48-72 часа.

---

## Why this exists

Asking Claude "look at my SQLite database" usually means copy-pasting `SELECT *` results into chat. That's painful.

This MCP server gives Claude direct, structured access to SQLite with:
- ✅ Schema introspection (list tables, get CREATE statements)
- ✅ Read queries (parameterized SELECT)
- ✅ Write operations (INSERT / UPDATE / DELETE) — gated by an explicit `allow_writes` flag
- 🚫 **Blocked by default:** `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `ATTACH DATABASE`, `PRAGMA writable_schema = 1` — these can wipe data and require an additional `--unsafe` flag

## Tools exposed to the LLM

| Tool | Purpose | Default behavior |
|---|---|---|
| `list_tables` | Lists all user tables in the database | Always available |
| `get_schema(table)` | Returns the CREATE TABLE statement for a table | Always available |
| `query(sql, params)` | Runs a SELECT query with parameter binding | Always available |
| `execute_write(sql, params)` | Runs INSERT/UPDATE/DELETE with parameter binding | Off by default; enable with `--allow-writes` |
| `database_stats` | Returns row counts and database file size | Always available |

## Installation

```bash
git clone https://github.com/agentforge-ru/mcp-sqlite-server
cd mcp-sqlite-server
pip install -e .
```

Or in one line:

```bash
pip install git+https://github.com/agentforge-ru/mcp-sqlite-server
```

## Wiring into Claude Desktop

Add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "python",
      "args": ["-m", "mcp_sqlite_server", "/absolute/path/to/your/database.db"]
    }
  }
}
```

To enable write operations:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "python",
      "args": [
        "-m", "mcp_sqlite_server",
        "/absolute/path/to/your/database.db",
        "--allow-writes"
      ]
    }
  }
}
```

Restart Claude Desktop. Tools appear automatically in the model's context.

## Usage examples (in Claude Desktop chat)

```
You: What tables does the analytics database have?
Claude: [calls list_tables] You have 4 tables: events, users, sessions, retention_cohorts.

You: Show me the schema of the events table.
Claude: [calls get_schema(table="events")]
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata JSON
)

You: How many users signed up last week?
Claude: [calls query(sql="SELECT COUNT(*) FROM users WHERE created_at >= date('now', '-7 days')")]
1,247 users signed up in the last 7 days.
```

## Safety model

This server uses a **whitelist-by-keyword approach** for blocking destructive operations. Specifically blocked unless `--unsafe`:

- `DROP TABLE`, `DROP DATABASE`, `DROP INDEX`, `DROP VIEW`
- `TRUNCATE TABLE`
- `ATTACH DATABASE`, `DETACH DATABASE`
- `PRAGMA writable_schema`
- `VACUUM` (long-running, can lock the database)

This is **defense-in-depth, not bulletproof.** Always:
- Run against a copy of production data, not production directly
- Backup before enabling `--allow-writes`
- Review the audit log (printed to stderr) after sessions

## Architecture

```
[ Claude Desktop / Claude Code / Cursor ]
              ↓ MCP protocol (stdio)
        [ mcp-sqlite-server ]
              ↓ sqlite3 (stdlib)
        [ your-database.db ]
```

No daemon, no port, no HTTP. The server runs as a subprocess of the MCP client and communicates over stdin/stdout. When the client closes, the server exits.

## Limitations (honest)

- **SQLite only.** Not PostgreSQL, not MySQL. For those, see other MCP servers in the ecosystem.
- **No connection pooling.** Each session opens a single connection.
- **No transactions exposed.** Each `execute_write` is auto-committed. If you need multi-statement transactions, wrap them in your own `BEGIN; ... COMMIT;`.
- **No views/triggers/CTEs are explicitly tested.** They work because SQLite handles them, but I haven't shipped formal test coverage for them yet.

## License

MIT — see `LICENSE`. Use it, fork it, send PRs.

## Author

Built by [agentforge_ru](https://github.com/agentforge-ru) — custom Claude Code subagents, MCP servers, and Telegram bots with AI logic.

If you want a custom MCP server for your specific data source (your CRM, your internal API, your Notion workspace) — [open an issue](https://github.com/agentforge-ru/mcp-sqlite-server/issues) or reach out via Kwork.
