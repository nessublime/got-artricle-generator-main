from dataclasses import dataclass
from dotenv import load_dotenv
import os


@dataclass
class OpenAIConfig:
    organization: str
    api_key: str


@dataclass
class UnsplashConfig:
    api_key: str


@dataclass
class ServiceConfig:
    openai_config: OpenAIConfig
    unsplash_config: UnsplashConfig


def load_config() -> ServiceConfig:
    load_dotenv()

    organization = os.getenv("OPENAI_ORG")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    unsplash_api_key = os.getenv("UNSPLASH_API_KEY")

    if organization is None:
        raise Exception(f"No OPENAI_ORG env found")
    if openai_api_key is None:
        raise Exception(f"No OPENAI_API_KEY env found")
    if unsplash_api_key is None:
        raise Exception(f"No UNSPLASH_API_KEY env found")

    return ServiceConfig(
        openai_config=OpenAIConfig(
            api_key=openai_api_key,
            organization=organization
        ),
        unsplash_config=UnsplashConfig(
            api_key=unsplash_api_key
        )
    )
