from openai import OpenAI
from django.conf import settings
from api.prompts.extraction_prompt import EXTRACTION_PROMPT
import json

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def extract_attributes_llm(query):

    response = client.responses.create(
        model="gpt-4.1-mini",
        temperature=0,
        input=[
            {
                "role": "system",
                "content": EXTRACTION_PROMPT
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )

    # Extract text output safely
    output_text = response.output_text

    return json.loads(output_text)