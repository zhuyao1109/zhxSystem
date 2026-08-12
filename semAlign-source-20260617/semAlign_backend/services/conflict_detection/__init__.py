# 修改后
from .clause_aligner import ClauseAligner
from .conflict_detector import EnhancedConflictDetector as ConflictDetector
from .similarity_calculator import SimilarityCalculator

__all__ = ['ClauseAligner', 'ConflictDetector', 'SimilarityCalculator']