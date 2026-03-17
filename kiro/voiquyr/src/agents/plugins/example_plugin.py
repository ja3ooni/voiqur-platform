"""
Example Plugin for EUVoice AI Platform
Demonstrates how to create plugins that extend the LLM agent's capabilities
"""

from typing import Dict, Any, List
try:
    from ..tool_integration import ToolRegistry, ToolParameter
except ImportError:
    # For direct testing
    from tool_integration import ToolRegistry, ToolParameter


# Plugin metadata
__version__ = "1.0.0"
__description__ = "Example plugin demonstrating tool extension capabilities"
__author__ = "EUVoice AI Team"


def register_tools(tool_registry: ToolRegistry) -> bool:
    """Register plugin tools with the tool registry"""
    try:
        # Register a simple calculation tool
        success1 = tool_registry.register_function(
            name="calculate_percentage",
            description="Calculate percentage of a value",
            function=calculate_percentage,
            parameters=[
                ToolParameter(
                    name="value",
                    type="number",
                    description="The value to calculate percentage of",
                    required=True
                ),
                ToolParameter(
                    name="percentage",
                    type="number",
                    description="The percentage to calculate",
                    required=True
                )
            ]
        )
        
        # Register a text processing tool
        success2 = tool_registry.register_function(
            name="count_words",
            description="Count words in a text",
            function=count_words,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to count words in",
                    required=True
                ),
                ToolParameter(
                    name="include_punctuation",
                    type="boolean",
                    description="Whether to include punctuation in word count",
                    required=False,
                    default=False
                )
            ]
        )
        
        # Register a language utility tool
        success3 = tool_registry.register_function(
            name="detect_language_simple",
            description="Simple language detection based on common words",
            function=detect_language_simple,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to analyze for language",
                    required=True
                )
            ]
        )
        
        return success1 and success2 and success3
        
    except Exception as e:
        print(f"Plugin registration failed: {e}")
        return False


def unregister_tools(tool_registry: ToolRegistry) -> bool:
    """Unregister plugin tools from the tool registry"""
    try:
        success1 = tool_registry.unregister_tool("calculate_percentage")
        success2 = tool_registry.unregister_tool("count_words")
        success3 = tool_registry.unregister_tool("detect_language_simple")
        
        return success1 and success2 and success3
        
    except Exception as e:
        print(f"Plugin unregistration failed: {e}")
        return False


# Tool implementations
def calculate_percentage(value: float, percentage: float) -> Dict[str, Any]:
    """Calculate percentage of a value"""
    result = (value * percentage) / 100
    return {
        "original_value": value,
        "percentage": percentage,
        "result": result,
        "formatted": f"{percentage}% of {value} is {result}"
    }


def count_words(text: str, include_punctuation: bool = False) -> Dict[str, Any]:
    """Count words in text"""
    import re
    
    if include_punctuation:
        words = text.split()
    else:
        # Remove punctuation and split
        clean_text = re.sub(r'[^\w\s]', '', text)
        words = clean_text.split()
    
    word_count = len(words)
    char_count = len(text)
    char_count_no_spaces = len(text.replace(' ', ''))
    
    return {
        "text": text,
        "word_count": word_count,
        "character_count": char_count,
        "character_count_no_spaces": char_count_no_spaces,
        "average_word_length": char_count_no_spaces / word_count if word_count > 0 else 0
    }


def detect_language_simple(text: str) -> Dict[str, Any]:
    """Simple language detection based on common words"""
    text_lower = text.lower()
    
    # Simple language indicators
    language_indicators = {
        "english": ["the", "and", "is", "in", "to", "of", "a", "that", "it", "with"],
        "french": ["le", "de", "et", "à", "un", "il", "être", "et", "en", "avoir"],
        "german": ["der", "die", "und", "in", "den", "von", "zu", "das", "mit", "sich"],
        "spanish": ["el", "de", "que", "y", "a", "en", "un", "es", "se", "no"],
        "italian": ["il", "di", "che", "e", "la", "per", "in", "un", "è", "con"],
        "portuguese": ["o", "de", "que", "e", "do", "da", "em", "um", "para", "é"],
        "dutch": ["de", "van", "het", "een", "in", "te", "dat", "op", "voor", "met"],
        "arabic": ["في", "من", "إلى", "على", "هذا", "هذه", "التي", "الذي", "كان", "أن"]
    }
    
    scores = {}
    words = text_lower.split()
    
    for language, indicators in language_indicators.items():
        score = sum(1 for word in words if word in indicators)
        if len(words) > 0:
            scores[language] = score / len(words)
        else:
            scores[language] = 0
    
    # Find the language with highest score
    detected_language = max(scores, key=scores.get) if scores else "unknown"
    confidence = scores.get(detected_language, 0)
    
    return {
        "text": text,
        "detected_language": detected_language,
        "confidence": confidence,
        "all_scores": scores,
        "method": "simple_word_matching"
    }


# Plugin configuration
PLUGIN_CONFIG = {
    "name": "example_plugin",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "tools": [
        "calculate_percentage",
        "count_words", 
        "detect_language_simple"
    ],
    "dependencies": [],
    "settings": {
        "enable_advanced_features": False,
        "cache_results": True
    }
}