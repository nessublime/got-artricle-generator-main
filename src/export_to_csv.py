import os
from dotenv import load_dotenv
import asyncio
import completion_data
import sqlite
import csv

CSV_HEADERS = [
    "keyword",
    "title",
    "category",
    "metatitle",
    "metadesc",
    "raw_content",
    "cleaned_content",
    "html_content",
    "img_url",
    "img_attribution_username"
]

GENERATED_DIR_PATH = "generated"
GENERATED_FILE_NAME = "generated.csv"


async def main():
    load_dotenv()

    connection = sqlite.get_sqlite_connection()
    sqlite.run_migrations(connection)

    completion_db = completion_data.CompletionDataDB(connection)

    generated_articles = completion_db.get_succeded()

    if not os.path.exists(GENERATED_DIR_PATH):
        os.makedirs(GENERATED_DIR_PATH)
    with open(f"{GENERATED_DIR_PATH}/{GENERATED_FILE_NAME}", "w", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(CSV_HEADERS)
        for article in generated_articles:
            writer.writerow([
                article.completion_input.keyword,
                article.title,
                article.completion_input.category,
                article.meta_title,
                article.meta_desc,
                article.raw_content,
                article.cleaned_content,
                article.html_content,
                article.img_url,
                article.img_attribution_username
            ])

asyncio.run(main())
