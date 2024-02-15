"""Package for the generation of diagrams based on SQLAlchemy ORM models and or the database itself"""
from .db_diagram import create_schema_graph
from .model_diagram import create_uml_graph
from .utils import show_schema_graph, show_uml_graph

__version__ = "2.0"

__all__ = (
    "create_schema_graph",
    "create_uml_graph",
    "show_schema_graph",
    "show_uml_graph",
)
