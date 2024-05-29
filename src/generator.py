import os
from typing import Callable, TypeVar, Any
import requests
from dataclasses import dataclass
import ia_generator
from tqdm import tqdm
import markdown
from concurrent import futures
import asyncio
import completion_data
import config
from collections.abc import Coroutine


@dataclass
class CompletionsConfig:
    generate_images: bool
    title_pipe: Callable[[completion_data.CompletionInput], str]
    content_prompt_pipe: Callable[[completion_data.CompletionInput], str]
    meta_title_prompt_pipe: Callable[[completion_data.CompletionInput], str]
    meta_desc_prompt_pipe: Callable[[completion_data.CompletionInput], str]


sem = asyncio.Semaphore(4)


class ArticleGenerator:
    openai_service: ia_generator.OpenAICompletionService
    completion_db: completion_data.CompletionDataDB
    category_dict: dict[str, str]
    completion_config: CompletionsConfig
    service_config: config.ServiceConfig

    def __init__(self, openai_service: ia_generator.OpenAICompletionService, completion_db: completion_data.CompletionDataDB, category_dict: dict[str, str], completion_config: CompletionsConfig, service_config: config.ServiceConfig) -> None:
        self.openai_service = openai_service
        self.category_dict = category_dict
        self.completion_config = completion_config
        self.completion_db = completion_db
        self.service_config = service_config

    async def start_generation(self, inputs: list[completion_data.CompletionInput]):
        await asyncio.gather(
            *[self.__safe_generate_article_async(input) for input in inputs]
        )

    async def regenerate_articles(self):
        failed_articles = self.completion_db.get_failed()

        if len(failed_articles) <= 0:
            print("No failed articles to re-generate :)")
            return

        await asyncio.gather(
            *[self.__safe_regen_article(article) for article in failed_articles]
        )

    async def __safe_generate_article_async(self, input: completion_data.CompletionInput):
        async with sem:
            return await self.generate_article(input)

    async def __safe_regen_article(self, article: completion_data.CompletionData) -> completion_data.CompletionData:
        async with sem:
            return await self.__regenerate_article(article)

    async def __regenerate_article(self, article: completion_data.CompletionData) -> completion_data.CompletionData:
        if article.errors is None:
            return article

        new_errors: list[completion_data.CompletionError] = []

        meta_title_prompt = self.completion_config.meta_title_prompt_pipe(
            article.completion_input)
        meta_desc_prompt = self.completion_config.meta_desc_prompt_pipe(article.completion_input)
        content_prompt = self.completion_config.content_prompt_pipe(article.completion_input)

        for error in article.errors:
            if error.error_type == completion_data.CompletionErrorType.CONTENT:
                raw_content = await generate_article_content(self.openai_service, content_prompt)

                match raw_content:
                    case completion_data.CompletionError():
                        new_errors.append(raw_content)
                    case str():
                        article.raw_content = raw_content
                        article.cleaned_content = get_cleaned_content(
                            raw_content)

            if error.error_type == completion_data.CompletionErrorType.META_DESC:
                meta_desc = await generate_meta_desc(self.openai_service, meta_desc_prompt)

                match meta_desc:
                    case completion_data.CompletionError():
                        new_errors.append(meta_desc)
                    case str():
                        article.meta_desc = meta_desc

            if error.error_type == completion_data.CompletionErrorType.META_TITLE:
                meta_title = await generate_meta_title(self.openai_service, meta_title_prompt)

                match meta_title:
                    case completion_data.CompletionError():
                        new_errors.append(meta_title)
                    case str():
                        article.meta_title = meta_title

            if error.error_type == completion_data.CompletionErrorType.IMG:
                img = await get_img_url(self.service_config.unsplash_config, article.completion_input, self.category_dict)

                match img:
                    case completion_data.CompletionError():
                        new_errors.append(img)
                    case _:
                        article.img_url = img[0]
                        article.img_attribution_username = img[1]

            article.errors = new_errors if len(new_errors) > 0 else None
            self.completion_db.update_completion_data(article)

            if len(new_errors) > 0:
                print(
                    f"[FAILED] Article re-generated with errors for keyword {article.completion_input.keyword}")
            else:
                print(
                    f"[OK] Article completion re-generated sucessfuly for keyword {article.completion_input.keyword}")

            return article

    async def generate_article(self, input: completion_data.CompletionInput):
        existing_completion = self.completion_db.get_by_keyword(input.keyword)
        if existing_completion is not None:
            print(
                f"[SKIP] Article with keyword {existing_completion.completion_input.keyword} already exists, skipping\n")
            return

        title = self.completion_config.title_pipe(input)
        meta_title_prompt = self.completion_config.meta_title_prompt_pipe(
            input)
        meta_desc_prompt = self.completion_config.meta_desc_prompt_pipe(input)
        content_prompt = self.completion_config.content_prompt_pipe(input)

        metatitle, metadesc, raw_content, img_data = await asyncio.gather(
            generate_meta_title(self.openai_service, meta_title_prompt),
            generate_meta_desc(self.openai_service, meta_desc_prompt),
            generate_article_content(self.openai_service, content_prompt),
            get_img_url(self.service_config.unsplash_config,
                        input, self.category_dict),
        )

        errors = collect_errors([metatitle, metadesc, raw_content, img_data])

        self.completion_db.save_completion_data(
            completion_data.CompletionData(
                completion_input=input,
                raw_content=raw_content if error_or_none(
                    raw_content) is not None else None,
                cleaned_content=get_cleaned_content(raw_content) if error_or_none(
                    raw_content) is not None else None,
                html_content=None,
                meta_desc=metadesc if error_or_none(
                    metadesc) is not None else None,
                meta_title=metatitle if error_or_none(
                    metatitle) is not None else None,
                title=title,
                img_url=img_data[0] if error_or_none(
                    img_data) is not None else None,
                img_attribution_username=img_data[1] if error_or_none(
                    img_data) is not None else None,
                errors=errors if len(errors) > 0 else None,
                used_prompts=completion_data.CompletionPrompts(
                    content=content_prompt,
                    meta_desc=meta_desc_prompt,
                    meta_title=meta_title_prompt
                )
            )
        )

        if len(errors) > 0:
            print(
                f"[FAILED] Article generated with errors for keyword {input.keyword}")
        else:
            print(
                f"[OK] Article completion generated sucessfuly for keyword {input.keyword}")


T = TypeVar("T")


def error_or_none(c: T | completion_data.CompletionError) -> T | None:
    match c:
        case completion_data.CompletionError():
            return None
        case _:
            return c


def collect_errors(datas: list[T | completion_data.CompletionError]) -> list[completion_data.CompletionError]:
    errors: list[completion_data.CompletionError] = []
    for data in datas:
        match data:
            case completion_data.CompletionError():
                errors.append(data)
            case _:
                continue
    return errors


def get_cleaned_content(raw_content: str) -> str:
    replaced = raw_content.replace("\r\n", "\n").replace("\r", "")

    # Remove first line to remote title from content
    cleaned_content = "\n".join(replaced.split("\n")[1:])

    return cleaned_content


def article_content_to_html(content: str) -> str:
    return markdown.markdown(content)


async def generate_meta_desc(openai_service: ia_generator.OpenAICompletionService, prompt: str) -> str | completion_data.CompletionError:
    try:
        return await openai_service.generate_completion(prompt, max_tokens=100)
    except Exception as e:
        return completion_data.CompletionError(completion_data.CompletionErrorType.META_DESC, str(e))


async def generate_article_content(openai_service: ia_generator.OpenAICompletionService, prompt: str) -> str | completion_data.CompletionError:
    try:
        completion = await openai_service.generate_completion(prompt, max_tokens=3711, temperature=0.5, presence_penalty=0.8)

        return completion
    except Exception as e:
        return completion_data.CompletionError(completion_data.CompletionErrorType.CONTENT, str(e))


async def generate_meta_title(openai_service: ia_generator.OpenAICompletionService, prompt: str) -> str | completion_data.CompletionError:
    try:
        return await openai_service.generate_completion(prompt, max_tokens=45)
    except Exception as e:
        return completion_data.CompletionError(completion_data.CompletionErrorType.META_TITLE, str(e))


async def get_img_url(
    unsplash_config: config.UnsplashConfig,
    input: completion_data.CompletionInput,
    category_dict: dict[str, str]
) -> tuple[str, str] | completion_data.CompletionError:
    try:
        url = "https://api.unsplash.com/photos/random"

        img_query = category_dict[input.category]
        querystring = {"query": f"{img_query}", "count": "1"}

        headers = {
            "Authorization": f"Client-ID {unsplash_config.api_key}"
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.request(
                "GET", url, headers=headers, params=querystring)
        )

        if response.status_code != 200:
            return completion_data.CompletionError(completion_data.CompletionErrorType.IMG, "Bad request executing unsplash api")

        values = response.json()

        if values is None or len(values) == 0:
            return completion_data.CompletionError(completion_data.CompletionErrorType.IMG, "No img url found")

        return [values[0]["urls"]["regular"], values[0]["user"]["username"]]
    except Exception as e:
        return completion_data.CompletionError(completion_data.CompletionErrorType.IMG, str(e))
