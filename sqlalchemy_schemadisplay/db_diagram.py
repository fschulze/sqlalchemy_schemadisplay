"""Set of functions to generate the diagram of the actual database"""
from typing import List, Union

import pydot
from sqlalchemy import Column, ForeignKeyConstraint, MetaData, Table, text
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Engine


def _render_table_html(
    table: Table,
    engine: Engine,
    show_indexes: bool,
    show_datatypes: bool,
    show_column_keys: bool,
    show_schema_name: bool,
    format_schema_name: dict,
    format_table_name: dict,
) -> str:
    # pylint: disable=too-many-locals,too-many-arguments
    """Create a rendering of a table in the database

    Args:
        table (sqlalchemy.Table): SqlAlchemy table which is going to be rendered.
        engine (sqlalchemy.engine.Engine): SqlAlchemy database engine to connect to the database.
        show_indexes (bool): Whether to display the index column in the table
        show_datatypes (bool):  Whether to display the type of the columns in the table
        show_column_keys (bool): If true then add a PK/FK suffix to columns names that \
            are primary and foreign keys
        show_schema_name (bool): If true, then prepend '<schema name>.' to the table  \
            name resulting in '<schema name>.<table name>'
        format_schema_name (dict): If provided, allowed keys include: \
            'color' (hex color code incl #), 'fontsize' as a float, and 'bold' and 'italics' \
                as bools
        format_table_name (dict): If provided, allowed keys include: \
            'color' (hex color code incl #), 'fontsize' as a float, and 'bold' and 'italics' as \
                bools

    Returns:
        str: html string with the rendering of the table
    """
    # add in (PK) OR (FK) suffixes to column names that are considered to be primary key or
    # foreign key
    use_column_key_attr = hasattr(ForeignKeyConstraint, "column_keys")
    # sqlalchemy > 1.0 uses column_keys to return list of strings for foreign keys,previously
    # was columns
    if show_column_keys:
        if use_column_key_attr:
            # sqlalchemy > 1.0
            fk_col_names = {
                h for f in table.foreign_key_constraints for h in f.columns.keys()
            }
        else:
            # sqlalchemy pre 1.0?
            fk_col_names = {
                h.name for f in table.foreign_keys for h in f.constraint.columns
            }
        # fk_col_names = set([h for f in table.foreign_key_constraints for h in f.columns.keys()])
        pk_col_names = set(list(table.primary_key.columns.keys()))
    else:
        fk_col_names = set()
        pk_col_names = set()

    def format_col_type(col: Column) -> str:
        """Get the type of the column as a string

        Args:
            col (Column): SqlAlchemy column of the table that is being rendered

        Returns:
            str: column type
        """
        try:
            return col.type.get_col_spec()
        except (AttributeError, NotImplementedError):
            return str(col.type)

    def format_col_str(col: Column) -> str:
        """Generate the column name so that it takes into account any possible suffix.

        Args:
            col (sqlalchemy.Column): SqlAlchemy column of the table that is being rendered

        Returns:
            str: name of the column with the appropriate suffixes
        """
        # add in (PK) OR (FK) suffixes to column names that are considered to be primary key
        # or foreign key
        suffix = (
            "(FK)"
            if col.name in fk_col_names
            else "(PK)"
            if col.name in pk_col_names
            else ""
        )
        if show_datatypes:
            return f"- {col.name + suffix} : {format_col_type(col)}"
        return f"- {col.name + suffix}"

    def format_name(obj_name: str, format_dict: Union[dict, None]) -> str:
        """Format the name of the object so that it is rendered differently.

        Args:
            obj_name (str): name of the object being rendered
            format_dict (Union[dict,None]): dictionary with the rendering options. \
                If None nothing is done

        Returns:
            str: formatted name of the object
        """
        # Check if format_dict was provided
        if format_dict is not None:
            # Should color be checked?
            # Could use  /^#([A-Fa-f0-9]{8}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/
            _color = format_dict.get("color") if "color" in format_dict else "initial"
            _point_size = (
                float(format_dict["fontsize"])
                if "fontsize" in format_dict
                else "initial"
            )
            _bold = "<B>" if format_dict.get("bold") else ""
            _italic = "<I>" if format_dict.get("italics") else ""
            _text = f'<FONT COLOR="{_color}" '
            _text += f'POINT-SIZE="{_point_size}">'
            _text += f'{_bold}{_italic}{obj_name}{"</I>" if format_dict.get("italics") else ""}'
            _text += f'{"</B>" if format_dict.get("bold") else ""}</FONT>'

            return _text
        return obj_name

    schema_str = ""
    if show_schema_name and hasattr(table, "schema") and table.schema is not None:
        # Build string for schema name, empty if show_schema_name is False
        schema_str = format_name(table.schema, format_schema_name)
    table_str = format_name(table.name, format_table_name)

    # Assemble table header
    html = '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"><TR><TD ALIGN="CENTER">'
    html += f'{schema_str}{"." if show_schema_name else ""}{table_str}</TD></TR>'
    html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'

    html += "".join(
        f'<TR><TD ALIGN="LEFT" PORT="{col.name}">{format_col_str(col)}</TD></TR>'
        for col in table.columns
    )
    if isinstance(engine, Engine) and isinstance(engine.engine.dialect, PGDialect):
        # postgres engine doesn't reflect indexes
        with engine.connect() as connection:
            indexes = {
                key: value
                for key, value in connection.execute(
                    text(
                        f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '{table.name}'"
                    )
                )
            }
            if indexes and show_indexes:
                html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'
                for value in indexes.values():
                    i_label = "UNIQUE " if "UNIQUE" in value else "INDEX "
                    i_label += value[value.index("(") :]
                    html += f'<TR><TD ALIGN="LEFT">{i_label}</TD></TR>'
    html += "</TABLE>>"
    return html


def create_schema_graph(
    engine: Engine,
    tables: List[Table] = None,
    metadata: MetaData = None,
    show_indexes: bool = True,
    show_datatypes: bool = True,
    font: str = "Bitstream-Vera Sans",
    concentrate: bool = True,
    relation_options: Union[dict, None] = None,
    rankdir: str = "TB",
    show_column_keys: bool = False,
    restrict_tables: Union[List[str], None] = None,
    show_schema_name: bool = False,
    format_schema_name: Union[dict, None] = None,
    format_table_name: Union[dict, None] = None,
) -> pydot.Dot:
    # pylint: disable=too-many-locals,too-many-arguments
    """Create a diagram for the database schema.

    Args:
        engine (sqlalchemy.engine.Engine): SqlAlchemy database engine to connect to the database.
        tables (List[sqlalchemy.Table], optional): SqlAlchemy database tables. Defaults to None.
        metadata (sqlalchemy.MetaData, optional): SqlAlchemy `MetaData` with reference to related \
            tables. Defaults to None.
        show_indexes (bool, optional): Whether to display the index column in the table. \
            Defaults to True.
        show_datatypes (bool, optional): Whether to display the type of the columns in the table. \
            Defaults to True.
        font (str, optional): font to be used in the diagram. Defaults to "Bitstream-Vera Sans".
        concentrate (bool, optional): Specifies if multi-edges should be merged into a single edge \
            & partially parallel edges to share overlapping path. Passed to `pydot.Dot` object. \
                Defaults to True.
        relation_options (Union[dict, None], optional): kwargs passed to pydot.Edge init.  \
            Most attributes in pydot.EDGE_ATTRIBUTES are viable options. A few values are set \
                programmatically. Defaults to None.
        rankdir (str, optional): Sets direction of graph layout.  Passed to `pydot.Dot` object.  \
            Options are 'TB' (top to bottom), 'BT' (bottom to top), 'LR' (left to right), \
                'RL' (right to left). Defaults to 'TB'.
        show_column_keys (bool, optional): If true then add a PK/FK suffix to columns names that \
            are primary and foreign keys. Defaults to False.
        restrict_tables (Union[List[str], optional):  Restrict the graph to only consider tables \
            whose name are defined `restrict_tables`. Defaults to None.
        show_schema_name (bool, optional): If true, then prepend '<schema name>.' to the table  \
            name resulting in '<schema name>.<table name>'. Defaults to False.
        format_schema_name (Union[dict, None], optional): If provided, allowed keys include: \
            'color' (hex color code incl #), 'fontsize' as a float, and 'bold' and 'italics' \
                as bools. Defaults to None.
        format_table_name (Union[dict, None], optional): If provided, allowed keys include: \
            'color' (hex color code incl #), 'fontsize' as a float, and 'bold' and 'italics' as \
                bools. Defaults to None.

    Raises:
        ValueError: One needs to specify either the metadata or the tables
        KeyError: raised when unexpected keys are given to `format_schema_name` or \
            `format_table_name`
    Returns:
        pydot.Dot: pydot object with the schema of the database
    """

    if not relation_options:
        relation_options = {}

    relation_kwargs = {"fontsize": "7.0", "dir": "both"}
    relation_kwargs.update(relation_options)

    if not metadata and not tables:
        raise ValueError("You need to specify at least tables or metadata")

    if metadata and not tables:
        metadata.reflect(bind=engine)
        tables = metadata.tables.values()

    _accepted_keys = {"color", "fontsize", "italics", "bold"}

    # check if unexpected keys were used in format_schema_name param
    if (
        format_schema_name is not None
        and len(set(format_schema_name.keys()).difference(_accepted_keys)) > 0
    ):
        raise KeyError(
            "Unrecognized keys were used in dict provided for `format_schema_name` parameter"
        )
    # check if unexpected keys were used in format_table_name param
    if (
        format_table_name is not None
        and len(set(format_table_name.keys()).difference(_accepted_keys)) > 0
    ):
        raise KeyError(
            "Unrecognized keys were used in dict provided for `format_table_name` parameter"
        )

    graph = pydot.Dot(
        prog="dot",
        mode="ipsep",
        overlap="ipsep",
        sep="0.01",
        concentrate=str(concentrate),
        rankdir=rankdir,
    )
    if restrict_tables is None:
        restrict_tables = {t.name.lower() for t in tables}
    else:
        restrict_tables = {t.lower() for t in restrict_tables}
    tables = [t for t in tables if t.name.lower() in restrict_tables]
    for table in tables:

        graph.add_node(
            pydot.Node(
                str(table.name),
                shape="plaintext",
                label=_render_table_html(
                    table=table,
                    engine=engine,
                    show_indexes=show_indexes,
                    show_datatypes=show_datatypes,
                    show_column_keys=show_column_keys,
                    show_schema_name=show_schema_name,
                    format_schema_name=format_schema_name,
                    format_table_name=format_table_name,
                ),
                fontname=font,
                fontsize="7.0",
            ),
        )

    for table in tables:
        for fk in table.foreign_keys:
            if fk.column.table not in tables:
                continue
            edge = [table.name, fk.column.table.name]
            is_inheritance = fk.parent.primary_key and fk.column.primary_key
            if is_inheritance:
                edge = edge[::-1]
            graph_edge = pydot.Edge(
                headlabel="+ %s" % fk.column.name,
                taillabel="+ %s" % fk.parent.name,
                arrowhead=is_inheritance and "none" or "odot",
                arrowtail=(fk.parent.primary_key or fk.parent.unique)
                and "empty"
                or "crow",
                fontname=font,
                # samehead=fk.column.name, sametail=fk.parent.name,
                *edge,
                **relation_kwargs,
            )
            graph.add_edge(graph_edge)

    # not sure what this part is for, doesn't work with pydot 1.0.2
    #            graph_edge.parent_graph = graph.parent_graph
    #            if table.name not in [e.get_source() for e in graph.get_edge_list()]:
    #                graph.edge_src_list.append(table.name)
    #            if fk.column.table.name not in graph.edge_dst_list:
    #                graph.edge_dst_list.append(fk.column.table.name)
    #            graph.sorted_graph_elements.append(graph_edge)
    return graph
