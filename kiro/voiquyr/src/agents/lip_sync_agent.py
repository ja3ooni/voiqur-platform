"""
Lip Sync Agent - Facial animation synchronization with synthesized speech
Implements facial animation synchronization with <50ms latency and phoneme-to-viseme mapping
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
import math

from ..core.models import AgentMessage, AgentState, Task, AgentCapability, Priority
from ..core.messaging import MessageBus


class Viseme(Enum):
    """Standard visemes for facial animation"""
    # Silence and neutral
    SIL = "sil"  # Silence
    
    # Vowels
    AA = "aa"    # father, hot
    AE = "ae"    # cat, bat
    AH = "ah"    # but, cut
    AO = "ao"    # law, caught
    AW = "aw"    # how, now
    AY = "ay"    # my, eye
    EH = "eh"    # bed, red
    ER = "er"    # bird, hurt
    EY = "ey"    # say, day
    IH = "ih"    # bit, hit
    IY = "iy"    # beat, feet
    OW = "ow"    # go, show
    OY = "oy"    # boy, toy
    UH = "uh"    # book, good
    UW = "uw"    # boot, food
    
    # Consonants
    B_P_M = "b_p_m"      # Bilabial: b, p, m
    F_V = "f_v"          # Labiodental: f, v
    TH = "th"            # Dental: th (thin, this)
    T_D_N_L = "t_d_n_l"  # Alveolar: t, d, n, l
    S_Z = "s_z"          # Sibilant: s, z
    SH_ZH = "sh_zh"      # Postalveolar: sh, zh
    CH_JH = "ch_jh"      # Affricate: ch, jh
    K_G_NG = "k_g_ng"    # Velar: k, g, ng
    R = "r"              # Rhotic: r
    W = "w"              # Approximant: w
    Y = "y"              # Palatal: y
    H = "h"              # Glottal: h


class AvatarStyle(Enum):
    """Supported avatar styles"""
    REALISTIC_3D = "realistic_3d"
    CARTOON_3D = "cartoon_3d"
    ANIME_2D = "anime_2d"
    MINIMAL_2D = "minimal_2d"
    ABSTRACT = "abstract"


class RenderingEngine(Enum):
    """Supported 3D rendering engines"""
    UNITY = "unity"
    UNREAL = "unreal"
    BLENDER = "blender"
    THREE_JS = "three_js"
    BABYLON_JS = "babylon_js"
    CUSTOM = "custom"


@dataclass
class PhonemeTimestamp:
    """Phoneme with timing information"""
    phoneme: str
    start_time: float  # seconds
    end_time: float    # seconds
    confidence: float  # 0.0 to 1.0


@dataclass
class VisemeFrame:
    """Single viseme animation frame"""
    viseme: Viseme
    timestamp: float  # seconds
    duration: float   # seconds
    intensity: float  # 0.0 to 1.0
    blend_weights: Dict[str, float] = field(default_factory=dict)  # For blendshape animation
    jaw_open: float = 0.0      # 0.0 to 1.0
    lip_pucker: float = 0.0    # 0.0 to 1.0
    lip_spread: float = 0.0    # 0.0 to 1.0
    tongue_height: float = 0.0 # 0.0 to 1.0
    tongue_front: float = 0.0  # 0.0 to 1.0


@dataclass
class LipSyncAnimation:
    """Complete lip sync animation sequence"""
    animation_id: str
    viseme_frames: List[VisemeFrame]
    total_duration: float
    frame_rate: int  # fps
    avatar_style: AvatarStyle
    rendering_engine: RenderingEngine
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_frame_at_time(self, timestamp: float) -> Optional[VisemeFrame]:
        """Get the viseme frame at a specific timestamp"""
        for frame in self.viseme_frames:
            if frame.timestamp <= timestamp < frame.timestamp + frame.duration:
                return frame
        return None
    
    def get_blended_frame(self, timestamp: float) -> Optional[VisemeFrame]:
        """Get blended viseme frame for smooth transitions"""
        current_frame = self.get_frame_at_time(timestamp)
        if not current_frame:
            return None
        
        # Find next frame for blending
        next_frame = None
        for frame in self.viseme_frames:
            if frame.timestamp > current_frame.timestamp:
                next_frame = frame
                break
        
        if not next_frame:
            return current_frame
        
        # Calculate blend factor
        transition_start = current_frame.timestamp + current_frame.duration * 0.7
        transition_end = next_frame.timestamp
        
        if timestamp < transition_start:
            return current_frame
        elif timestamp >= transition_end:
            return next_frame
        else:
            # Blend between frames
            blend_factor = (timestamp - transition_start) / (transition_end - transition_start)
            return self._blend_frames(current_frame, next_frame, blend_factor)
    
    def _blend_frames(self, frame1: VisemeFrame, frame2: VisemeFrame, factor: float) -> VisemeFrame:
        """Blend two viseme frames"""
        return VisemeFrame(
            viseme=frame2.viseme if factor > 0.5 else frame1.viseme,
            timestamp=frame1.timestamp + (frame2.timestamp - frame1.timestamp) * factor,
            duration=frame1.duration + (frame2.duration - frame1.duration) * factor,
            intensity=frame1.intensity + (frame2.intensity - frame1.intensity) * factor,
            jaw_open=frame1.jaw_open + (frame2.jaw_open - frame1.jaw_open) * factor,
            lip_pucker=frame1.lip_pucker + (frame2.lip_pucker - frame1.lip_pucker) * factor,
            lip_spread=frame1.lip_spread + (frame2.lip_spread - frame1.lip_spread) * factor,
            tongue_height=frame1.tongue_height + (frame2.tongue_height - frame1.tongue_height) * factor,
            tongue_front=frame1.tongue_front + (frame2.tongue_front - frame1.tongue_front) * factor
        )


class PhonemeToVisemeMapper:
    """Maps phonemes to visemes for different languages"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize phoneme-to-viseme mappings for different languages
        self.mappings = self._initialize_mappings()
    
    def _initialize_mappings(self) -> Dict[str, Dict[str, Viseme]]:
        """Initialize phoneme-to-viseme mappings for multiple languages"""
        mappings = {}
        
        # English (IPA and ARPABET)
        mappings["en"] = {
            # Vowels
            "AA": Viseme.AA, "aa": Viseme.AA, "ɑ": Viseme.AA,
            "AE": Viseme.AE, "ae": Viseme.AE, "æ": Viseme.AE,
            "AH": Viseme.AH, "ah": Viseme.AH, "ʌ": Viseme.AH, "ə": Viseme.AH,
            "AO": Viseme.AO, "ao": Viseme.AO, "ɔ": Viseme.AO,
            "AW": Viseme.AW, "aw": Viseme.AW, "aʊ": Viseme.AW,
            "AY": Viseme.AY, "ay": Viseme.AY, "aɪ": Viseme.AY,
            "EH": Viseme.EH, "eh": Viseme.EH, "ɛ": Viseme.EH,
            "ER": Viseme.ER, "er": Viseme.ER, "ɝ": Viseme.ER, "ɚ": Viseme.ER,
            "EY": Viseme.EY, "ey": Viseme.EY, "eɪ": Viseme.EY,
            "IH": Viseme.IH, "ih": Viseme.IH, "ɪ": Viseme.IH,
            "IY": Viseme.IY, "iy": Viseme.IY, "i": Viseme.IY,
            "OW": Viseme.OW, "ow": Viseme.OW, "oʊ": Viseme.OW,
            "OY": Viseme.OY, "oy": Viseme.OY, "ɔɪ": Viseme.OY,
            "UH": Viseme.UH, "uh": Viseme.UH, "ʊ": Viseme.UH,
            "UW": Viseme.UW, "uw": Viseme.UW, "u": Viseme.UW,
            
            # Consonants
            "B": Viseme.B_P_M, "b": Viseme.B_P_M,
            "P": Viseme.B_P_M, "p": Viseme.B_P_M,
            "M": Viseme.B_P_M, "m": Viseme.B_P_M,
            "F": Viseme.F_V, "f": Viseme.F_V,
            "V": Viseme.F_V, "v": Viseme.F_V,
            "TH": Viseme.TH, "th": Viseme.TH, "θ": Viseme.TH, "ð": Viseme.TH,
            "T": Viseme.T_D_N_L, "t": Viseme.T_D_N_L,
            "D": Viseme.T_D_N_L, "d": Viseme.T_D_N_L,
            "N": Viseme.T_D_N_L, "n": Viseme.T_D_N_L,
            "L": Viseme.T_D_N_L, "l": Viseme.T_D_N_L,
            "S": Viseme.S_Z, "s": Viseme.S_Z,
            "Z": Viseme.S_Z, "z": Viseme.S_Z,
            "SH": Viseme.SH_ZH, "sh": Viseme.SH_ZH, "ʃ": Viseme.SH_ZH,
            "ZH": Viseme.SH_ZH, "zh": Viseme.SH_ZH, "ʒ": Viseme.SH_ZH,
            "CH": Viseme.CH_JH, "ch": Viseme.CH_JH, "tʃ": Viseme.CH_JH,
            "JH": Viseme.CH_JH, "jh": Viseme.CH_JH, "dʒ": Viseme.CH_JH,
            "K": Viseme.K_G_NG, "k": Viseme.K_G_NG,
            "G": Viseme.K_G_NG, "g": Viseme.K_G_NG,
            "NG": Viseme.K_G_NG, "ng": Viseme.K_G_NG, "ŋ": Viseme.K_G_NG,
            "R": Viseme.R, "r": Viseme.R, "ɹ": Viseme.R,
            "W": Viseme.W, "w": Viseme.W,
            "Y": Viseme.Y, "y": Viseme.Y, "j": Viseme.Y,
            "H": Viseme.H, "h": Viseme.H,
            
            # Silence
            "SIL": Viseme.SIL, "sil": Viseme.SIL, "": Viseme.SIL
        }
        
        # German
        mappings["de"] = {
            # Vowels (similar to English with some differences)
            "a": Viseme.AA, "ɑ": Viseme.AA,
            "ɛ": Viseme.EH, "e": Viseme.EY,
            "ɪ": Viseme.IH, "i": Viseme.IY,
            "ɔ": Viseme.AO, "o": Viseme.OW,
            "ʊ": Viseme.UH, "u": Viseme.UW,
            "ə": Viseme.AH, "ɐ": Viseme.AH,
            "y": Viseme.IY, "ʏ": Viseme.IH,  # German umlauts
            "ø": Viseme.EY, "œ": Viseme.EH,
            
            # Consonants (mostly similar to English)
            "b": Viseme.B_P_M, "p": Viseme.B_P_M, "m": Viseme.B_P_M,
            "f": Viseme.F_V, "v": Viseme.F_V,
            "t": Viseme.T_D_N_L, "d": Viseme.T_D_N_L, "n": Viseme.T_D_N_L, "l": Viseme.T_D_N_L,
            "s": Viseme.S_Z, "z": Viseme.S_Z,
            "ʃ": Viseme.SH_ZH, "ʒ": Viseme.SH_ZH,
            "tʃ": Viseme.CH_JH, "dʒ": Viseme.CH_JH,
            "k": Viseme.K_G_NG, "g": Viseme.K_G_NG, "ŋ": Viseme.K_G_NG,
            "ʁ": Viseme.R, "r": Viseme.R,  # German uvular R
            "w": Viseme.W, "j": Viseme.Y, "h": Viseme.H,
            "x": Viseme.K_G_NG,  # German ach-laut
            "ç": Viseme.SH_ZH,   # German ich-laut
            
            "": Viseme.SIL
        }
        
        # French
        mappings["fr"] = {
            # Vowels
            "a": Viseme.AA, "ɑ": Viseme.AA,
            "e": Viseme.EY, "ɛ": Viseme.EH, "ə": Viseme.AH,
            "i": Viseme.IY, "ɪ": Viseme.IH,
            "o": Viseme.OW, "ɔ": Viseme.AO,
            "u": Viseme.UW, "ʊ": Viseme.UH,
            "y": Viseme.IY, "ø": Viseme.EY, "œ": Viseme.EH,  # French front rounded vowels
            
            # Nasal vowels (approximate with base vowel + slight modification)
            "ã": Viseme.AA, "ɛ̃": Viseme.EH, "ɔ̃": Viseme.AO, "œ̃": Viseme.EH,
            
            # Consonants
            "b": Viseme.B_P_M, "p": Viseme.B_P_M, "m": Viseme.B_P_M,
            "f": Viseme.F_V, "v": Viseme.F_V,
            "t": Viseme.T_D_N_L, "d": Viseme.T_D_N_L, "n": Viseme.T_D_N_L, "l": Viseme.T_D_N_L,
            "s": Viseme.S_Z, "z": Viseme.S_Z,
            "ʃ": Viseme.SH_ZH, "ʒ": Viseme.SH_ZH,
            "k": Viseme.K_G_NG, "g": Viseme.K_G_NG, "ŋ": Viseme.K_G_NG,
            "ʁ": Viseme.R, "r": Viseme.R,  # French uvular R
            "w": Viseme.W, "j": Viseme.Y, "ɥ": Viseme.W,  # French approximants
            
            "": Viseme.SIL
        }
        
        # Add more languages as needed...
        
        return mappings
    
    def map_phoneme_to_viseme(self, phoneme: str, language: str = "en") -> Viseme:
        """Map a phoneme to its corresponding viseme"""
        try:
            if language not in self.mappings:
                language = "en"  # Fallback to English
            
            mapping = self.mappings[language]
            
            # Direct lookup
            if phoneme in mapping:
                return mapping[phoneme]
            
            # Try lowercase
            if phoneme.lower() in mapping:
                return mapping[phoneme.lower()]
            
            # Try uppercase
            if phoneme.upper() in mapping:
                return mapping[phoneme.upper()]
            
            # Fallback to silence for unknown phonemes
            self.logger.warning(f"Unknown phoneme '{phoneme}' for language '{language}', using silence")
            return Viseme.SIL
            
        except Exception as e:
            self.logger.error(f"Phoneme mapping failed: {e}")
            return Viseme.SIL
    
    def map_phoneme_sequence(self, phonemes: List[PhonemeTimestamp], 
                           language: str = "en") -> List[Tuple[Viseme, float, float]]:
        """Map a sequence of phonemes to visemes with timing"""
        viseme_sequence = []
        
        for phoneme_data in phonemes:
            viseme = self.map_phoneme_to_viseme(phoneme_data.phoneme, language)
            viseme_sequence.append((viseme, phoneme_data.start_time, phoneme_data.end_time))
        
        return viseme_sequence


class VisemeAnimationGenerator:
    """Generate viseme animations with facial parameters"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Viseme characteristics for facial animation
        self.viseme_characteristics = self._initialize_viseme_characteristics()
    
    def _initialize_viseme_characteristics(self) -> Dict[Viseme, Dict[str, float]]:
        """Initialize facial characteristics for each viseme"""
        characteristics = {}
        
        # Silence
        characteristics[Viseme.SIL] = {
            "jaw_open": 0.0, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.5, "tongue_front": 0.5
        }
        
        # Vowels
        characteristics[Viseme.AA] = {  # father, hot
            "jaw_open": 0.8, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.2, "tongue_front": 0.3
        }
        
        characteristics[Viseme.AE] = {  # cat, bat
            "jaw_open": 0.6, "lip_pucker": 0.0, "lip_spread": 0.3,
            "tongue_height": 0.3, "tongue_front": 0.7
        }
        
        characteristics[Viseme.AH] = {  # but, cut
            "jaw_open": 0.4, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.4, "tongue_front": 0.5
        }
        
        characteristics[Viseme.AO] = {  # law, caught
            "jaw_open": 0.6, "lip_pucker": 0.4, "lip_spread": 0.0,
            "tongue_height": 0.3, "tongue_front": 0.2
        }
        
        characteristics[Viseme.EH] = {  # bed, red
            "jaw_open": 0.4, "lip_pucker": 0.0, "lip_spread": 0.2,
            "tongue_height": 0.5, "tongue_front": 0.7
        }
        
        characteristics[Viseme.EY] = {  # say, day
            "jaw_open": 0.3, "lip_pucker": 0.0, "lip_spread": 0.4,
            "tongue_height": 0.6, "tongue_front": 0.8
        }
        
        characteristics[Viseme.IH] = {  # bit, hit
            "jaw_open": 0.2, "lip_pucker": 0.0, "lip_spread": 0.3,
            "tongue_height": 0.7, "tongue_front": 0.8
        }
        
        characteristics[Viseme.IY] = {  # beat, feet
            "jaw_open": 0.1, "lip_pucker": 0.0, "lip_spread": 0.6,
            "tongue_height": 0.9, "tongue_front": 0.9
        }
        
        characteristics[Viseme.OW] = {  # go, show
            "jaw_open": 0.3, "lip_pucker": 0.6, "lip_spread": 0.0,
            "tongue_height": 0.6, "tongue_front": 0.2
        }
        
        characteristics[Viseme.UH] = {  # book, good
            "jaw_open": 0.2, "lip_pucker": 0.4, "lip_spread": 0.0,
            "tongue_height": 0.7, "tongue_front": 0.2
        }
        
        characteristics[Viseme.UW] = {  # boot, food
            "jaw_open": 0.1, "lip_pucker": 0.8, "lip_spread": 0.0,
            "tongue_height": 0.8, "tongue_front": 0.1
        }
        
        # Consonants (simplified - focus on visible articulation)
        characteristics[Viseme.B_P_M] = {  # Bilabial
            "jaw_open": 0.0, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.5, "tongue_front": 0.5
        }
        
        characteristics[Viseme.F_V] = {  # Labiodental
            "jaw_open": 0.1, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.5, "tongue_front": 0.5
        }
        
        characteristics[Viseme.TH] = {  # Dental
            "jaw_open": 0.2, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.3, "tongue_front": 0.9
        }
        
        characteristics[Viseme.T_D_N_L] = {  # Alveolar
            "jaw_open": 0.2, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.7, "tongue_front": 0.8
        }
        
        characteristics[Viseme.S_Z] = {  # Sibilant
            "jaw_open": 0.1, "lip_pucker": 0.0, "lip_spread": 0.2,
            "tongue_height": 0.8, "tongue_front": 0.8
        }
        
        characteristics[Viseme.SH_ZH] = {  # Postalveolar
            "jaw_open": 0.1, "lip_pucker": 0.2, "lip_spread": 0.0,
            "tongue_height": 0.7, "tongue_front": 0.6
        }
        
        characteristics[Viseme.CH_JH] = {  # Affricate
            "jaw_open": 0.2, "lip_pucker": 0.1, "lip_spread": 0.0,
            "tongue_height": 0.7, "tongue_front": 0.7
        }
        
        characteristics[Viseme.K_G_NG] = {  # Velar
            "jaw_open": 0.3, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.8, "tongue_front": 0.2
        }
        
        characteristics[Viseme.R] = {  # Rhotic
            "jaw_open": 0.2, "lip_pucker": 0.3, "lip_spread": 0.0,
            "tongue_height": 0.6, "tongue_front": 0.4
        }
        
        characteristics[Viseme.W] = {  # Approximant w
            "jaw_open": 0.1, "lip_pucker": 0.6, "lip_spread": 0.0,
            "tongue_height": 0.7, "tongue_front": 0.2
        }
        
        characteristics[Viseme.Y] = {  # Palatal y
            "jaw_open": 0.1, "lip_pucker": 0.0, "lip_spread": 0.4,
            "tongue_height": 0.9, "tongue_front": 0.9
        }
        
        characteristics[Viseme.H] = {  # Glottal h
            "jaw_open": 0.3, "lip_pucker": 0.0, "lip_spread": 0.0,
            "tongue_height": 0.5, "tongue_front": 0.5
        }
        
        return characteristics
    
    async def generate_animation(self, viseme_sequence: List[Tuple[Viseme, float, float]],
                               avatar_style: AvatarStyle = AvatarStyle.REALISTIC_3D,
                               rendering_engine: RenderingEngine = RenderingEngine.UNITY,
                               frame_rate: int = 30) -> LipSyncAnimation:
        """Generate lip sync animation from viseme sequence"""
        try:
            animation_id = str(uuid.uuid4())
            viseme_frames = []
            
            frame_duration = 1.0 / frame_rate
            
            for viseme, start_time, end_time in viseme_sequence:
                duration = end_time - start_time
                
                # Get base characteristics for this viseme
                if viseme in self.viseme_characteristics:
                    base_chars = self.viseme_characteristics[viseme].copy()
                else:
                    base_chars = self.viseme_characteristics[Viseme.SIL].copy()
                
                # Apply avatar style modifications
                self._apply_avatar_style_modifications(base_chars, avatar_style)
                
                # Create viseme frame
                frame = VisemeFrame(
                    viseme=viseme,
                    timestamp=start_time,
                    duration=duration,
                    intensity=1.0,  # Could be modified based on phoneme confidence
                    jaw_open=base_chars["jaw_open"],
                    lip_pucker=base_chars["lip_pucker"],
                    lip_spread=base_chars["lip_spread"],
                    tongue_height=base_chars["tongue_height"],
                    tongue_front=base_chars["tongue_front"]
                )
                
                # Generate blendshape weights for specific rendering engines
                frame.blend_weights = self._generate_blendshape_weights(frame, rendering_engine)
                
                viseme_frames.append(frame)
            
            # Calculate total duration
            total_duration = max([f.timestamp + f.duration for f in viseme_frames]) if viseme_frames else 0.0
            
            # Apply smoothing and transitions
            smoothed_frames = await self._apply_smoothing(viseme_frames, frame_rate)
            
            animation = LipSyncAnimation(
                animation_id=animation_id,
                viseme_frames=smoothed_frames,
                total_duration=total_duration,
                frame_rate=frame_rate,
                avatar_style=avatar_style,
                rendering_engine=rendering_engine,
                metadata={
                    "viseme_count": len(viseme_sequence),
                    "generation_method": "phoneme_based",
                    "smoothing_applied": True
                }
            )
            
            return animation
            
        except Exception as e:
            self.logger.error(f"Animation generation failed: {e}")
            raise
    
    def _apply_avatar_style_modifications(self, characteristics: Dict[str, float], 
                                        avatar_style: AvatarStyle):
        """Apply avatar style-specific modifications to characteristics"""
        if avatar_style == AvatarStyle.CARTOON_3D:
            # Exaggerate movements for cartoon style
            for key in characteristics:
                characteristics[key] = min(1.0, characteristics[key] * 1.2)
        
        elif avatar_style == AvatarStyle.ANIME_2D:
            # Reduce jaw movement, emphasize lip shapes
            characteristics["jaw_open"] *= 0.7
            characteristics["lip_pucker"] *= 1.3
            characteristics["lip_spread"] *= 1.3
        
        elif avatar_style == AvatarStyle.MINIMAL_2D:
            # Simplify to basic mouth shapes
            characteristics["tongue_height"] = 0.5
            characteristics["tongue_front"] = 0.5
            if characteristics["jaw_open"] > 0.5:
                characteristics["jaw_open"] = 0.8
            elif characteristics["jaw_open"] > 0.2:
                characteristics["jaw_open"] = 0.4
            else:
                characteristics["jaw_open"] = 0.0
        
        elif avatar_style == AvatarStyle.ABSTRACT:
            # Highly simplified representation
            for key in characteristics:
                if characteristics[key] > 0.5:
                    characteristics[key] = 1.0
                elif characteristics[key] > 0.2:
                    characteristics[key] = 0.5
                else:
                    characteristics[key] = 0.0
    
    def _generate_blendshape_weights(self, frame: VisemeFrame, 
                                   rendering_engine: RenderingEngine) -> Dict[str, float]:
        """Generate blendshape weights for specific rendering engines"""
        weights = {}
        
        if rendering_engine == RenderingEngine.UNITY:
            # Unity-style blendshapes
            weights.update({
                "JawOpen": frame.jaw_open,
                "MouthPucker": frame.lip_pucker,
                "MouthStretch": frame.lip_spread,
                "TongueUp": frame.tongue_height,
                "TongueOut": frame.tongue_front
            })
            
            # Add viseme-specific blendshapes
            viseme_name = frame.viseme.value.upper()
            weights[f"Viseme_{viseme_name}"] = frame.intensity
        
        elif rendering_engine == RenderingEngine.UNREAL:
            # Unreal Engine style
            weights.update({
                "Jaw_Open": frame.jaw_open,
                "Lips_Pucker": frame.lip_pucker,
                "Lips_Stretch": frame.lip_spread,
                "Tongue_Raise": frame.tongue_height,
                "Tongue_Forward": frame.tongue_front
            })
        
        elif rendering_engine == RenderingEngine.BLENDER:
            # Blender style
            weights.update({
                "jaw.open": frame.jaw_open,
                "lips.pucker": frame.lip_pucker,
                "lips.spread": frame.lip_spread,
                "tongue.height": frame.tongue_height,
                "tongue.front": frame.tongue_front
            })
        
        elif rendering_engine in [RenderingEngine.THREE_JS, RenderingEngine.BABYLON_JS]:
            # Web-based engines (simplified)
            weights.update({
                "jawOpen": frame.jaw_open,
                "mouthPucker": frame.lip_pucker,
                "mouthStretch": frame.lip_spread
            })
        
        return weights
    
    async def _apply_smoothing(self, frames: List[VisemeFrame], 
                             frame_rate: int) -> List[VisemeFrame]:
        """Apply smoothing to reduce abrupt transitions"""
        if len(frames) < 2:
            return frames
        
        smoothed_frames = []
        smoothing_window = max(1, frame_rate // 10)  # 100ms smoothing window
        
        for i, frame in enumerate(frames):
            if i == 0 or i == len(frames) - 1:
                # Keep first and last frames unchanged
                smoothed_frames.append(frame)
                continue
            
            # Calculate smoothed values
            start_idx = max(0, i - smoothing_window // 2)
            end_idx = min(len(frames), i + smoothing_window // 2 + 1)
            
            window_frames = frames[start_idx:end_idx]
            
            # Smooth each parameter
            smoothed_frame = VisemeFrame(
                viseme=frame.viseme,
                timestamp=frame.timestamp,
                duration=frame.duration,
                intensity=frame.intensity,
                jaw_open=np.mean([f.jaw_open for f in window_frames]),
                lip_pucker=np.mean([f.lip_pucker for f in window_frames]),
                lip_spread=np.mean([f.lip_spread for f in window_frames]),
                tongue_height=np.mean([f.tongue_height for f in window_frames]),
                tongue_front=np.mean([f.tongue_front for f in window_frames]),
                blend_weights=frame.blend_weights.copy()
            )
            
            smoothed_frames.append(smoothed_frame)
        
        return smoothed_frames


class LipSyncAgent:
    """
    Lip Sync Agent - Facial animation synchronization with synthesized speech
    Implements facial animation synchronization with <50ms latency
    """
    
    def __init__(self, agent_id: str, message_bus: MessageBus):
        self.agent_id = agent_id
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.phoneme_mapper = PhonemeToVisemeMapper()
        self.animation_generator = VisemeAnimationGenerator()
        
        # Agent state
        self.state = AgentState(
            agent_id=agent_id,
            agent_type="lip_sync",
            status="idle",
            capabilities=[
                AgentCapability(
                    name="generate_lip_sync_animation",
                    description="Generate lip sync animation from phonemes with <50ms latency",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "phonemes": {"type": "array", "description": "Array of phoneme objects with timing"},
                            "language": {"type": "string", "default": "en"},
                            "avatar_style": {"type": "string", "default": "realistic_3d"},
                            "rendering_engine": {"type": "string", "default": "unity"},
                            "frame_rate": {"type": "integer", "default": 30}
                        },
                        "required": ["phonemes"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "animation": {"type": "object"},
                            "total_duration": {"type": "number"},
                            "frame_count": {"type": "integer"}
                        }
                    }
                ),
                AgentCapability(
                    name="get_realtime_viseme",
                    description="Get current viseme for real-time animation",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "animation_id": {"type": "string"},
                            "timestamp": {"type": "number"}
                        },
                        "required": ["animation_id", "timestamp"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "viseme_frame": {"type": "object"}
                        }
                    }
                ),
                AgentCapability(
                    name="convert_to_engine_format",
                    description="Convert animation to specific rendering engine format",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "animation": {"type": "object"},
                            "target_engine": {"type": "string"}
                        },
                        "required": ["animation", "target_engine"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "converted_animation": {"type": "object"}
                        }
                    }
                )
            ],
            performance_metrics={
                "generation_latency": 0.0,  # Target <50ms
                "total_animations": 0,
                "average_frame_rate": 30.0,
                "successful_generations": 0
            }
        )
        
        # Performance tracking
        self.performance_metrics = {
            "total_animations": 0,
            "successful_generations": 0,
            "average_generation_time": 0.0,
            "average_frame_count": 0.0
        }
        
        # Animation cache for real-time access
        self.animation_cache: Dict[str, LipSyncAnimation] = {}
    
    async def initialize(self) -> bool:
        """Initialize the Lip Sync Agent"""
        try:
            self.logger.info(f"Initializing Lip Sync Agent {self.agent_id}")
            
            # Test animation generation
            test_phonemes = [
                PhonemeTimestamp("h", 0.0, 0.1, 0.9),
                PhonemeTimestamp("ɛ", 0.1, 0.3, 0.95),
                PhonemeTimestamp("l", 0.3, 0.4, 0.9),
                PhonemeTimestamp("oʊ", 0.4, 0.7, 0.95)
            ]
            
            viseme_sequence = self.phoneme_mapper.map_phoneme_sequence(test_phonemes, "en")
            await self.animation_generator.generate_animation(viseme_sequence)
            
            self.state.status = "ready"
            self.logger.info(f"Lip Sync Agent {self.agent_id} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Lip Sync Agent initialization failed: {e}")
            self.state.status = "error"
            return False
    
    async def generate_lip_sync_animation(self, phonemes: List[Dict[str, Any]], 
                                        language: str = "en",
                                        avatar_style: str = "realistic_3d",
                                        rendering_engine: str = "unity",
                                        frame_rate: int = 30) -> LipSyncAnimation:
        """Generate lip sync animation from phoneme data"""
        try:
            start_time = time.time()
            self.state.status = "processing"
            
            # Convert phoneme data to PhonemeTimestamp objects
            phoneme_timestamps = []
            for p in phonemes:
                phoneme_timestamps.append(PhonemeTimestamp(
                    phoneme=p["phoneme"],
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    confidence=p.get("confidence", 1.0)
                ))
            
            # Map phonemes to visemes
            viseme_sequence = self.phoneme_mapper.map_phoneme_sequence(phoneme_timestamps, language)
            
            # Generate animation
            avatar_style_enum = AvatarStyle(avatar_style)
            rendering_engine_enum = RenderingEngine(rendering_engine)
            
            animation = await self.animation_generator.generate_animation(
                viseme_sequence, avatar_style_enum, rendering_engine_enum, frame_rate
            )
            
            # Cache animation for real-time access
            self.animation_cache[animation.animation_id] = animation
            
            # Update performance metrics
            generation_time = time.time() - start_time
            self._update_performance_metrics(animation, generation_time)
            
            self.state.status = "ready"
            return animation
            
        except Exception as e:
            self.logger.error(f"Lip sync animation generation failed: {e}")
            self.state.status = "error"
            raise
    
    def get_realtime_viseme(self, animation_id: str, timestamp: float) -> Optional[VisemeFrame]:
        """Get current viseme frame for real-time animation"""
        try:
            if animation_id not in self.animation_cache:
                self.logger.warning(f"Animation {animation_id} not found in cache")
                return None
            
            animation = self.animation_cache[animation_id]
            return animation.get_blended_frame(timestamp)
            
        except Exception as e:
            self.logger.error(f"Real-time viseme retrieval failed: {e}")
            return None
    
    def convert_to_engine_format(self, animation: LipSyncAnimation, 
                               target_engine: str) -> Dict[str, Any]:
        """Convert animation to specific rendering engine format"""
        try:
            target_engine_enum = RenderingEngine(target_engine)
            
            if target_engine_enum == RenderingEngine.UNITY:
                return self._convert_to_unity_format(animation)
            elif target_engine_enum == RenderingEngine.UNREAL:
                return self._convert_to_unreal_format(animation)
            elif target_engine_enum == RenderingEngine.BLENDER:
                return self._convert_to_blender_format(animation)
            elif target_engine_enum in [RenderingEngine.THREE_JS, RenderingEngine.BABYLON_JS]:
                return self._convert_to_web_format(animation)
            else:
                return self._convert_to_generic_format(animation)
                
        except Exception as e:
            self.logger.error(f"Engine format conversion failed: {e}")
            return self._convert_to_generic_format(animation)
    
    def _convert_to_unity_format(self, animation: LipSyncAnimation) -> Dict[str, Any]:
        """Convert to Unity animation format"""
        unity_animation = {
            "animationClip": {
                "name": f"LipSync_{animation.animation_id}",
                "length": animation.total_duration,
                "frameRate": animation.frame_rate,
                "curves": []
            }
        }
        
        # Create animation curves for each blendshape
        blendshape_curves = {}
        
        for frame in animation.viseme_frames:
            for blendshape, weight in frame.blend_weights.items():
                if blendshape not in blendshape_curves:
                    blendshape_curves[blendshape] = []
                
                blendshape_curves[blendshape].append({
                    "time": frame.timestamp,
                    "value": weight * 100,  # Unity uses 0-100 range
                    "inTangent": 0,
                    "outTangent": 0
                })
        
        # Add curves to animation
        for blendshape, keyframes in blendshape_curves.items():
            unity_animation["animationClip"]["curves"].append({
                "path": "Head",  # Assuming head mesh
                "propertyName": f"blendShape.{blendshape}",
                "keyframes": keyframes
            })
        
        return unity_animation
    
    def _convert_to_unreal_format(self, animation: LipSyncAnimation) -> Dict[str, Any]:
        """Convert to Unreal Engine animation format"""
        unreal_animation = {
            "animationSequence": {
                "name": f"LipSync_{animation.animation_id}",
                "sequenceLength": animation.total_duration,
                "frameRate": animation.frame_rate,
                "morphTargetCurves": []
            }
        }
        
        # Group frames by morph target
        morph_curves = {}
        
        for frame in animation.viseme_frames:
            for morph_target, weight in frame.blend_weights.items():
                if morph_target not in morph_curves:
                    morph_curves[morph_target] = []
                
                morph_curves[morph_target].append({
                    "time": frame.timestamp,
                    "value": weight
                })
        
        # Add morph target curves
        for morph_target, keyframes in morph_curves.items():
            unreal_animation["animationSequence"]["morphTargetCurves"].append({
                "morphTargetName": morph_target,
                "keys": keyframes
            })
        
        return unreal_animation
    
    def _convert_to_blender_format(self, animation: LipSyncAnimation) -> Dict[str, Any]:
        """Convert to Blender animation format"""
        blender_animation = {
            "action": {
                "name": f"LipSync_{animation.animation_id}",
                "frame_range": [0, int(animation.total_duration * animation.frame_rate)],
                "fcurves": []
            }
        }
        
        # Create F-curves for shape keys
        shape_key_data = {}
        
        for frame in animation.viseme_frames:
            frame_number = int(frame.timestamp * animation.frame_rate)
            
            for shape_key, weight in frame.blend_weights.items():
                if shape_key not in shape_key_data:
                    shape_key_data[shape_key] = []
                
                shape_key_data[shape_key].append({
                    "frame": frame_number,
                    "value": weight,
                    "interpolation": "BEZIER"
                })
        
        # Add F-curves
        for shape_key, keyframes in shape_key_data.items():
            blender_animation["action"]["fcurves"].append({
                "data_path": f'key_blocks["{shape_key}"].value',
                "keyframes": keyframes
            })
        
        return blender_animation
    
    def _convert_to_web_format(self, animation: LipSyncAnimation) -> Dict[str, Any]:
        """Convert to web-based format (Three.js/Babylon.js)"""
        web_animation = {
            "name": f"LipSync_{animation.animation_id}",
            "duration": animation.total_duration,
            "fps": animation.frame_rate,
            "tracks": []
        }
        
        # Create morph target tracks
        morph_tracks = {}
        
        for frame in animation.viseme_frames:
            for morph_name, weight in frame.blend_weights.items():
                if morph_name not in morph_tracks:
                    morph_tracks[morph_name] = {
                        "name": f"Head.morphTargetInfluences[{morph_name}]",
                        "type": "number",
                        "times": [],
                        "values": []
                    }
                
                morph_tracks[morph_name]["times"].append(frame.timestamp)
                morph_tracks[morph_name]["values"].append(weight)
        
        web_animation["tracks"] = list(morph_tracks.values())
        return web_animation
    
    def _convert_to_generic_format(self, animation: LipSyncAnimation) -> Dict[str, Any]:
        """Convert to generic format"""
        return {
            "animation_id": animation.animation_id,
            "duration": animation.total_duration,
            "frame_rate": animation.frame_rate,
            "avatar_style": animation.avatar_style.value,
            "rendering_engine": animation.rendering_engine.value,
            "frames": [
                {
                    "timestamp": frame.timestamp,
                    "duration": frame.duration,
                    "viseme": frame.viseme.value,
                    "intensity": frame.intensity,
                    "jaw_open": frame.jaw_open,
                    "lip_pucker": frame.lip_pucker,
                    "lip_spread": frame.lip_spread,
                    "tongue_height": frame.tongue_height,
                    "tongue_front": frame.tongue_front,
                    "blend_weights": frame.blend_weights
                }
                for frame in animation.viseme_frames
            ]
        }
    
    def _update_performance_metrics(self, animation: LipSyncAnimation, generation_time: float):
        """Update performance metrics"""
        self.performance_metrics["total_animations"] += 1
        self.performance_metrics["successful_generations"] += 1
        
        # Update average generation time
        total = self.performance_metrics["total_animations"]
        current_avg = self.performance_metrics["average_generation_time"]
        self.performance_metrics["average_generation_time"] = (
            (current_avg * (total - 1) + generation_time) / total
        )
        
        # Update average frame count
        frame_count = len(animation.viseme_frames)
        current_frame_avg = self.performance_metrics["average_frame_count"]
        self.performance_metrics["average_frame_count"] = (
            (current_frame_avg * (total - 1) + frame_count) / total
        )
        
        # Update agent state metrics
        self.state.performance_metrics.update({
            "generation_latency": self.performance_metrics["average_generation_time"],
            "total_animations": self.performance_metrics["total_animations"],
            "average_frame_rate": animation.frame_rate,
            "successful_generations": self.performance_metrics["successful_generations"]
        })
    
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle incoming messages from other agents"""
        try:
            if message.message_type == "lip_sync_generation_request":
                # Handle lip sync generation request
                phonemes = message.payload.get("phonemes", [])
                language = message.payload.get("language", "en")
                avatar_style = message.payload.get("avatar_style", "realistic_3d")
                rendering_engine = message.payload.get("rendering_engine", "unity")
                frame_rate = message.payload.get("frame_rate", 30)
                
                if not phonemes:
                    raise ValueError("phonemes are required")
                
                animation = await self.generate_lip_sync_animation(
                    phonemes, language, avatar_style, rendering_engine, frame_rate
                )
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="lip_sync_generation_response",
                    payload={
                        "animation": self._convert_to_generic_format(animation),
                        "animation_id": animation.animation_id,
                        "total_duration": animation.total_duration,
                        "frame_count": len(animation.viseme_frames),
                        "agent_id": self.agent_id
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "realtime_viseme_request":
                # Handle real-time viseme request
                animation_id = message.payload.get("animation_id")
                timestamp = message.payload.get("timestamp")
                
                if not animation_id or timestamp is None:
                    raise ValueError("animation_id and timestamp are required")
                
                viseme_frame = self.get_realtime_viseme(animation_id, timestamp)
                
                if viseme_frame:
                    frame_data = {
                        "viseme": viseme_frame.viseme.value,
                        "timestamp": viseme_frame.timestamp,
                        "duration": viseme_frame.duration,
                        "intensity": viseme_frame.intensity,
                        "jaw_open": viseme_frame.jaw_open,
                        "lip_pucker": viseme_frame.lip_pucker,
                        "lip_spread": viseme_frame.lip_spread,
                        "tongue_height": viseme_frame.tongue_height,
                        "tongue_front": viseme_frame.tongue_front,
                        "blend_weights": viseme_frame.blend_weights
                    }
                else:
                    frame_data = None
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="realtime_viseme_response",
                    payload={
                        "viseme_frame": frame_data,
                        "agent_id": self.agent_id
                    },
                    correlation_id=message.message_id,
                    priority=message.priority
                )
            
            elif message.message_type == "engine_conversion_request":
                # Handle engine format conversion request
                animation_data = message.payload.get("animation")
                target_engine = message.payload.get("target_engine")
                
                if not animation_data or not target_engine:
                    raise ValueError("animation and target_engine are required")
                
                # Reconstruct animation object (simplified)
                animation = LipSyncAnimation(
                    animation_id=animation_data["animation_id"],
                    viseme_frames=[],  # Would need full reconstruction
                    total_duration=animation_data["duration"],
                    frame_rate=animation_data["frame_rate"],
                    avatar_style=AvatarStyle(animation_data["avatar_style"]),
                    rendering_engine=RenderingEngine(animation_data["rendering_engine"])
                )
                
                converted = self.convert_to_engine_format(animation, target_engine)
                
                return AgentMessage(
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    message_type="engine_conversion_response",
                    payload={
                        "converted_animation": converted,
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
            "cached_animations": len(self.animation_cache)
        }