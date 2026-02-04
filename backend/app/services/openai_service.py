from openai import AsyncOpenAI
from app.config import get_settings
import json
import re
from typing import Optional, Dict, Any

settings = get_settings()


class OpenAIService:
    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = settings.openai_model
        self.dalle_model = settings.dalle_model

    async def generate_content(
        self,
        content_type: str,
        topic: Optional[str] = None,
        platforms: list[str] = None,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate social media content using OpenAI."""

        if platforms is None:
            platforms = ["linkedin"]

        platform_str = ", ".join(platforms)

        if content_type == "educational":
            system_prompt = self._get_educational_prompt(platform_str)
        elif content_type == "motivation":
            system_prompt = self._get_motivation_prompt(platform_str)
        else:
            system_prompt = self._get_general_prompt(platform_str)

        user_prompt = f"Create a post about: {topic}" if topic else "Create an engaging post based on your expertise."

        if custom_prompt:
            user_prompt = custom_prompt

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.85
            )

            raw_content = response.choices[0].message.content.strip()

            # Parse JSON response
            parsed = self._parse_ai_response(raw_content)

            return {
                "success": True,
                "content": parsed.get("content", raw_content),
                "image_prompt": parsed.get("image_prompt", ""),
                "hashtags": parsed.get("hashtags", []),
                "topic": topic,
                "content_type": content_type
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "image_prompt": ""
            }

    async def generate_image(self, prompt: str) -> Dict[str, Any]:
        """Generate an image using DALL-E."""
        try:
            response = await self.client.images.generate(
                model=self.dalle_model,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )

            return {
                "success": True,
                "image_url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_url": ""
            }

    def _parse_ai_response(self, raw: str) -> Dict[str, Any]:
        """Parse AI response, handling JSON and plain text."""
        try:
            # Remove markdown code blocks if present
            json_str = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
            json_str = re.sub(r'```$', '', json_str)

            # Find JSON object
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end + 1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # If not JSON, return raw content
        return {"content": raw}

    def _get_educational_prompt(self, platforms: str) -> str:
        return f"""You are a tech founder and AI expert. Write educational content for: {platforms}

Style: Direct, punchy, no fluff. Like Alex Hormozi meets Justin Welsh.

STRUCTURE:
1. HOOK (first line): Under 50 characters. Pattern interrupt.
2. RE-HOOK: One sentence explaining what they'll learn
3. BODY: Use "" bullets. 5-7 points maximum. Short sentences.
4. TAKEAWAY: One powerful sentence
5. CTA: Question or invite saves/shares
6. HASHTAGS: Include 10-15 relevant hashtags

RULES:
- 80-150 words
- Maximum 2 emojis
- Each line is its own paragraph
- Be SPECIFIC with numbers and examples
- Write like you've actually done this

Output ONLY valid JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional image description]", "hashtags": ["tag1", "tag2"]}}"""

    def _get_motivation_prompt(self, platforms: str) -> str:
        return f"""You are a tech founder sharing wisdom for: {platforms}

Style: Short, punchy, quotable. Like Alex Hormozi.

STRUCTURE FOR ONE-LINERS:
"[Bold statement]

[2-3 sentences expanding with personal touch]

[One-line takeaway]

Save this."

STRUCTURE FOR LESSONS:
"[Number] things I learned:

1. [Lesson] - [Short explanation]
2. [Lesson] - [Short explanation]
3. [Lesson] - [Short explanation]

Which one resonates with you?"

RULES:
- 40-80 words MAXIMUM
- Each line is its own paragraph
- NO corporate speak
- 0-2 emojis only
- 10+ hashtags at the end
- Make it quotable

Output ONLY JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional motivational image description]", "hashtags": ["tag1", "tag2"]}}"""

    def _get_general_prompt(self, platforms: str) -> str:
        return f"""You are a tech founder creating content for: {platforms}

Create engaging, valuable content that resonates with professionals and entrepreneurs.

RULES:
- Be authentic and specific
- Share real insights or opinions
- Include a clear takeaway
- End with engagement prompt (question or CTA)
- Include 10-15 relevant hashtags
- 50-150 words

Output ONLY JSON:
{{"content": "[full post with hashtags]", "image_prompt": "[optional image description]", "hashtags": ["tag1", "tag2"]}}"""


# Singleton instance
_openai_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service
