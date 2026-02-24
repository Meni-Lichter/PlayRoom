"""String utility functions for normalizing identifiers and canonicalizing headers"""
import pandas as pd

def normalize_identifier(value):
    """
    Normalize an identifier (like room number or 12NC) by:
    - Converting to string
    - Removing decimal points if present (e.g., 989606130501.0 -> 989606130501)
    - Removing spaces, hyphens, and underscores
    - Stripping leading and trailing whitespace
    input : 
        - value: The value to normalize (can be any type, will be converted to string)
    output:
        - string: The normalized string with non-alphanumeric characters removed.
    """
    if pd.isna(value):
        return ""
    
    # Convert to string first
    normalized = str(value).strip()
    
    # Remove decimal point and any trailing zeros from float representation
    # E.g., "989606130501.0" -> "989606130501"
    if '.' in normalized:
        normalized = normalized.split('.')[0]
    
    # Remove all non-alphanumeric characters (spaces, hyphens, underscores)
    normalized = normalized.replace(" ", "").replace("-", "").replace("_", "")
    
    return normalized


def canon_header(s: str) -> str:
    """
    Canonicalize a header for robust matching
    """
    if s is None:
        return ""
    s = s.casefold()
    s = s.strip(" ")
    s = s.strip("\n")
    s = s.strip("\t")
    s = s.strip("\r")
    s = s.replace("\n", " ").replace("\t", " ").replace("\r", " ")              
    return s



def is_blank(val, blank_tokens) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip()
    if s == "":
        return True
    return s.casefold() in {t.casefold() for t in blank_tokens}
