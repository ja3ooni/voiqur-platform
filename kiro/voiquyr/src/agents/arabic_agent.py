"""
Arabic Language Specialist Agent - Comprehensive Arabic language processing
Implements MSA and dialect support with diacritization and cultural context adaptation
"""

import asyncio
import logging
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from datetime import datetime
import uuid
import re

from ..core.models import AgentMessage, AgentState, Task, AgentCapability, Priority
from ..core.messaging import MessageBus


class ArabicDialect(Enum):
    """Major Arabic dialects and variants"""
    MSA = "msa"  # Modern Standard Arabic
    EGYPTIAN = "egyptian"  # Egyptian Arabic
    LEVANTINE = "levantine"  # Levantine Arabic (Syria, Lebanon, Jordan, Palestine)
    GULF = "gulf"  # Gulf Arabic (UAE, Saudi, Kuwait, Qatar, Bahrain, Oman)
    MAGHREBI = "maghrebi"  # Maghrebi Arabic (Morocco, Algeria, Tunisia, Libya)
    IRAQI = "iraqi"  # Iraqi Arabic
    SUDANESE = "sudanese"  # Sudanese Arabic
    YEMENI = "yemeni"  # Yemeni Arabic
    UNKNOWN = "unknown"


class CulturalContext(Enum):
    """Arabic cultural contexts"""
    FORMAL_RELIGIOUS = "formal_religious"
    FORMAL_ACADEMIC = "formal_academic"
    FORMAL_BUSINESS = "formal_business"
    INFORMAL_FAMILY = "informal_family"
    INFORMAL_FRIENDS = "informal_friends"
    MEDIA_NEWS = "media_news"
    MEDIA_ENTERTAINMENT = "media_entertainment"
    LITERARY = "literary"
    COLLOQUIAL = "colloquial"


class FormalityLevel(Enum):
    """Arabic formality levels"""
    VERY_FORMAL = "very_formal"  # Classical/Quranic Arabic
    FORMAL = "formal"  # MSA, official documents
    SEMI_FORMAL = "semi_formal"  # Educated speech
    INFORMAL = "informal"  # Casual conversation
    VERY_INFORMAL = "very_informal"  # Slang, intimate


@dataclass
class ArabicTextAnalysis:
    """Analysis result for Arabic text"""
    original_text: str
    normalized_text: str
    diacritized_text: str
    dialect: ArabicDialect
    dialect_confidence: float
    cultural_context: CulturalContext
    formality_level: FormalityLevel
    code_switching_detected: bool
    mixed_languages: List[str] = field(default_factory=list)
    dialect_markers: List[str] = field(default_factory=list)
    cultural_markers: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiacritizationResult:
    """Result of Arabic diacritization"""
    original_text: str
    diacritized_text: str
    confidence_scores: List[float]
    alternative_diacritizations: List[str] = field(default_factory=list)
    processing_time: float = 0.0


@dataclass
class CodeSwitchingAnalysis:
    """Analysis of code-switching in Arabic text"""
    segments: List[Dict[str, Any]]  # Each segment has language, text, confidence
    switch_points: List[int]  # Character positions where language switches
    dominant_language: str
    languages_detected: List[str]
    switching_frequency: float  # Switches per 100 words
    confidence: float


class ArabicTextProcessor:
    """Core Arabic text processing functionality"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Arabic script ranges and patterns
        self.arabic_range = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        self.arabic_letters = r'[\u0627-\u064A\u0671-\u06D3\u06F0-\u06F9]'
        self.diacritics = r'[\u064B-\u0652\u0670\u0640]'
        
        # Dialect-specific patterns and vocabulary
        self.dialect_patterns = self._initialize_dialect_patterns()
        self.cultural_markers = self._initialize_cultural_markers()
        self.formality_indicators = self._initialize_formality_indicators()
    
    def _initialize_dialect_patterns(self) -> Dict[ArabicDialect, Dict[str, Any]]:
        """Initialize dialect-specific patterns and vocabulary"""
        patterns = {}
        
        # Egyptian Arabic
        patterns[ArabicDialect.EGYPTIAN] = {
            "markers": [
                "إيه", "ايه", "كده", "كدة", "علشان", "عشان", "إزيك", "ازيك",
                "يلا", "يالا", "معلش", "ماعلش", "خلاص", "كمان", "برضه", "برضو"
            ],
            "phonetic_patterns": [
                r"ج.*ج",  # Egyptian 'g' sound
                r"ق.*أ",   # Qaf as glottal stop
            ],
            "grammatical_features": [
                "بي" + r"[\u0627-\u064A]+",  # Present tense marker 'bi-'
                "ح" + r"[\u0627-\u064A]+",   # Future marker 'ha-'
            ]
        }
        
        # Levantine Arabic
        patterns[ArabicDialect.LEVANTINE] = {
            "markers": [
                "شو", "ايش", "وين", "كيف", "هيك", "هيدا", "هاي", "منيح",
                "يعني", "بدي", "بده", "بدها", "عم", "رح", "راح"
            ],
            "phonetic_patterns": [
                r"ق.*ء",   # Qaf as glottal stop
                r"ك.*ش",   # Kaf-shin combination
            ],
            "grammatical_features": [
                "عم" + r"[\u0627-\u064A]+",  # Progressive marker 'am'
                "رح" + r"[\u0627-\u064A]+",  # Future marker 'rah'
            ]
        }
        
        # Gulf Arabic
        patterns[ArabicDialect.GULF] = {
            "markers": [
                "شلون", "وش", "ويش", "شنو", "شنهو", "يبا", "يبه", "ماكو",
                "اكو", "هسه", "هسة", "زين", "مب", "مو", "ما", "چان", "گال"
            ],
            "phonetic_patterns": [
                r"چ",      # Persian 'ch' sound
                r"گ",      # Persian 'g' sound
                r"ژ",      # Persian 'zh' sound
            ],
            "grammatical_features": [
                "دا" + r"[\u0627-\u064A]+",  # Progressive marker 'da'
                "ب" + r"[\u0627-\u064A]+",   # Future marker 'b'
            ]
        }
        
        # Maghrebi Arabic
        patterns[ArabicDialect.MAGHREBI] = {
            "markers": [
                "آش", "اش", "فين", "كيفاش", "واش", "وقتاش", "علاش", "بزاف",
                "شوية", "شويا", "بصح", "والاكن", "نتا", "نتي", "هوا", "هيا"
            ],
            "phonetic_patterns": [
                r"ڤ",      # Maghrebi 'v' sound
                r"پ",      # Maghrebi 'p' sound
            ],
            "grammatical_features": [
                "كا" + r"[\u0627-\u064A]+",  # Progressive marker 'ka'
                "غا" + r"[\u0627-\u064A]+",  # Future marker 'gha'
            ]
        }
        
        # MSA (Modern Standard Arabic)
        patterns[ArabicDialect.MSA] = {
            "markers": [
                "إن", "أن", "كان", "كانت", "يكون", "تكون", "سوف", "قد",
                "لقد", "إذا", "إذ", "حيث", "بينما", "لكن", "غير", "سوى"
            ],
            "phonetic_patterns": [
                r"ق.*ق",   # Classical qaf pronunciation
                r"ث.*ث",   # Theta sound preservation
                r"ذ.*ذ",   # Dhal sound preservation
            ],
            "grammatical_features": [
                "سوف" + r"[\u0627-\u064A]+",  # Future marker 'sawfa'
                "قد" + r"[\u0627-\u064A]+",   # Perfect marker 'qad'
                r"[\u0627-\u064A]+ة",        # Feminine marker
            ]
        }
        
        return patterns
    
    def _initialize_cultural_markers(self) -> Dict[CulturalContext, List[str]]:
        """Initialize cultural context markers"""
        markers = {}
        
        markers[CulturalContext.FORMAL_RELIGIOUS] = [
            "بسم الله", "الحمد لله", "إن شاء الله", "ما شاء الله", "سبحان الله",
            "استغفر الله", "لا حول ولا قوة إلا بالله", "صلى الله عليه وسلم",
            "رضي الله عنه", "رحمه الله", "جزاك الله خيرا", "بارك الله فيك"
        ]
        
        markers[CulturalContext.FORMAL_ACADEMIC] = [
            "بحث", "دراسة", "تحليل", "نظرية", "منهجية", "استنتاج", "فرضية",
            "مراجع", "مصادر", "ببليوغرافيا", "أطروحة", "رسالة", "مؤتمر"
        ]
        
        markers[CulturalContext.FORMAL_BUSINESS] = [
            "شركة", "مؤسسة", "إدارة", "قسم", "موظف", "عميل", "زبون", "عقد",
            "اتفاقية", "صفقة", "استثمار", "ربح", "خسارة", "ميزانية", "تقرير"
        ]
        
        markers[CulturalContext.INFORMAL_FAMILY] = [
            "أبي", "أمي", "أخي", "أختي", "جدي", "جدتي", "عمي", "عمتي",
            "خالي", "خالتي", "ابن عمي", "بنت عمي", "حبيبي", "حبيبتي", "يا روحي"
        ]
        
        markers[CulturalContext.MEDIA_NEWS] = [
            "أخبار", "تقرير", "مراسل", "صحفي", "نشرة", "عاجل", "خبر عاجل",
            "مصدر", "تصريح", "بيان", "مؤتمر صحفي", "تغطية", "حدث"
        ]
        
        return markers
    
    def _initialize_formality_indicators(self) -> Dict[FormalityLevel, List[str]]:
        """Initialize formality level indicators"""
        indicators = {}
        
        indicators[FormalityLevel.VERY_FORMAL] = [
            "إن", "أن", "كان", "ليس", "ليست", "سوف", "قد", "لقد",
            "حيث", "إذ", "بينما", "غير أن", "إلا أن", "مع ذلك"
        ]
        
        indicators[FormalityLevel.FORMAL] = [
            "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "اللذان", "اللتان",
            "يجب", "ينبغي", "يمكن", "يستطيع", "نستطيع", "نحن"
        ]
        
        indicators[FormalityLevel.INFORMAL] = [
            "ده", "دي", "دول", "كده", "كدة", "إيه", "ايه", "ليه", "ليش",
            "شو", "ايش", "وين", "كيف", "منين", "امتى"
        ]
        
        indicators[FormalityLevel.VERY_INFORMAL] = [
            "يلا", "يالا", "خلاص", "معلش", "ماعلش", "برضه", "برضو",
            "كمان", "تاني", "كتير", "شوي", "شوية"
        ]
        
        return indicators
    
    async def analyze_arabic_text(self, text: str) -> ArabicTextAnalysis:
        """Comprehensive analysis of Arabic text"""
        try:
            start_time = time.time()
            
            # Normalize text
            normalized_text = self._normalize_arabic_text(text)
            
            # Detect dialect
            dialect, dialect_confidence, dialect_markers = await self._detect_dialect(normalized_text)
            
            # Analyze cultural context
            cultural_context, cultural_markers = self._analyze_cultural_context(normalized_text)
            
            # Determine formality level
            formality_level = self._determine_formality_level(normalized_text)
            
            # Detect code-switching
            code_switching_analysis = await self._detect_code_switching(normalized_text)
            
            # Diacritize text
            diacritized_text = await self._diacritize_text(normalized_text, dialect)
            
            processing_time = time.time() - start_time
            
            return ArabicTextAnalysis(
                original_text=text,
                normalized_text=normalized_text,
                diacritized_text=diacritized_text,
                dialect=dialect,
                dialect_confidence=dialect_confidence,
                cultural_context=cultural_context,
                formality_level=formality_level,
                code_switching_detected=code_switching_analysis.switching_frequency > 0,
                mixed_languages=code_switching_analysis.languages_detected,
                dialect_markers=dialect_markers,
                cultural_markers=cultural_markers,
                processing_time=processing_time,
                metadata={
                    "text_length": len(text),
                    "normalized_length": len(normalized_text),
                    "arabic_ratio": self._calculate_arabic_ratio(text),
                    "code_switching_frequency": code_switching_analysis.switching_frequency
                }
            )
            
        except Exception as e:
            self.logger.error(f"Arabic text analysis failed: {e}")
            return ArabicTextAnalysis(
                original_text=text,
                normalized_text=text,
                diacritized_text=text,
                dialect=ArabicDialect.UNKNOWN,
                dialect_confidence=0.0,
                cultural_context=CulturalContext.COLLOQUIAL,
                formality_level=FormalityLevel.INFORMAL,
                code_switching_detected=False,
                processing_time=0.0,
                metadata={"error": str(e)}
            )
    
    def _normalize_arabic_text(self, text: str) -> str:
        """Normalize Arabic text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize Arabic letters
        # Alef variations
        text = re.sub(r'[إأآا]', 'ا', text)
        # Yeh variations
        text = re.sub(r'[يى]', 'ي', text)
        # Teh marbuta
        text = re.sub(r'ة', 'ه', text)
        # Remove tatweel (kashida)
        text = re.sub(r'ـ', '', text)
        
        # Normalize punctuation
        text = re.sub(r'[،؍؎؏ؘؙؚؐؑؒؓؔؕؖؗ؛؞؟]', '،', text)
        
        return text
    
    async def _detect_dialect(self, text: str) -> Tuple[ArabicDialect, float, List[str]]:
        """Detect Arabic dialect from text"""
        try:
            dialect_scores = {dialect: 0.0 for dialect in ArabicDialect}
            found_markers = []
            
            words = text.split()
            total_words = len(words)
            
            if total_words == 0:
                return ArabicDialect.UNKNOWN, 0.0, []
            
            # Check for dialect-specific markers
            for dialect, patterns in self.dialect_patterns.items():
                dialect_score = 0.0
                dialect_markers = []
                
                # Check vocabulary markers
                for marker in patterns["markers"]:
                    if marker in text:
                        dialect_score += 2.0
                        dialect_markers.append(marker)
                
                # Check phonetic patterns
                for pattern in patterns["phonetic_patterns"]:
                    matches = re.findall(pattern, text)
                    dialect_score += len(matches) * 1.5
                
                # Check grammatical features
                for feature in patterns["grammatical_features"]:
                    matches = re.findall(feature, text)
                    dialect_score += len(matches) * 1.0
                
                # Normalize by text length
                dialect_scores[dialect] = dialect_score / max(1, total_words)
                
                if dialect_markers:
                    found_markers.extend(dialect_markers)
            
            # Find best matching dialect
            best_dialect = max(dialect_scores, key=dialect_scores.get)
            confidence = dialect_scores[best_dialect]
            
            # If no strong dialect indicators, default to MSA
            if confidence < 0.1:
                best_dialect = ArabicDialect.MSA
                confidence = 0.5
            
            # Normalize confidence to 0-1 range
            confidence = min(1.0, confidence)
            
            return best_dialect, confidence, found_markers[:5]  # Return top 5 markers
            
        except Exception as e:
            self.logger.error(f"Dialect detection failed: {e}")
            return ArabicDialect.UNKNOWN, 0.0, []
    
    def _analyze_cultural_context(self, text: str) -> Tuple[CulturalContext, List[str]]:
        """Analyze cultural context of Arabic text"""
        try:
            context_scores = {context: 0.0 for context in CulturalContext}
            found_markers = []
            
            # Check for cultural markers
            for context, markers in self.cultural_markers.items():
                score = 0.0
                context_markers = []
                
                for marker in markers:
                    if marker in text:
                        score += 1.0
                        context_markers.append(marker)
                
                context_scores[context] = score
                if context_markers:
                    found_markers.extend(context_markers)
            
            # Find best matching context
            best_context = max(context_scores, key=context_scores.get)
            
            # If no strong indicators, use colloquial as default
            if context_scores[best_context] == 0:
                best_context = CulturalContext.COLLOQUIAL
            
            return best_context, found_markers[:3]  # Return top 3 markers
            
        except Exception as e:
            self.logger.error(f"Cultural context analysis failed: {e}")
            return CulturalContext.COLLOQUIAL, []
    
    def _determine_formality_level(self, text: str) -> FormalityLevel:
        """Determine formality level of Arabic text"""
        try:
            formality_scores = {level: 0.0 for level in FormalityLevel}
            
            # Check for formality indicators
            for level, indicators in self.formality_indicators.items():
                score = 0.0
                
                for indicator in indicators:
                    if indicator in text:
                        score += 1.0
                
                formality_scores[level] = score
            
            # Find best matching formality level
            best_level = max(formality_scores, key=formality_scores.get)
            
            # If no strong indicators, use informal as default
            if formality_scores[best_level] == 0:
                best_level = FormalityLevel.INFORMAL
            
            return best_level
            
        except Exception as e:
            self.logger.error(f"Formality level determination failed: {e}")
            return FormalityLevel.INFORMAL
    
    async def _detect_code_switching(self, text: str) -> CodeSwitchingAnalysis:
        """Detect code-switching between Arabic and other languages"""
        try:
            segments = []
            switch_points = []
            languages_detected = ["ar"]  # Arabic is always present
            
            # Simple language detection based on script
            words = text.split()
            current_language = "ar"
            current_segment = []
            
            for i, word in enumerate(words):
                # Check if word contains Arabic script
                if re.search(self.arabic_range, word):
                    word_language = "ar"
                # Check for Latin script (English/French)
                elif re.search(r'[a-zA-Z]', word):
                    word_language = "en"  # Simplified - could be other Latin languages
                # Check for numbers
                elif re.search(r'[0-9]', word):
                    word_language = current_language  # Numbers inherit current language
                else:
                    word_language = current_language  # Unknown, inherit current
                
                if word_language != current_language:
                    # Language switch detected
                    if current_segment:
                        segments.append({
                            "language": current_language,
                            "text": " ".join(current_segment),
                            "confidence": 0.9,
                            "start_word": i - len(current_segment),
                            "end_word": i - 1
                        })
                    
                    switch_points.append(i)
                    current_language = word_language
                    current_segment = [word]
                    
                    if word_language not in languages_detected:
                        languages_detected.append(word_language)
                else:
                    current_segment.append(word)
            
            # Add final segment
            if current_segment:
                segments.append({
                    "language": current_language,
                    "text": " ".join(current_segment),
                    "confidence": 0.9,
                    "start_word": len(words) - len(current_segment),
                    "end_word": len(words) - 1
                })
            
            # Calculate switching frequency
            switching_frequency = (len(switch_points) / max(1, len(words))) * 100
            
            # Determine dominant language
            language_word_counts = {}
            for segment in segments:
                lang = segment["language"]
                word_count = len(segment["text"].split())
                language_word_counts[lang] = language_word_counts.get(lang, 0) + word_count
            
            dominant_language = max(language_word_counts, key=language_word_counts.get) if language_word_counts else "ar"
            
            return CodeSwitchingAnalysis(
                segments=segments,
                switch_points=switch_points,
                dominant_language=dominant_language,
                languages_detected=languages_detected,
                switching_frequency=switching_frequency,
                confidence=0.8  # Simplified confidence
            )
            
        except Exception as e:
            self.logger.error(f"Code-switching detection failed: {e}")
            return CodeSwitchingAnalysis(
                segments=[{"language": "ar", "text": text, "confidence": 0.5}],
                switch_points=[],
                dominant_language="ar",
                languages_detected=["ar"],
                switching_frequency=0.0,
                confidence=0.5
            )
    
    async def _diacritize_text(self, text: str, dialect: ArabicDialect) -> str:
        """Add diacritics to Arabic text based on dialect"""
        try:
            # Simplified diacritization - in practice, this would use trained models
            diacritized = text
            
            # Basic diacritization rules based on common patterns
            if dialect == ArabicDialect.MSA:
                # MSA diacritization rules
                diacritized = self._apply_msa_diacritization(diacritized)
            elif dialect in [ArabicDialect.EGYPTIAN, ArabicDialect.LEVANTINE]:
                # Dialectal diacritization (less formal)
                diacritized = self._apply_dialectal_diacritization(diacritized)
            
            return diacritized
            
        except Exception as e:
            self.logger.error(f"Diacritization failed: {e}")
            return text
    
    def _apply_msa_diacritization(self, text: str) -> str:
        """Apply MSA-specific diacritization rules"""
        # Simplified rules - real implementation would use comprehensive models
        
        # Common word patterns
        patterns = [
            (r'\bالله\b', 'اللَّه'),  # Allah
            (r'\bمن\b', 'مِن'),      # min (from)
            (r'\bإلى\b', 'إِلَى'),   # ila (to)
            (r'\bفي\b', 'فِي'),      # fi (in)
            (r'\bعلى\b', 'عَلَى'),   # ala (on)
            (r'\bهذا\b', 'هَذَا'),   # hatha (this)
            (r'\bهذه\b', 'هَذِه'),   # hathihi (this fem)
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _apply_dialectal_diacritization(self, text: str) -> str:
        """Apply dialectal diacritization rules"""
        # Simplified dialectal rules
        
        patterns = [
            (r'\bده\b', 'دَه'),      # da (this - Egyptian)
            (r'\bدي\b', 'دِي'),      # di (this fem - Egyptian)
            (r'\bكده\b', 'كِدَه'),   # kida (like this - Egyptian)
            (r'\bشو\b', 'شُو'),      # shu (what - Levantine)
            (r'\bوين\b', 'وِين'),    # ween (where - Levantine)
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _calculate_arabic_ratio(self, text: str) -> float:
        """Calculate the ratio of Arabic characters in text"""
        if not text:
            return 0.0
        
        arabic_chars = len(re.findall(self.arabic_range, text))
        total_chars = len(re.sub(r'\s', '', text))  # Exclude whitespace
        
        return arabic_chars / max(1, total_chars)


class ArabicSpeechProcessor:
    """Arabic speech processing and synthesis adaptation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Dialect-specific phonetic mappings
        self.phonetic_mappings = self._initialize_phonetic_mappings()
    
    def _initialize_phonetic_mappings(self) -> Dict[ArabicDialect, Dict[str, str]]:
        """Initialize dialect-specific phonetic mappings"""
        mappings = {}
        
        # Egyptian Arabic phonetic variations
        mappings[ArabicDialect.EGYPTIAN] = {
            "ج": "g",    # Jim as 'g'
            "ق": "ʔ",    # Qaf as glottal stop
            "ث": "s",    # Tha as 's'
            "ذ": "z",    # Dhal as 'z'
        }
        
        # Levantine Arabic phonetic variations
        mappings[ArabicDialect.LEVANTINE] = {
            "ق": "ʔ",    # Qaf as glottal stop
            "ك": "tʃ",   # Kaf as 'ch' in some contexts
        }
        
        # Gulf Arabic phonetic variations
        mappings[ArabicDialect.GULF] = {
            "چ": "tʃ",   # Persian ch
            "گ": "g",    # Persian g
            "ژ": "ʒ",    # Persian zh
        }
        
        # Maghrebi Arabic phonetic variations
        mappings[ArabicDialect.MAGHREBI] = {
            "ڤ": "v",    # V sound
            "پ": "p",    # P sound
        }
        
        return mappings
    
    async def adapt_for_dialect(self, text: str, dialect: ArabicDialect, 
                              formality: FormalityLevel) -> Dict[str, Any]:
        """Adapt text processing for specific dialect and formality"""
        try:
            adaptations = {
                "phonetic_adjustments": {},
                "prosodic_adjustments": {},
                "cultural_adaptations": {},
                "synthesis_parameters": {}
            }
            
            # Apply phonetic adaptations
            if dialect in self.phonetic_mappings:
                adaptations["phonetic_adjustments"] = self.phonetic_mappings[dialect]
            
            # Prosodic adaptations based on dialect
            adaptations["prosodic_adjustments"] = self._get_prosodic_adaptations(dialect, formality)
            
            # Cultural adaptations
            adaptations["cultural_adaptations"] = self._get_cultural_adaptations(dialect, formality)
            
            # TTS synthesis parameters
            adaptations["synthesis_parameters"] = self._get_synthesis_parameters(dialect, formality)
            
            return adaptations
            
        except Exception as e:
            self.logger.error(f"Dialect adaptation failed: {e}")
            return {"error": str(e)}
    
    def _get_prosodic_adaptations(self, dialect: ArabicDialect, 
                                formality: FormalityLevel) -> Dict[str, float]:
        """Get prosodic adaptations for dialect and formality"""
        adaptations = {
            "speaking_rate": 1.0,
            "pitch_range": 1.0,
            "stress_pattern": 1.0,
            "intonation_contour": 1.0
        }
        
        # Dialect-specific prosodic features
        if dialect == ArabicDialect.EGYPTIAN:
            adaptations.update({
                "speaking_rate": 1.1,  # Slightly faster
                "pitch_range": 1.2,    # More expressive
                "stress_pattern": 1.1   # More stress-timed
            })
        elif dialect == ArabicDialect.LEVANTINE:
            adaptations.update({
                "speaking_rate": 1.0,
                "pitch_range": 1.3,    # Very expressive intonation
                "intonation_contour": 1.2
            })
        elif dialect == ArabicDialect.GULF:
            adaptations.update({
                "speaking_rate": 0.9,  # Slightly slower
                "pitch_range": 0.9,    # More controlled
                "stress_pattern": 0.9
            })
        elif dialect == ArabicDialect.MAGHREBI:
            adaptations.update({
                "speaking_rate": 1.2,  # Faster
                "pitch_range": 1.1,
                "stress_pattern": 1.2
            })
        
        # Formality adjustments
        if formality in [FormalityLevel.VERY_FORMAL, FormalityLevel.FORMAL]:
            adaptations["speaking_rate"] *= 0.9  # Slower for formal speech
            adaptations["pitch_range"] *= 0.8    # More controlled pitch
        elif formality == FormalityLevel.VERY_INFORMAL:
            adaptations["speaking_rate"] *= 1.1  # Faster for informal speech
            adaptations["pitch_range"] *= 1.2    # More expressive
        
        return adaptations
    
    def _get_cultural_adaptations(self, dialect: ArabicDialect, 
                                formality: FormalityLevel) -> Dict[str, Any]:
        """Get cultural adaptations for dialect and formality"""
        adaptations = {
            "honorifics": [],
            "politeness_markers": [],
            "cultural_expressions": [],
            "religious_expressions": []
        }
        
        # Add dialect-specific cultural elements
        if dialect == ArabicDialect.EGYPTIAN:
            adaptations["cultural_expressions"] = ["يلا", "معلش", "خلاص"]
            adaptations["politeness_markers"] = ["لو سمحت", "من فضلك"]
        elif dialect == ArabicDialect.LEVANTINE:
            adaptations["cultural_expressions"] = ["يعني", "منيح", "هيك"]
            adaptations["politeness_markers"] = ["إذا بتسمح", "لو سمحت"]
        elif dialect == ArabicDialect.GULF:
            adaptations["cultural_expressions"] = ["زين", "ماكو مشكلة", "هسه"]
            adaptations["politeness_markers"] = ["لو تكرمت", "إذا ما عليك أمر"]
        
        # Add formality-appropriate expressions
        if formality in [FormalityLevel.VERY_FORMAL, FormalityLevel.FORMAL]:
            adaptations["honorifics"] = ["حضرتك", "سيادتك", "معاليك"]
            adaptations["religious_expressions"] = ["بإذنك", "إن شاء الله", "بارك الله فيك"]
        
        return adaptations
    
    def _get_synthesis_parameters(self, dialect: ArabicDialect, 
                                formality: FormalityLevel) -> Dict[str, float]:
        """Get TTS synthesis parameters for dialect and formality"""
        parameters = {
            "voice_quality": 1.0,
            "breathiness": 0.0,
            "roughness": 0.0,
            "nasality": 0.0,
            "emphasis_strength": 1.0
        }
        
        # Dialect-specific voice characteristics
        if dialect == ArabicDialect.EGYPTIAN:
            parameters.update({
                "voice_quality": 1.1,
                "emphasis_strength": 1.2
            })
        elif dialect == ArabicDialect.LEVANTINE:
            parameters.update({
                "voice_quality": 1.0,
                "breathiness": 0.1,
                "emphasis_strength": 1.1
            })
        elif dialect == ArabicDialect.GULF:
            parameters.update({
                "voice_quality": 0.9,
                "roughness": 0.1,
                "emphasis_strength": 0.9
            })
        elif dialect == ArabicDialect.MAGHREBI:
            parameters.update({
                "voice_quality": 1.1,
                "nasality": 0.2,
                "emphasis_strength": 1.3
            })
        
        # Formality adjustments
        if formality == FormalityLevel.VERY_FORMAL:
            parameters["voice_quality"] *= 0.9
            parameters["breathiness"] = 0.0
            parameters["roughness"] = 0.0
        elif formality == FormalityLevel.VERY_INFORMAL:
            parameters["breathiness"] += 0.1
            parameters["emphasis_strength"] *= 1.1
        
        return parameters


class ArabicAgent:
    """
    Arabic Language Specialist Agent - Comprehensive Arabic language processing
    Implements MSA and dialect support with diacritization and cultural context adaptation
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize processors
        self.text_processor = ArabicTextProcessor()
        self.speech_processor = ArabicSpeechProcessor()
        
        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type="arabic_specialist",
            status="idle",
            capabilities=[
                AgentCapability(
                    name="analyze_arabic_text",
                    description="Comprehensive Arabic text analysis with dialect detection",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "dialect": {"type": "string"},
                            "confidence": {"type": "number"},
                            "cultural_context": {"type": "string"},
                            "formality_level": {"type": "string"},
                            "diacritized_text": {"type": "string"}
                        }
                    }
                ),
                AgentCapability(
                    name="adapt_for_arabic_synthesis",
                    description="Adapt processing parameters for Arabic TTS synthesis",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "dialect": {"type": "string"},
                            "formality": {"type": "string"}
                        },
                        "required": ["text", "dialect"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "synthesis_adaptations": {"type": "object"}
                        }
                    }
                ),
                AgentCapability(
                    name="handle_code_switching",
                    description="Handle code-switching between Arabic and other languages",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "segments": {"type": "array"},
                            "dominant_language": {"type": "string"},
                            "switching_frequency": {"type": "number"}
                        }
                    }
                )
            ],
            performance_metrics={
                "dialect_accuracy": 0.88,  # Target >85%
                "processing_latency": 0.0,
                "total_analyses": 0,
                "successful_analyses": 0
            }
        )
        
        # Performance tracking
        self.performance_metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "average_processing_time": 0.0,
            "dialect_distribution": {},
            "accuracy_by_dialect": {}
        }
    
    async def initialize(self) -> bool:
        """Initialize the Arabic Agent"""
        try:
            self.logger.info(f"Initializing Arabic Agent {self.agent_id}")
            
            # Test text processing
            test_text = "مرحبا، كيف حالك؟ هذا نص تجريبي باللغة العربية."
            await self.text_processor.analyze_arabic_text(test_text)
            
            # Test speech processing
            await self.speech_processor.adapt_for_dialect(
                test_text, ArabicDialect.MSA, FormalityLevel.FORMAL
            )
            
            self.state.status = "ready"
            self.logger.info(f"Arabic Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Arabic Agent initialization failed: {e}")
            self.state.status = "error"
            return False
    
    async def analyze_arabic_text(self, text: str) -> ArabicTextAnalysis:
        """Analyze Arabic text for dialect, context, and other features"""
        try:
            self.state.status = "processing"
            
            analysis = await self.text_processor.analyze_arabic_text(text)
            
            # Update performance metrics
            self._update_performance_metrics(analysis)
            
            self.state.status = "ready"
            return analysis
            
        except Exception as e:
            self.logger.error(f"Arabic text analysis failed: {e}")
            self.state.status = "error"
            raise
    
    async def adapt_for_arabic_synthesis(self, text: str, dialect: str, 
                                       formality: str = "formal") -> Dict[str, Any]:
        """Adapt processing parameters for Arabic TTS synthesis"""
        try:
            dialect_enum = ArabicDialect(dialect)
            formality_enum = FormalityLevel(formality)
            
            adaptations = await self.speech_processor.adapt_for_dialect(
                text, dialect_enum, formality_enum
            )
            
            return adaptations
            
        except Exception as e:
            self.logger.error(f"Arabic synthesis adaptation failed: {e}")
            return {"error": str(e)}
    
    async def handle_code_switching(self, text: str) -> CodeSwitchingAnalysis:
        """Handle code-switching between Arabic and other languages"""
        try:
            analysis = await self.text_processor._detect_code_switching(text)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Code-switching handling failed: {e}")
            return CodeSwitchingAnalysis(
                segments=[{"language": "ar", "text": text, "confidence": 0.5}],
                switch_points=[],
                dominant_language="ar",
                languages_detected=["ar"],
                switching_frequency=0.0,
                confidence=0.5
            )
    
    def _update_performance_metrics(self, analysis: ArabicTextAnalysis):
        """Update performance metrics"""
        self.performance_metrics["total_analyses"] += 1
        
        if analysis.dialect_confidence > 0.7:  # Consider successful if confidence > 70%
            self.performance_metrics["successful_analyses"] += 1
        
        # Update dialect distribution
        dialect = analysis.dialect.value
        if dialect not in self.performance_metrics["dialect_distribution"]:
            self.performance_metrics["dialect_distribution"][dialect] = 0
        self.performance_metrics["dialect_distribution"][dialect] += 1
        
        # Update average processing time
        total = self.performance_metrics["total_analyses"]
        current_avg = self.performance_metrics["average_processing_time"]
        self.performance_metrics["average_processing_time"] = (
            (current_avg * (total - 1) + analysis.processing_time) / total
        )
        
        # Calculate accuracy
        accuracy = (self.performance_metrics["successful_analyses"] / 
                   self.performance_metrics["total_analyses"])
        
        # Update agent state metrics
        self.state.performance_metrics.update({
            "dialect_accuracy": accuracy,
            "processing_latency": self.performance_metrics["average_processing_time"],
            "total_analyses": self.performance_metrics["total_analyses"],
            "successful_analyses": self.performance_metrics["successful_analyses"]
        })
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents"""
        try:
            if message.message_type == "arabic_analysis_request":
                # Handle Arabic text analysis request
                text = message.payload.get("text")
                
                if not text:
                    raise ValueError("text is required")
                
                analysis = await self.analyze_arabic_text(text)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="arabic_analysis_response",
                    payload={
                        "dialect": analysis.dialect.value,
                        "dialect_confidence": analysis.dialect_confidence,
                        "cultural_context": analysis.cultural_context.value,
                        "formality_level": analysis.formality_level.value,
                        "diacritized_text": analysis.diacritized_text,
                        "normalized_text": analysis.normalized_text,
                        "code_switching_detected": analysis.code_switching_detected,
                        "mixed_languages": analysis.mixed_languages,
                        "dialect_markers": analysis.dialect_markers,
                        "cultural_markers": analysis.cultural_markers,
                        "processing_time": analysis.processing_time,
                        "metadata": analysis.metadata,
                        "agent_id": self.agent_id
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "arabic_synthesis_adaptation_request":
                # Handle synthesis adaptation request
                text = message.payload.get("text")
                dialect = message.payload.get("dialect", "msa")
                formality = message.payload.get("formality", "formal")
                
                if not text:
                    raise ValueError("text is required")
                
                adaptations = await self.adapt_for_arabic_synthesis(text, dialect, formality)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="arabic_synthesis_adaptation_response",
                    payload={
                        "synthesis_adaptations": adaptations,
                        "agent_id": self.agent_id
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "code_switching_analysis_request":
                # Handle code-switching analysis request
                text = message.payload.get("text")
                
                if not text:
                    raise ValueError("text is required")
                
                analysis = await self.handle_code_switching(text)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="code_switching_analysis_response",
                    payload={
                        "segments": analysis.segments,
                        "switch_points": analysis.switch_points,
                        "dominant_language": analysis.dominant_language,
                        "languages_detected": analysis.languages_detected,
                        "switching_frequency": analysis.switching_frequency,
                        "confidence": analysis.confidence,
                        "agent_id": self.agent_id
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            else:
                self.logger.warning(f"Unknown message type: {message.message_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Message handling failed: {e}")
            
            # Send error response
            return AgentMessage(
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                message_type="error",
                payload={
                    "error": str(e),
                    "original_message_type": message.message_type,
                    "agent_id": self.agent_id
                },
                correlation_id=message.message_id,
                priority=message.priority
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "agent_id": self.agent_id,
            "status": self.state.status,
            "performance_metrics": self.performance_metrics.copy(),
            "state_metrics": self.state.performance_metrics.copy(),
            "capabilities": [cap.name for cap in self.state.capabilities],
            "dialect_distribution": self.performance_metrics["dialect_distribution"].copy()
        }