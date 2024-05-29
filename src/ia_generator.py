import openai
import asyncio
import config


class OpenAICompletionService:
    openai_config: config.OpenAIConfig

    def __init__(self, openai_config: config.OpenAIConfig) -> None:
        self.openai_config = openai_config
        openai.organization = openai_config.organization
        openai.api_key = openai_config.api_key

    async def generate_completion(self, prompt: str, max_tokens=1024, temperature=0.2, presence_penalty=0):
        _prompt = f"""{prompt}. End string with <end>.

    texto:
    """

        for _ in range(5):
            try:
                loop = asyncio.get_event_loop()
                answer = await loop.run_in_executor(None, lambda: openai.Completion.create(
                    model="text-davinci-003",
                    prompt=_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    presence_penalty=presence_penalty,
                ))

                generated_text: str = answer["choices"][0]["text"]
                prompt = prompt + generated_text

                if "<end>" in generated_text or generated_text == "":
                    return generated_text.replace("<end>", "").strip()
            except Exception as e:
                print("Error ocurred in completion: ", e)
                continue
