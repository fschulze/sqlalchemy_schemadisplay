"""
Set of functions to display the database diagrams generated.
"""
from io import StringIO

from PIL import Image

from sqlalchemy_schemadisplay import create_schema_graph, create_uml_graph


def show_uml_graph(*args, **kwargs):
    """
    Show the SQLAlchemy ORM diagram generated.
    """
    iostream = StringIO(
        create_uml_graph(*args, **kwargs).create_png()
    )  # pylint: disable=no-member
    Image.open(iostream).show(command=kwargs.get("command", "gwenview"))


def show_schema_graph(*args, **kwargs):
    """
    Show the database diagram generated
    """
    iostream = StringIO(
        create_schema_graph(*args, **kwargs).create_png()
    )  # pylint: disable=no-member
    Image.open(iostream).show(command=kwargs.get("command", "gwenview"))
