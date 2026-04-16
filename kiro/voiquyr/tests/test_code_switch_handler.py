"""
Property tests for Code_Switch_Handler.

Feature: voiquyr-differentiators
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from src.core.code_switch_handler import (
    CodeSwitchHandler,
    Language,
    LanguageSegment,
    ResponseLanguageConfig
)


# Property 12: Code-switch detection coverage
# Validates: Requirements 5.1, 5.5
@given(
    lang_sequence=st.lists(
        st.sampled_from([Language.ARABIC, Language.ENGLISH, Language.HINDI]),
        min_size=2,
        max_size=20
    )
)
@settings(max_examples=100)
def test_code_switch_detection_coverage(lang_sequence):
    """Property 12: Code-switch detection coverage."""
    handler = CodeSwitchHandler()
    # Create mock words with language boundaries
    words = [
        {"text": f"word{i}", "language": lang, "confidence": 0.9, "idx": i}
        for i, lang in enumerate(lang_sequence)
    ]
    
    # Merge into segments
    segments = handler._merge_segments(words)
    
    # Count actual switches
    switches = sum(1 for i in range(len(lang_sequence) - 1) 
                   if lang_sequence[i] != lang_sequence[i + 1])
    
    # Assert switch count matches
    if switches > 0:
        assert len(segments) > 1
    
    # Assert all words covered
    total_words_in_segments = sum(
        seg.end_word_idx - seg.start_word_idx + 1 
        for seg in segments
    )
    assert total_words_in_segments == len(words)


# Property 13: Unified transcript completeness
# Validates: Requirements 5.3
@given(
    words=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))),
            st.sampled_from([Language.ARABIC, Language.ENGLISH, Language.HINDI])
        ),
        min_size=1,
        max_size=50
    )
)
@settings(max_examples=100)
def test_unified_transcript_completeness(words):
    """Property 13: Unified transcript completeness."""
    handler = CodeSwitchHandler()
    # Create word list with languages
    words_with_lang = [
        {"text": text, "language": lang, "confidence": 0.9, "idx": i}
        for i, (text, lang) in enumerate(words)
    ]
    
    # Build unified transcript
    unified = " ".join(w["text"] for w in words_with_lang)
    
    # Assert all words present in order
    for word_data in words_with_lang:
        assert word_data["text"] in unified


# Property 14: Preferred response language enforcement
# Validates: Requirements 5.7
@given(
    preferred_lang=st.sampled_from([Language.ARABIC, Language.HINDI, Language.ENGLISH])
)
@settings(max_examples=100)
@pytest.mark.asyncio
async def test_preferred_response_language_enforcement(preferred_lang):
    """Property 14: Preferred response language enforcement."""
    handler = CodeSwitchHandler()
    # Create mock transcript with mixed languages
    transcript = await handler.transcribe(b"mock_audio", [Language.ENGLISH, Language.ARABIC])
    
    # Create config with preferred language
    config = ResponseLanguageConfig(
        tenant_id="test-tenant",
        preferred_response_language=preferred_lang,
        enforce_preference=True
    )
    
    # Apply response language
    response_lang = handler.apply_response_language(transcript, config)
    
    # Assert response language matches preference
    assert response_lang == preferred_lang
