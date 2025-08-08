"""Code analysis utilities for extracting and summarizing code examples."""

import os
import sys
from typing import Any

import openai

# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")


def extract_code_blocks(
    markdown_content: str, min_length: int = 1000,
) -> list[dict[str, Any]]:
    """
    Extract code blocks from markdown content along with context.

    Args:
        markdown_content: The markdown content to extract code blocks from
        min_length: Minimum length of code blocks to extract (default: 1000 characters)

    Returns:
        List of dictionaries containing code blocks and their context
    """
    code_blocks = []

    # Find all occurrences of triple backticks
    backtick_positions = []
    pos = 0
    while True:
        pos = markdown_content.find("```", pos)
        if pos == -1:
            break
        backtick_positions.append(pos)
        pos += 3

    # Process pairs of backticks
    i = 0
    while i < len(backtick_positions) - 1:
        start_pos = backtick_positions[i]
        end_pos = backtick_positions[i + 1]

        # Extract the content between backticks
        code_section = markdown_content[start_pos + 3 : end_pos]

        # Check if there's a language specifier on the first line
        lines = code_section.split("\n", 1)
        if len(lines) > 1:
            # Check if first line is a language specifier (no spaces, common language names)
            first_line = lines[0].strip()
            if first_line and " " not in first_line and len(first_line) < 20:
                language = first_line
                code_content = lines[1] if len(lines) > 1 else ""
            else:
                language = ""
                code_content = code_section
        else:
            language = ""
            code_content = code_section

        # Skip if code block is too short
        if len(code_content) < min_length:
            i += 2  # Move to next pair
            continue

        # Extract context before (1000 chars)
        context_start = max(0, start_pos - 1000)
        context_before = markdown_content[context_start:start_pos].strip()

        # Extract context after (1000 chars)
        context_end = min(len(markdown_content), end_pos + 3 + 1000)
        context_after = markdown_content[end_pos + 3 : context_end].strip()

        code_blocks.append(
            {
                "code": code_content,
                "language": language,
                "context_before": context_before,
                "context_after": context_after,
                "full_context": f"{context_before}\n\n{code_content}\n\n{context_after}",
            },
        )

        # Move to next pair (skip the closing backtick we just processed)
        i += 2

    return code_blocks


def generate_code_example_summary(
    code: str, context_before: str = "", context_after: str = "",
) -> str:
    """
    Generate a summary for a code example using its surrounding context.

    Args:
        code: The code example
        context_before: Context before the code
        context_after: Context after the code

    Returns:
        A summary of what the code example demonstrates
    """
    model_choice = os.getenv("MODEL_CHOICE", "gpt-4o-mini")

    # Create the prompt
    prompt = f"""<context_before>
{context_before[-500:] if len(context_before) > 500 else context_before}
</context_before>

<code_example>
{code[:1500] if len(code) > 1500 else code}
</code_example>

<context_after>
{context_after[:500] if len(context_after) > 500 else context_after}
</context_after>

Based on the code example and its surrounding context, provide a concise summary (2-3 sentences) that describes what this code example demonstrates and its purpose. Focus on the practical application and key concepts illustrated.
"""

    try:
        response = openai.chat.completions.create(
            model=model_choice,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise code example summaries.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=100,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error generating code example summary: {e}", file=sys.stderr)
        return "Code example for demonstration purposes."


def process_code_example(args):
    """
    Process a single code example to generate its summary.
    This function is designed to be used with concurrent.futures.

    Args:
        args: Tuple containing (code, context_before, context_after)

    Returns:
        The generated summary
    """
    code, context_before, context_after = args
    return generate_code_example_summary(code, context_before, context_after)
