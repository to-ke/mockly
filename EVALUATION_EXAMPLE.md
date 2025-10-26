# Code Evaluation Example

## Sample Input

### Code Submitted
```python
def two_sum(nums, target):
    # Create a hash map to store numbers and their indices
    num_map = {}
    
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    
    return []
```

### Question Context
- **Difficulty**: Easy
- **Problem**: Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

### Language
Python

---

## Sample Output (Formatted Plain Text)

### Scores Displayed
- Code Cleanliness: ⭐⭐⭐⭐⭐ (5/5)
- Communication: ⭐⭐⭐ (3/5)
- Code Efficiency: ⭐⭐⭐⭐⭐ (5/5)

### Interviewer Comments (Markdown Format)

The feedback is rendered with markdown formatting in the UI:

```markdown
### Code Cleanliness
The code demonstrates good readability with **clear variable names** like `num_map` and `complement`. The function name `two_sum` is descriptive and follows Python naming conventions. The comment at the top helps explain the approach, though the logic is self-explanatory. The code structure is clean with **consistent indentation** and proper use of Python idioms like `enumerate()`.

### Efficiency
Excellent algorithmic approach using a hash map for **O(n) time complexity** instead of the naive O(n²) nested loop solution. The space complexity is **O(n)** which is optimal for this problem. The single-pass algorithm is efficient and handles the problem constraints well. Good understanding of when to trade space for time complexity.

### Overall Comments
This is a well-implemented solution to the two-sum problem. The use of a hash map demonstrates **strong understanding of data structures** and their applications. The code is production-ready with good naming conventions and clarity. One minor suggestion would be to add a docstring explaining the function parameters and return value for better documentation.
```

**How it renders:**
- Category headings (###) appear larger and bold
- **Bold text** emphasizes key points
- `Code terms` have monospace font with highlighting
- Clean spacing between sections

**Note**: Communication feedback is excluded when it's just a placeholder value.

---

## Another Example - Less Optimal Code

### Code Submitted
```python
def twoSum(n, t):
    for x in range(len(n)):
        for y in range(x+1, len(n)):
            if n[x] + n[y] == t:
                return [x, y]
```

### Expected Evaluation (Formatted Plain Text)

#### Scores Displayed
- Code Cleanliness: ⭐⭐ (2/5)
- Communication: ⭐⭐⭐ (3/5)
- Code Efficiency: ⭐⭐ (2/5)

#### Interviewer Comments

```markdown
### Code Cleanliness
The code has **several issues with naming conventions**. Variable names like `n`, `t`, `x`, and `y` are not descriptive and make the code harder to understand. The function name uses camelCase instead of snake_case which is the Python convention. There are **no comments** explaining the approach. While the logic is correct, the code readability suffers significantly from poor naming choices.

### Efficiency
The solution uses a **nested loop approach** resulting in **O(n²) time complexity**. This is a brute-force solution that works but is inefficient for larger inputs. There's no consideration of optimization techniques like using a hash map which could reduce this to **O(n)**. Space complexity is O(1) which is good, but the time complexity trade-off makes this solution suboptimal for production use.

### Overall Comments
The solution is functionally correct and will produce the right answer, but it has **significant room for improvement**. Focus on using descriptive variable names that convey meaning (e.g., `nums` instead of `n`, `target` instead of `t`, `i` and `j` or `first_index` and `second_index` instead of `x` and `y`). Follow Python naming conventions with snake_case. Most importantly, consider using a hash map to achieve O(n) time complexity instead of the nested loop approach. This would demonstrate better understanding of algorithmic optimization and data structure selection.
```

---

## Rating Distribution Examples

### Excellent Solution (4-5 range)
- Clean, readable code with proper naming
- Optimal time/space complexity
- Handles edge cases
- Good comments where needed
- **Result**: Cleanliness: 5, Efficiency: 5

### Good Solution (3-4 range)
- Mostly readable with minor naming issues
- Good but not optimal algorithm choice
- Basic edge case handling
- **Result**: Cleanliness: 4, Efficiency: 3

### Average Solution (2-3 range)
- Acceptable but hard to read
- Brute force approach
- Missing some edge cases
- **Result**: Cleanliness: 3, Efficiency: 2

### Poor Solution (1-2 range)
- Very hard to read/understand
- Inefficient approach
- No consideration of edge cases
- **Result**: Cleanliness: 2, Efficiency: 1

