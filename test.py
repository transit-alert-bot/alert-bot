import re
def extract_prompt(input_string: str) -> str:
    pattern = r'(?i)\bgenerate\s*:\s*(.*)'  # Regex pattern to match variations of "generate:"
    match = re.search(pattern, input_string)
    if match:
        return match.group(1).strip()  # Return the matched text, stripping leading and trailing whitespace
    else:
        return "Substring not found in the input string."


def test_extract_prompt():
    # Test case 1: Regular case with "generate:"
    input_string_1 = "Please generate: a list of items"
    assert extract_prompt(input_string_1) == "a list of items"

    # Test case 2: Uppercase "GENERATE:" with extra whitespace
    input_string_2 = "   GENERATE:     This is a test prompt   "
    assert extract_prompt(input_string_2) == "This is a test prompt"

    # Test case 3: Mixed case and multiple whitespace variations
    input_string_3 = "Generate:  \t  \n\t  sample text  \t  \n"
    assert extract_prompt(input_string_3) == "sample text"

    # Test case 4: No prompt found
    input_string_4 = "No prompt here"
    assert extract_prompt(input_string_4) == "Substring not found in the input string."

    # Test case 5: Prompt at the beginning of the string
    input_string_5 = "Generate: Prompt at the beginning"
    assert extract_prompt(input_string_5) == "Prompt at the beginning"

    # Test case 6: Prompt at the end of the string
    input_string_6 = "Some text before the prompt. Generate: "
    assert extract_prompt(input_string_6) == ""

    print("All test cases passed successfully!")

# Run the test cases
test_extract_prompt()