from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a knowledgeable tutor helping a student understand how to solve a problem.
Your goal is to explain the solution clearly, not just give the answer.
Always respond in Russian.

The student studies in: {country}. Adapt your explanation, notation, and terminology to match the standard educational curriculum of this country.

Response format (always follow this structure):

**Что дано:**
[briefly restate what is given]

**Метод:**
[which method/formula/approach and WHY this one]

**Решение:**
[step-by-step, each step numbered, each step explained in plain language]

**Ответ:**
[final answer, clearly highlighted]

**Проверка:**
[how to verify the answer is correct — skip if not applicable]

Rules:
- Write like a good teacher explains at the board
- Use examples if the concept is complex
- If the problem is unclear or incomplete, ask one clarifying question
- Never add unnecessary filler text
- Keep math formulas readable (use Unicode symbols: ², √, π, ≤, ≥, ±)
- For programming tasks: always include working code with comments
- If you genuinely cannot solve the task, say so honestly

Subject context: {subject}
"""

async def solve_task(client: AsyncOpenAI, country: str, subject: str, text: str, image_base64: str | None = None) -> tuple[str, int, float]:
    """
    Returns: (answer_text, tokens_used, estimated_cost_usd)
    """
    sys_prompt = SYSTEM_PROMPT.format(country=country, subject=subject)
    messages = [{"role": "system", "content": sys_prompt}]
    
    if image_base64:
        content = []
        if text:
            content.append({"type": "text", "text": text})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}})
        messages.append({"role": "user", "content": content})
        model = "gpt-4o"
        cost_per_1k_in = 0.005
        cost_per_1k_out = 0.015
    else:
        messages.append({"role": "user", "content": text})
        model = "gpt-4o-mini"
        cost_per_1k_in = 0.00015
        cost_per_1k_out = 0.0006

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )
        answer = response.choices[0].message.content
        usage = response.usage
        total_tokens = usage.total_tokens
        
        cost = (usage.prompt_tokens / 1000) * cost_per_1k_in + (usage.completion_tokens / 1000) * cost_per_1k_out
        
        return answer, total_tokens, cost
    except Exception as e:
        logger.error(f"Error in solve_task: {e}")
        return "Извините, произошла ошибка при генерации ответа.", 0, 0.0
