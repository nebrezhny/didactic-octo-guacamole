from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """
Determine the subject of this task in one word.
Reply with exactly one of: math / physics / chemistry / programming / russian / english / history / biology / other

Task: {text}

Reply (one word only):
"""

async def classify_subject(client: AsyncOpenAI, text: str, image_base64: str | None = None) -> str:
    messages = [
        {"role": "system", "content": "You are a subject classifier. Reply with exactly one word from the allowed list."}
    ]
    
    if image_base64:
        content = [
            {"type": "text", "text": CLASSIFY_PROMPT.format(text=text or "See image.")},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
        messages.append({"role": "user", "content": content})
        model = "gpt-4o"
    else:
        messages.append({"role": "user", "content": CLASSIFY_PROMPT.format(text=text)})
        model = "gpt-4o-mini"

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=10,
            temperature=0.0
        )
        subject = response.choices[0].message.content.strip().lower()
        allowed = {"math", "physics", "chemistry", "programming", "russian", "english", "history", "biology"}
        return subject if subject in allowed else "other"
    except Exception as e:
        logger.error(f"Error in classify_subject: {e}")
        return "other"
