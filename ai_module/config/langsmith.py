"""LangSmith tracing configuration for Narrative Investment."""

import os
from pathlib import Path
from typing import Optional
from functools import wraps

from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def init_langsmith(
    project_name: str = "narrative-investment",
    environment: str = None,
) -> bool:
    """
    Initialize LangSmith tracing.
    
    Args:
        project_name: LangSmith project name
        environment: Environment tag (dev/staging/prod)
        
    Returns:
        True if initialized successfully
    """
    api_key = os.getenv("LANGSMITH_API_KEY", "")
    
    if not api_key:
        print("⚠️ LANGSMITH_API_KEY not set - tracing disabled")
        return False
    
    # Set environment variables for LangChain tracing
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGCHAIN_API_KEY"] = api_key
    
    if environment:
        os.environ["LANGCHAIN_TAGS"] = f"env:{environment}"
    
    print(f"✅ LangSmith tracing initialized")
    print(f"   Project: {project_name}")
    print(f"   Environment: {environment or 'default'}")
    
    return True


def get_langsmith_client():
    """Get LangSmith client for custom operations."""
    try:
        from langsmith import Client
        return Client()
    except ImportError:
        print("⚠️ langsmith package not installed")
        return None
    except Exception as e:
        print(f"⚠️ Failed to create LangSmith client: {e}")
        return None


def trace_function(
    run_type: str = "chain",
    name: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Decorator to trace a function with LangSmith.
    
    Args:
        run_type: Type of run (chain/llm/tool/retriever/embedding)
        name: Custom name for the trace
        metadata: Additional metadata to attach
    
    Usage:
        @trace_function(run_type="chain", name="my_chain")
        def my_function(input):
            return output
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from langsmith import traceable
                
                traced_func = traceable(
                    run_type=run_type,
                    name=name or func.__name__,
                    metadata=metadata or {},
                )(func)
                
                return traced_func(*args, **kwargs)
                
            except ImportError:
                # LangSmith not available, run without tracing
                return func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ Tracing error: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_async_function(
    run_type: str = "chain",
    name: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Decorator to trace an async function with LangSmith.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                from langsmith import traceable
                
                traced_func = traceable(
                    run_type=run_type,
                    name=name or func.__name__,
                    metadata=metadata or {},
                )(func)
                
                return await traced_func(*args, **kwargs)
                
            except ImportError:
                return await func(*args, **kwargs)
            except Exception as e:
                print(f"⚠️ Tracing error: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def create_feedback(
    run_id: str,
    key: str,
    score: float,
    comment: Optional[str] = None,
) -> bool:
    """
    Create feedback for a LangSmith run.
    
    Args:
        run_id: The run ID to provide feedback for
        key: Feedback key (e.g., "correctness", "helpfulness")
        score: Score value (0-1)
        comment: Optional comment
        
    Returns:
        True if feedback was created successfully
    """
    client = get_langsmith_client()
    if not client:
        return False
    
    try:
        client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
        return True
    except Exception as e:
        print(f"⚠️ Failed to create feedback: {e}")
        return False


def get_run_url(run_id: str) -> Optional[str]:
    """Get the LangSmith URL for a run."""
    project = os.getenv("LANGCHAIN_PROJECT", "narrative-investment")
    return f"https://smith.langchain.com/o/default/projects/p/{project}/r/{run_id}"


# Configuration for different components
TRACING_CONFIG = {
    "tutor": {
        "project": "narrative-investment-tutor",
        "tags": ["tutor", "chat"],
        "metadata": {
            "service": "ai-tutor",
            "version": "0.1.0",
        },
    },
    "search": {
        "project": "narrative-investment-search",
        "tags": ["search", "perplexity"],
        "metadata": {
            "service": "case-search",
            "version": "0.1.0",
        },
    },
    "pipeline": {
        "project": "narrative-investment-pipeline",
        "tags": ["pipeline", "data"],
        "metadata": {
            "service": "data-pipeline",
            "version": "0.1.0",
        },
    },
}


def init_component_tracing(component: str) -> bool:
    """
    Initialize tracing for a specific component.
    
    Args:
        component: Component name (tutor/search/pipeline)
        
    Returns:
        True if initialized successfully
    """
    if component not in TRACING_CONFIG:
        print(f"⚠️ Unknown component: {component}")
        return init_langsmith()
    
    config = TRACING_CONFIG[component]
    
    result = init_langsmith(
        project_name=config["project"],
        environment=os.getenv("ENVIRONMENT", "dev"),
    )
    
    if result:
        # Set component-specific tags
        tags = config.get("tags", [])
        if tags:
            os.environ["LANGCHAIN_TAGS"] = ",".join(tags)
    
    return result


# Auto-initialize on import if API key is set
if os.getenv("LANGSMITH_API_KEY"):
    init_langsmith()
