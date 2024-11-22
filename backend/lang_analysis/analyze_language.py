from langdetect import detect_langs, language

def analyze_language(text: str) -> list[language.Language]:
    return detect_langs(text)