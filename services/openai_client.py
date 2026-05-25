import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env.local")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o"

DEFAULT_SYSTEM_PROMPT = (
    "You are a faithful member of the Church of Jesus Christ of Latter-Day Saints (LDS). "
    "You always provide answers in line with LDS beliefs. In all responses, cite references "
    "from scriptures and modern Prophets in your answers. Be concise and format as a table "
    "when making comparisons."
)


def get_embeddings(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def chat_completion(messages: list[dict], system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(model=CHAT_MODEL, messages=full_messages)
    return response.choices[0].message.content


def chat_completion_stream(messages: list[dict], system_prompt: str = DEFAULT_SYSTEM_PROMPT):
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    stream = client.chat.completions.create(
        model=CHAT_MODEL, messages=full_messages, stream=True
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
