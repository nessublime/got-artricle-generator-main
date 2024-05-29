import sqlite3


def get_sqlite_connection():
    return sqlite3.connect("db/article_completions.db")


def run_migrations(con: sqlite3.Connection):
    # Run migration
    with con as cursor:
        cursor.execute("""CREATE TABLE IF NOT EXISTS article_completions(
          keyword VARCHAR NOT NULL PRIMARY KEY,
          category VARCHAR NOT NULL,
          title VARCHAR,
          raw_content VARCHAR,
          cleaned_content VARCHAR,
          html_content VARCHAR,
          meta_title VARCHAR,
          meta_desc VARCHAR,
          img_url VARCHAR,
          img_attribution_username VARCHAR,
          errors JSON,
          prompts JSON NOT NULL
          )""")
