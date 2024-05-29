import ia_generator
import asyncio
import completion_data
import generator
import sqlite
import loaders
import config


async def main():
    my_config = config.load_config()

    category_dict = loaders.load_category_dict()
    completions_config = loaders.load_completions_config()

    connection = sqlite.get_sqlite_connection()
    sqlite.run_migrations(connection)

    completion_db = completion_data.CompletionDataDB(connection)
    openai_service = ia_generator.OpenAICompletionService(
        my_config.openai_config)
    article_generator = generator.ArticleGenerator(
        openai_service,
        completion_db,
        category_dict,
        completions_config,
        my_config
    )

    await article_generator.regenerate_articles()


asyncio.run(main())
