"""
Document summary generation utilities
Handles AI-powered document summarization
"""

from openai import OpenAI
import os


def generate_document_summary(document_text, openai_client, model="gpt-4o-mini"):
    """
    Generate a ~100 word summary of the document using OpenAI
    
    Args:
        document_text: The full document text
        openai_client: Initialized OpenAI client
        model: Model to use for summarization (default: gpt-4o-mini)
    
    Returns:
        str: Document summary
    """
    try:
        prompt = f"""You are a precise summarizer for legal and investment agreements.

Summarize the following document in about 100 words.

Focus on:
- The type of agreement (e.g., SAFE, investment, loan, etc.)
- The involved parties
- The main purpose or obligations
- Any key variables such as amount, dates, or governing law

Avoid filler language and boilerplate.
Output only the summary paragraph, without bullets or formatting.

Document Text:
{document_text[:5000]}"""  # Limit to first 5000 chars to save tokens

        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating document summary: {str(e)}")
        return "Summary unavailable"

