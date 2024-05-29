from dataclasses import dataclass
import csv
import completion_data
import generator


def load_keywords() -> list[completion_data.CompletionInput]:
    keywords: list[tuple[str, str]] = []
    with open("keywords.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        _ = next(reader)
        for row in reader:
            keywords.append(completion_data.CompletionInput(row[0], row[1]))

    return keywords


def load_category_dict() -> dict[str, str]:
    category_dict = dict[str, str]()
    with open("categories.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        _ = next(reader)
        for row in reader:
            category_dict[row[0]] = row[1]

    return category_dict



def load_completions_config():
    return generator.CompletionsConfig(
        generate_images=True,
        title_pipe=lambda input: f"""{input.keyword}""",
        content_prompt_pipe=lambda input: f"""We are a web that makes great and polished articles about petanque in spanish.
        Generate an detailed, eye-catching, SEO optimized web article in html format about "{input.keyword} in spanish. With introduction and headings. Write it in a professional but casual tone. Make important sentences bold.""",
        meta_desc_prompt_pipe=lambda input: f"""Genera un parrafo de metadescripción SEO de menos de 155 caracteres sobre "{input.keyword}".""",
        meta_title_prompt_pipe=lambda input: f"""Genera un meta-título SEO para la keyword "{input.keyword}" con menos de 57 caracteres y sin separadores."""
    )
