"""Regex helper functions."""

import re

def get_tokens(s):
    """Find all tokens contained in square brackets in a string."""
    return re.findall(r'\[[^\]]+\]', s)

def get_text_between_tokens(s):
    """Split a string by tokens contained in square brackets."""
    tokens = re.findall(r'\[([^\]]+)\]', s)
    contents = re.split(r'\[[^\]]+\]', s)
    contents = [content.strip() for content in contents if content.strip() != '']
    return {tokens[i]: contents[i] if i < len(contents) else None for i in range(len(tokens))}

def parse_error_log(log):
    """Parse an error log file, find messages encapsulated in [MESSAGE] tags."""
    with open(log, 'rt') as f:
        content = f.read()

    pattern = r'\[MESSAGE\] (.*?)\n\t(.*?)\n'
    matches = re.findall(pattern, content, re.DOTALL)

    return [{'message': match[0], 'content': match[1]} for match in matches]

def capture_between_start_and_end(s):
    """Capture the content between [START] and [END] tags in a string."""
    match = re.search(r'\[START\](.*?)\[END\]', s, re.DOTALL)
    return match.group(1) if match else None

def get_yaml_blocks(file_content, language):
    """Find all yaml blocks in a string."""
    pattern = re.compile(r'```'+ re.escape(language) + '(.*?)```', re.DOTALL)
    matches = pattern.findall(file_content)
    return matches

def find_nth_bracketed_message(s, n: int):
    """Find the nth message encapsulated in square brackets in a string."""
    match = re.search(r'(\[[^\]]+\])', s)
    if match is None or len(match.groups()) < n:
        return None
    return match.group(n) if match else None

def trim_assistant(s: str) -> str:
    """Return that which comes after the <|assistant|> tag."""
    match = re.search(r'<\|assistant\|>(.*)', s, re.DOTALL)
    return match.group(1) if match else None

def get_type(s: str) -> str:
    """Returns that which is given after the type= tag."""
    match = re.search(r'type=(\w+)', s)
    return match.group(1) if match else None

def get_file_extension(s: str) -> str:
    """Return the file extension of a filename."""
    match = re.search(r'\.(\w+)$', s)
    return match.group(1) if match else None

def is_url(s: str) -> bool:
    """Check if a string is a URL. Loose check."""
    return re.search(r'https?://', s) is not None

def is_file(s: str) -> bool:
    """Check if a string is a file. Loose check."""
    return re.search(r'\.\w+$', s) is not None

def strip_url(s: str) -> str:
    """Remove the protocol from a URL."""
    return re.sub(r'https?://', '', s)

def strip_file(s: str) -> str:
    """Remove the file extension from a filename."""
    return re.sub(r'\.\w+$', '', s)

def replace_close_open(s: str) -> str:
    """Replace _close with _open in a string."""
    return re.sub(r'_close', '_open', s)

def remove_open(s: str) -> str:
    """Replace _open with nothing in a string."""
    return re.sub(r'_open', '', s)

def return_close_bool(s: str) -> bool:
    """Return whether a string contains _close."""
    return re.search(r'_close', s) is not None

def contains_v1_or_api(s: str) -> bool:
    """Check if a string contains /v1/ or /api/."""
    return bool(re.search(r'/v1/|/api/', s))

def have_same_base_url(url1, url2):
    """Check if two URLs have the same base URL."""
    base_url_regex = r'https?://[^/]*'
    base_url1 = re.match(base_url_regex, url1).group()
    base_url2 = re.match(base_url_regex, url2).group()
    return base_url1 == base_url2

def return_escapable_variables(s: str) -> list:
    """Return all variables that can be escaped in a string."""
    return re.findall(r'\{(.+?)\}', s)

def list_to_file_path(l: list) -> str:
    """Replace all slashes with underscores and join a list of strings with underscores: 
        --> so it can be saved as a file path
    """
    return re.sub(r'/', '_', '_'.join(l) + '.json')

def simple_tokenize_words(s: str) -> list:
    """Return the words in a string. Naive."""
    return re.findall(r'\w+', s)

def simple_tokenize_words_and_punctuation(s: str) -> list:
    """Return the words and punctuation in a string. Naive."""
    return re.findall(r'\b\w+\b', s)

def censor(v: str, c: str):
    """Censor a string by replacing all occurrences of a character with <hidden>."""
    c_escaped = re.escape(c)
    return re.sub(c_escaped, "<hidden>", v)

def remove_date_literal(s: str) -> str:
    """Remove the date- prefix from a string."""
    return re.sub(r'date-', '', s)
