from enum import Enum

class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowMode(str, Enum): #TODO: 지울까..
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    FEEDBACK_LOOP = "feedback_loop"
    
class TaskStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
        
class DataSourceType(str, Enum):
    RDB_DATA = "internal_data"
    WEB_DATA = "web_search"
    VDB_DATA = "vector_db"
