# Code Quality Evaluation Implementation

## Overview
This implementation enables Claude AI to evaluate candidate code submissions based on well-defined criteria. The system now captures code from the Monaco editor, sends it to Claude with question context, and returns detailed feedback with ratings.

## Key Features

### 1. **Intelligent Code Evaluation**
- Claude analyzes actual code written by candidates
- Ratings based on Code Cleanliness, Communication, and Efficiency
- Context-aware evaluation using the interview question details

### 2. **Rating Criteria**

#### Code Cleanliness (1-5)
- Readability and code clarity
- Proper variable and function naming conventions
- Code organization and structure
- Adherence to good coding practices
- Consistent formatting and indentation

#### Communication (1-5)
- Currently set to placeholder value of 3
- Reserved for future voice/text interaction analysis

#### Efficiency (1-5)
- Time complexity analysis
- Space complexity and memory usage
- Algorithm and data structure choices
- Edge case handling
- Optimization considerations

### 3. **Rating Scale**
- 1: Poor - Major issues, does not meet basic standards
- 2: Below Average - Significant room for improvement
- 3: Average - Meets basic requirements but could be better
- 4: Good - Well done with minor areas for improvement
- 5: Excellent - Outstanding work, professional quality

## Implementation Details

### Backend Changes

#### 1. `mockly-backend/app/services/workflow/prompts.py`
- Added `build_code_evaluation_prompt()` function
- Creates comprehensive prompt with code, language, and question context
- Defines clear evaluation criteria and output format

#### 2. `mockly-backend/app/routes/routes_feedback.py`
- Changed from GET to POST endpoint
- Accepts payload with `code`, `language`, and optional `question` context
- Automatically loads full question details when only difficulty is provided
- Calls Claude AI for code evaluation
- Parses response to extract scores and formatted feedback
- Returns structured `FeedbackReport` with ratings and comments

### Frontend Changes

#### 1. `mockly-frontend/src/services/api.ts`
- Updated `fetchFeedback()` to accept payload parameter
- Changed from GET to POST request
- Sends code, language, and question context to backend

#### 2. `mockly-frontend/src/App.tsx`
- Extracts code from Monaco editor via session store
- Prepares question context including prompt and difficulty
- Sends complete payload when interview ends
- Maintains existing feedback display flow

## Data Flow

```
1. User writes code in Monaco Editor → Stored in session state
2. User clicks "End Interview" → App.tsx collects code + context
3. Frontend API sends POST /api/feedback with:
   - code: actual code from editor
   - language: selected programming language
   - question: { prompt, difficulty }
4. Backend:
   - Loads full question details if needed
   - Builds evaluation prompt with code
   - Calls Claude AI for analysis
   - Parses scores from response
   - Returns formatted feedback
5. Frontend displays ratings and comments in FeedbackView
```

## Testing

### Manual Test
Run the test script to verify the implementation:

```bash
# Make sure backend is running on port 8000
python test_code_evaluation.py
```

### Expected Output
The test will submit sample Python code (two-sum solution) and receive:
- Code Cleanliness score (1-5)
- Communication score (placeholder: 3)
- Efficiency score (1-5)
- Detailed feedback comments from Claude

## Future Enhancements

1. **Communication Rating**: Integrate with voice/text interaction logs to evaluate how well candidates explain their thought process
2. **Correctness Score**: Add automated test case validation
3. **Historical Tracking**: Store evaluations for progress tracking
4. **Custom Rubrics**: Allow customizable evaluation criteria per question type
5. **Multi-language Support**: Language-specific best practices evaluation

## Configuration

### Required Environment Variables
- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude access
- `ANTHROPIC_MODEL`: Model to use (default: claude-sonnet-4-20250514)

### Dependencies
- Backend: `anthropic` SDK (already in requirements)
- Frontend: Monaco Editor (already integrated via `@monaco-editor/react`)

## Error Handling

The implementation includes robust error handling:
- Returns 400 if code is missing
- Returns 500 with error details if Claude API fails
- Falls back to default scores (3) if parsing fails
- Graceful degradation if question details unavailable

## Comment Formatting

The feedback comments are automatically formatted with markdown for optimal readability:

### Formatting Features
- **Markdown rendering**: Comments are formatted with markdown (headings, bold, code blocks)
- **Category sections**: Each evaluation category is clearly labeled with ### headings
- **Score lines removed**: Scores are only shown in the rating cards, not in text
- **Placeholder filtering**: Communication section is hidden when it's just a placeholder
- **Clean separation**: Double line breaks between sections for readability
- **Styled rendering**: Headings, code snippets, and emphasis are styled for clarity

### Example Output Format
```markdown
### Code Cleanliness
The code demonstrates good readability with **clear variable names** like `num_map` and `complement`...

### Efficiency
Excellent algorithmic approach using a hash map for **O(n) time complexity**...

### Overall Comments
This is a well-implemented solution. Consider adding a docstring for better documentation.
```

The markdown is rendered in the UI with:
- **Headings** styled as larger, bold section titles
- `Code snippets` with monospace font and background highlighting
- **Bold text** for emphasis on key points
- Proper spacing between paragraphs and sections

## Notes

- Communication score is intentionally set to 3 (placeholder) until voice/text interaction analysis is implemented
- Communication feedback is automatically excluded from display when it's just a placeholder
- The evaluation is language-agnostic - Claude adapts feedback based on the specified programming language
- Question context is optional but recommended for more accurate evaluation
- Response formatting preserves markdown for rich text display while removing score lines
- Each category's feedback is extracted and formatted separately with markdown headings
- The frontend uses a markdown renderer to display formatted, readable feedback

## Files Modified

**Backend:**
- `mockly-backend/app/services/workflow/prompts.py` - Added evaluation prompt
- `mockly-backend/app/routes/routes_feedback.py` - Implemented evaluation endpoint

**Frontend:**
- `mockly-frontend/src/services/api.ts` - Updated API call
- `mockly-frontend/src/App.tsx` - Added code submission logic

**Testing:**
- `test_code_evaluation.py` - Test script for verification

