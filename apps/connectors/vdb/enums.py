from enum import Enum


class RetrievalMode(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
