from dataclasses import dataclass
import sqlite3
import json
from enum import Enum
from typing import Optional


class CompletionErrorType(Enum):
    CONTENT = 1
    META_TITLE = 2
    META_DESC = 3
    IMG = 4
    TITLE = 5

    def toString(self):
        return self.name


@dataclass
class CompletionInput:
    keyword: str
    category: str


@dataclass
class CompletionPrompts:
    content: str
    meta_desc: str
    meta_title: str


@dataclass
class CompletionError:
    error_type: CompletionErrorType
    reason: str

    def toJSON(self):
        return json.dumps(self, default=lambda o: {
            "error_type": o.error_type.toString(),
            "reason": o.reason
        },
            sort_keys=True)


@dataclass
class CompletionData:
    completion_input: CompletionInput
    title: str
    raw_content: str
    cleaned_content: str
    html_content: str
    meta_title: str
    meta_desc: str
    img_url: str
    img_attribution_username: str
    errors: list[CompletionError]
    used_prompts: CompletionPrompts


class CompletionDataDB:
    connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def save_completion_data(self, data: CompletionData):
        persistence = map_to_persistence(data)
        with self.connection as cursor:
            cursor.execute("""
        INSERT INTO article_completions VALUES
        ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
      """, persistence)

    def update_completion_data(self, data: CompletionData):
        persistence = map_to_persistence(data)
        with self.connection as cursor:
            cursor.execute(f"""
        UPDATE article_completions
        SET title = $1, raw_content = $2, cleaned_content = $3, meta_title = $4, meta_desc = $5, img_url = $6, img_attribution_username = $7, errors = $8, prompts = $9
        WHERE keyword = '{data.completion_input.keyword}'
      """, (data.title, data.raw_content, data.cleaned_content, data.meta_title, data.meta_desc, data.img_url, data.img_attribution_username, persistence[10], persistence[11]))

    def get_by_keyword(self, keyword: str) -> Optional[CompletionData]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"""
        SELECT * FROM article_completions a WHERE a.keyword = '{keyword}'
      """)
            article = cursor.fetchone()

            if article is None:
                return None

            return map_to_domain(article)
        except Exception as e:
            print(str(e))
            return None
        finally:
            cursor.close()

    def get_failed(self) -> list[CompletionData]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
        SELECT * FROM article_completions a WHERE a.errors IS NOT NULL
      """)
            articles = cursor.fetchall()

            return list(map(lambda x: map_to_domain(x), articles))
        finally:
            cursor.close()

    def get_succeded(self) -> list[CompletionData]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
        SELECT * FROM article_completions a WHERE a.errors IS NULL
      """)
            articles = cursor.fetchall()

            return list(map(lambda x: map_to_domain(x), articles))
        finally:
            cursor.close()


def map_error_type(error_type: str) -> CompletionErrorType:
    match error_type:
        case "CONTENT":
            return CompletionErrorType.CONTENT
        case "META_TITLE":
            return CompletionErrorType.META_TITLE
        case "META_DESC":
            return CompletionErrorType.META_DESC
        case "IMG":
            return CompletionErrorType.IMG
        case "TITLE":
            return CompletionErrorType.TITLE
        case _:
            raise Exception("Invalid error_type")


def map_to_domain(article) -> CompletionData:
    error_j = json.loads(article[10]) if article[10] is not None else None

    errors = list(map(lambda x: CompletionError(map_error_type(
        x["error_type"]), x["reason"]), error_j["errors"])) if error_j is not None else None

    prompts_json = json.loads(article[11])["prompts"]
    prompts = CompletionPrompts(
        content=prompts_json["content"],
        meta_desc=prompts_json["meta_desc"],
        meta_title=prompts_json["meta_title"],
    )

    return CompletionData(
        CompletionInput(article[0], article[1]),
        article[2],
        article[3],
        article[4],
        article[5],
        article[6],
        article[7],
        article[8],
        article[9],
        errors,
        prompts
    )


def map_to_persistence(article: CompletionData):
    json_o = json.dumps({"errors": list(map(lambda x: {
        "error_type": x.error_type.toString(),
        "reason": x.reason
    }, article.errors))}) if article.errors is not None else None

    prompts_json_o = json.dumps({"prompts": article.used_prompts.__dict__})

    return (
        article.completion_input.keyword,
        article.completion_input.category,
        article.title,
        article.raw_content,
        article.cleaned_content,
        article.html_content,
        article.meta_title,
        article.meta_desc,
        article.img_url,
        article.img_attribution_username,
        json_o,
        prompts_json_o
    )
