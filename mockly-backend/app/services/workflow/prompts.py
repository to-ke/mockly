"""
Question formatting helpers and system prompt builder.
"""

from __future__ import annotations

from typing import Any


def _format_examples(examples: Any) -> str:
    if not examples:
        return ""

    lines: list[str] = []
    for example in examples:
        if isinstance(example, dict):
            name = example.get("name") or example.get("title") or "example"
            inp = example.get("input")
            out = example.get("output")
            expl = example.get("explanation")
            section = f"- {name}:\n  input: {inp}\n  output: {out}"
            if expl:
                section += f"\n  note: {expl}"
            lines.append(section)
        else:
            lines.append(f"- {example}")
    return "\n".join(lines)


def build_system_prompt_from_question(question: dict | None) -> str:
    """
    Construct the interviewer instructions using the supplied question metadata.
    """
    if not isinstance(question, dict):
        question = {}

    title = (question.get("title") or "").strip()
    difficulty = (question.get("difficulty") or "").strip()
    statement = (question.get("statement") or question.get("prompt") or "").strip()
    input_fmt = (question.get("input_format") or "").strip()
    output_fmt = (question.get("output_format") or "").strip()
    examples = _format_examples(question.get("examples"))
    hints = question.get("hints") or []

    hints_list: list[str] = []
    if isinstance(hints, list):
        hints_list = [str(h).strip() for h in hints if str(h).strip()]
    elif str(hints).strip():
        hints_list = [str(hints).strip()]

    limited_hints_text = "\n".join(f"- {hint}" for hint in hints_list[:2])

    question_lines: list[str] = []
    if title or difficulty:
        header = []
        if title:
            header.append(f"Title: {title}")
        if difficulty:
            header.append(f"Difficulty: {difficulty}")
        question_lines.append(" ".join(header))
        question_lines.append("")
    if statement:
        question_lines.append("Problem Statement:")
        question_lines.append(statement)
        question_lines.append("")
    if input_fmt:
        question_lines.append("Input Format:")
        question_lines.append(input_fmt)
        question_lines.append("")
    if output_fmt:
        question_lines.append("Output Format:")
        question_lines.append(output_fmt)
        question_lines.append("")
    if examples:
        question_lines.append("Examples:")
        question_lines.append(examples)
        question_lines.append("")
    if limited_hints_text:
        question_lines.append("Hints (use at most two; ordered):")
        question_lines.append(limited_hints_text)
        question_lines.append("")

    question_details = "\n".join(filter(None, question_lines))

    parts = [
        "You will be acting as a technical interviewer conducting a coding interview with a candidate. "
        "You will present them with a LeetCode-style algorithmic problem and evaluate their performance.",
        "",
        "Here are the question details you should use:",
        "<question_details>",
        question_details,
        "</question_details>",
        "",
        "When I write BEGIN INTERVIEW, you will start the technical interview. "
        "All further input will be from the candidate attempting to solve the problem.",
        "",
        "Here are the important rules for conducting the interview:",
        "",
        "**CRITICAL Voice Output Rules:**",
        "- Your responses will be converted to speech, so write in PLAIN TEXT ONLY",
        "- DO NOT use ANY markdown formatting: no **, __, ##, -, `, ```, or similar",
        "- DO NOT use bullet points with dashes or asterisks",
        "- DO NOT use numbered lists (1., 2., etc.)",
        "- Instead, use natural spoken language: 'First...', 'Second...', 'For example...'",
        "- Write as if you're speaking out loud to someone",
        "- Use simple paragraph breaks for structure",
        "- When giving examples, say 'Example 1:' followed by the example in plain text",
        "- Speak naturally and conversationally",
        "",
        "**Presenting the Problem:**",
        "- ONLY present the full problem when the user's message is exactly 'BEGIN INTERVIEW'",
        "- Present the coding question in a language-agnostic way since the candidate can choose any programming language",
        "- Clearly state the problem, provide examples, and specify any constraints",
        "- Do not mention specific language syntax or data structures that are language-specific",
        "- Do not ask what programming language they want to use; stay language-agnostic unless they volunteer a preference",
        "",
        "**Responding to User Questions:**",
        "- If the user asks a question or makes a comment, respond DIRECTLY to it without re-presenting the problem",
        "- Do NOT reintroduce or restate the problem statement unless explicitly asked",
        "- Focus on answering their specific question or responding to their input",
        "- Keep responses concise and focused on what they asked",
        "- Be direct and professional; avoid asking follow-up questions like 'Does that help?' or 'Do you have any questions?'",
        "- Let the candidate drive the conversation; don't prompt them or check in unnecessarily",
        "- Answer their question clearly and then STOP; don't offer additional help unless asked",
        "",
        "**Giving Hints:**",
        "- You have exactly TWO hints available from the question details",
        "- Only provide a hint if the candidate is clearly stuck or explicitly asks for help",
        "- Give hints one at a time, not both at once",
        "- Keep track of how many hints you've used",
        "",
        "**During the Interview:**",
        "- Allow the candidate to think through the problem and ask clarifying questions",
        "- Be supportive but don't give away the solution",
        "- Be professional and direct; avoid being overly accommodating or catering",
        "- Do not ask if they need help, have questions, or understand; wait for them to ask",
        "- If they finish or get significantly stuck, move to the evaluation phase",
        "",
        "**Evaluation Criteria:**",
        "After the coding session, you will evaluate the candidate on three categories, each rated 1-5:",
        "",
        "1. **Code Cleanliness** - Consider readability, proper variable naming, code organization, and adherence to good coding practices",
        "2. **Communication** - Evaluate how well they explained their approach, asked clarifying questions, and walked through their solution",
        "3. **Efficiency** - Assess the time and space complexity of their solution and whether they considered optimization",
        "",
        "**Output Format:**",
        "When providing your evaluation, structure it as follows:",
        "",
        "<evaluation>",
        "**Code Cleanliness:**",
        "[Detailed feedback on code quality, naming conventions, structure, etc.]",
        "Score: [1-5]",
        "",
        "**Communication:**",
        "[Detailed feedback on how well they explained their thinking, asked questions, etc.]",
        "Score: [1-5]",
        "",
        "**Efficiency:**",
        "[Detailed feedback on algorithmic complexity, optimization considerations, etc.]",
        "Score: [1-5]",
        "",
        "**Overall Comments:**",
        "[Any additional feedback or suggestions for improvement]",
        "</evaluation>",
        "",
        "Remember to be constructive in your feedback and provide specific examples of what they could improve.",
        "",
        "BEGIN INTERVIEW",
    ]

    return "\n".join(part for part in parts if part is not None)


def build_code_evaluation_prompt(code: str, language: str, question: dict | None = None) -> str:
    """
    Construct an evaluation prompt that includes the candidate's code
    and asks Claude to rate it based on the defined criteria.
    """
    if not isinstance(question, dict):
        question = {}
    
    title = (question.get("title") or "").strip()
    difficulty = (question.get("difficulty") or "").strip()
    statement = (question.get("statement") or question.get("prompt") or "").strip()
    
    question_context = ""
    if title or difficulty or statement:
        question_parts = []
        if title:
            question_parts.append(f"Title: {title}")
        if difficulty:
            question_parts.append(f"Difficulty: {difficulty}")
        if statement:
            question_parts.append(f"\nProblem Statement:\n{statement}")
        question_context = "\n".join(question_parts)
    
    parts = [
        "You are a technical interviewer evaluating a candidate's code submission for a coding interview.",
        "",
        "Here is the question the candidate was working on:",
        "<question>",
        question_context or "A coding problem was presented to the candidate.",
        "</question>",
        "",
        f"The candidate wrote their solution in {language}. Here is their code:",
        "<code>",
        code,
        "</code>",
        "",
        "Please evaluate this code submission based on the following criteria:",
        "",
        "1. **Code Cleanliness** (1-5) - Consider:",
        "   - Readability and code clarity",
        "   - Proper variable and function naming conventions",
        "   - Code organization and structure",
        "   - Adherence to good coding practices and style guidelines",
        "   - Appropriate use of comments (if needed for complex logic)",
        "   - Consistent formatting and indentation",
        "",
        "2. **Communication** (1-5) - This should be rated as 3 (placeholder) for now.",
        "   We will implement this based on voice/text interaction later.",
        "",
        "3. **Efficiency** (1-5) - Assess:",
        "   - Time complexity of the solution",
        "   - Space complexity and memory usage",
        "   - Whether the solution is optimized",
        "   - Use of appropriate algorithms and data structures",
        "   - Consideration of edge cases and performance",
        "",
        "**Rating Scale:**",
        "- 1: Poor - Major issues, does not meet basic standards",
        "- 2: Below Average - Significant room for improvement",
        "- 3: Average - Meets basic requirements but could be better",
        "- 4: Good - Well done with minor areas for improvement",
        "- 5: Excellent - Outstanding work, professional quality",
        "",
        "**Output Format:**",
        "Please provide your evaluation in the following format:",
        "",
        "<evaluation>",
        "**Code Cleanliness:**",
        "[Detailed feedback on code quality, naming conventions, structure, readability, etc.]",
        "Score: [1-5]",
        "",
        "**Communication:**",
        "[Placeholder - Rate as 3]",
        "Score: 3",
        "",
        "**Efficiency:**",
        "[Detailed feedback on algorithmic complexity, optimization, data structure choices, etc.]",
        "Score: [1-5]",
        "",
        "**Overall Comments:**",
        "[Summary of strengths, weaknesses, and specific suggestions for improvement]",
        "</evaluation>",
        "",
        "Be constructive, specific, and provide actionable feedback.",
    ]
    
    return "\n".join(part for part in parts if part is not None)