# updated SQLA schema display to work with pydot 1.0.2
from typing import Union, List
import types
from sqlalchemy import Table, text, ForeignKeyConstraint, Column, MetaData
from sqlalchemy.orm import Mapper, Relationship
from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql.base import PGDialect
import pydot

#from cStringIO import StringIO
#from PIL import Image

__all__ = [
    'create_uml_graph', 'create_schema_graph', 'show_uml_graph',
    'show_schema_graph'
]


def _mk_label(
    mapper: Mapper,
    show_operations: bool,
    show_attributes: bool,
    show_datatypes: bool,
    show_inherited: bool,
    bordersize: float,
) -> str:
    #pylint: disable=too-many-arguments
    """Generate the rendering of a given orm model.

    Args:
        mapper (sqlalchemy.orm.Mapper): mapper for the SqlAlchemy orm class.
        show_operations (bool): whether to show functions defined in the orm.
        show_attributes (bool): whether to show the attributes of the class.
        show_datatypes (bool): Whether to display the type of the columns in the model.
        show_inherited (bool): whether to show inherited columns.
        bordersize (float): thickness of the border lines in the diagram

    Returns:
        str: html string to render the orm model
    """
    html = f'<<TABLE CELLSPACING="0" CELLPADDING="1" BORDER="0" CELLBORDER="{bordersize}" '
    html += f'ALIGN="LEFT"><TR><TD><FONT POINT-SIZE="10">{mapper.class_.__name__}</FONT></TD></TR>'

    def format_col(col):
        colstr = f'+{col.name}'
        if show_datatypes:
            colstr += f' : {col.type.__class__.__name__}'
        return colstr

    if show_attributes:
        if not show_inherited:
            cols = [c for c in mapper.columns if c.table == mapper.tables[0]]
        else:
            cols = mapper.columns
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(
            format_col(col) for col in cols)
    else:
        _ = [
            format_col(col)
            for col in sorted(mapper.columns,
                              key=lambda col: not col.primary_key)
        ]
    if show_operations:
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(
            '%s(%s)' %
            (name, ", ".join(default is _mk_label and (f"{arg}") or (
                f"{arg}={repr(default)}"
            ) for default, arg in zip(
                (func.func_defaults and len(func.func_code.co_varnames) - 1 -
                 (len(func.func_defaults) or 0) or func.func_code.co_argcount -
                 1) * [_mk_label] + list(func.func_defaults or []),
                func.func_code.co_varnames[1:])))
            for name, func in mapper.class_.__dict__.items()
            if isinstance(func, types.FunctionType)
            and func.__module__ == mapper.class_.__module__)
    html += '</TABLE>>'
    return html


def escape(name: str) -> str:
    """Set the name of the object between quotations to avoid reading errors

    Args:
        name (str): name of the object

    Returns:
        str: name of the object between quotations to avoid reading errors
    """
    return f'"{name}"'


def create_uml_graph(
    mappers: List[Mapper],
    show_operations: bool = True,
    show_attributes: bool = True,
    show_inherited: bool = True,
    show_multiplicity_one: bool = False,
    show_datatypes: bool = True,
    linewidth: float = 1.0,
    font: str = "Bitstream-Vera Sans",
) -> pydot.Dot:
    #pylint: disable=too-many-locals,too-many-arguments
    """Create rendering of the orm models associated with the database

    Args:
        mappers (List[sqlalchemy.orm.Mapper]): SqlAlchemy list of mappers of the orm classes.
        show_operations (bool, optional): whether to show functions defined in the orm. \
            Defaults to True.
        show_attributes (bool, optional): whether to show the attributes of the class. \
            Defaults to True.
        show_inherited (bool, optional): whether to show inherited columns. Defaults to True.
        show_multiplicity_one (bool, optional): whether to show the multiplicity as a float or \
            integer. Defaults to False.
        show_datatypes (bool, optional): Whether to display the type of the columns in the model. \
            Defaults to True.
        linewidth (float, optional): thickness of the lines in the diagram. Defaults to 1.0.
        font (str, optional): type of fond to be used for the diagram. \
            Defaults to "Bitstream-Vera Sans".

    Returns:
        pydot.Dot: pydot object with the diagram for the orm models.
    """
    graph = pydot.Dot(
        prog='neato',
        mode="major",
        overlap="0",
        sep="0.01",
        dim="3",
        pack="True",
        ratio=".75",
    )
    relations = set()
    for mapper in mappers:
        graph.add_node(
            pydot.Node(
                escape(mapper.class_.__name__),
                shape="plaintext",
                label=_mk_label(
                    mapper,
                    show_operations,
                    show_attributes,
                    show_datatypes,
                    show_inherited,
                    linewidth,
                ),
                fontname=font,
                fontsize="8.0",
            ))
        if mapper.inherits:
            graph.add_edge(
                pydot.Edge(
                    escape(mapper.inherits.class_.__name__),
                    escape(mapper.class_.__name__),
                    arrowhead='none',
                    arrowtail='empty',
                    style="setlinewidth(%s)" % linewidth,
                    arrowsize=str(linewidth),
                ), )
        for loader in mapper.iterate_properties:
            if isinstance(loader,
                          RelationshipProperty) and loader.mapper in mappers:
                if hasattr(loader, 'reverse_property'):
                    relations.add(frozenset([loader, loader.reverse_property]))
                else:
                    relations.add(frozenset([loader]))

    def multiplicity_indicator(prop: Relationship) -> str:
        """Indicate the multiplicity of a given relationship

        Args:
            prop (sqlalchemy.orm.Relationship): relationship associated with this model

        Returns:
            str: string indicating the multiplicity of the relationship
        """
        if prop.uselist:
            return ' *'
        if hasattr(prop, 'local_side'):
            cols = prop.local_side
        else:
            cols = prop.local_columns
        if any(col.nullable for col in cols):
            return ' 0..1'
        if show_multiplicity_one:
            return ' 1'
        return ''

    def calc_label(src: Relationship) -> str:
        """Generate the label for a given relationship

        Args:
            src (Relationship): relationship associated with this model

        Returns:
            str: relationship label
        """
        return '+' + src.key + multiplicity_indicator(src)

    for relation in relations:
        #if len(loaders) > 2:
        #    raise Exception("Warning: too many loaders for join %s" % join)
        args = {}

        if len(relation) == 2:
            src, dest = relation
            from_name = escape(src.parent.class_.__name__)
            to_name = escape(dest.parent.class_.__name__)

            args['headlabel'] = calc_label(src)

            args['taillabel'] = calc_label(dest)
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'none'
            args['constraint'] = False
        else:
            prop, = relation
            from_name = escape(prop.parent.class_.__name__)
            to_name = escape(prop.mapper.class_.__name__)
            args['headlabel'] = f'+{prop.key}{multiplicity_indicator(prop)}'
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'vee'

        graph.add_edge(
            pydot.Edge(
                from_name,
                to_name,
                fontname=font,
                fontsize="7.0",
                style=f"setlinewidth({linewidth})",
                arrowsize=str(linewidth),
                **args,
            ), )

    return graph


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
    #pylint: disable=too-many-locals,too-many-arguments
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
    use_column_key_attr = hasattr(ForeignKeyConstraint, 'column_keys')
    # sqlalchemy > 1.0 uses column_keys to return list of strings for foreign keys,previously
    # was columns
    if show_column_keys:
        if use_column_key_attr:
            # sqlalchemy > 1.0
            fk_col_names = set(h for f in table.foreign_key_constraints
                               for h in f.columns.keys())
        else:
            # sqlalchemy pre 1.0?
            fk_col_names = set(h.name for f in table.foreign_keys
                               for h in f.constraint.columns)
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
        suffix = '(FK)' if col.name in fk_col_names else '(PK)' if col.name in pk_col_names else ''
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
            _color = format_dict.get(
                "color") if "color" in format_dict else "initial"
            _point_size = float(format_dict["fontsize"]
                                ) if "fontsize" in format_dict else "initial"
            _bold = "<B>" if format_dict.get("bold") else ""
            _italic = "<I>" if format_dict.get("italics") else ""
            _text = f'<FONT COLOR="{_color}" '
            _text += f'POINT-SIZE="{_point_size}">'
            _text += f'{_bold}{_italic}{obj_name}{"</I>" if format_dict.get("italics") else ""}'
            _text += f'{"</B>" if format_dict.get("bold") else ""}</FONT>'

            return _text
        return obj_name

    schema_str = ""
    if show_schema_name and hasattr(table,
                                    'schema') and table.schema is not None:
        # Build string for schema name, empty if show_schema_name is False
        schema_str = format_name(table.schema, format_schema_name)
    table_str = format_name(table.name, format_table_name)

    # Assemble table header
    html = '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"><TR><TD ALIGN="CENTER">'
    html += f'{schema_str}{"." if show_schema_name else ""}{table_str}</TD></TR>'
    html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'

    html += ''.join(
        f'<TR><TD ALIGN="LEFT" PORT="{col.name}">{format_col_str(col)}</TD></TR>'
        for col in table.columns)
    if isinstance(engine, Engine) and isinstance(engine.engine.dialect,
                                                 PGDialect):
        # postgres engine doesn't reflect indexes
        with engine.connect() as connection:
            indexes = dict((key, value) for key, value in connection.execute(
                text(
                    f"SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '{table.name}'"
                )))
            if indexes and show_indexes:
                html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'
                for value in indexes.values():
                    i_label = 'UNIQUE ' if 'UNIQUE' in value else 'INDEX '
                    i_label += value[value.index('('):]
                    html += f'<TR><TD ALIGN="LEFT">{i_label}</TD></TR>'
    html += '</TABLE>>'
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
    rankdir: str = 'TB',
    show_column_keys: bool = False,
    restrict_tables: Union[List[str], None] = None,
    show_schema_name: bool = False,
    format_schema_name: Union[dict, None] = None,
    format_table_name: Union[dict, None] = None,
) -> pydot.Dot:
    #pylint: disable=too-many-locals,too-many-arguments
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
        font (str, optional): _description_. Defaults to "Bitstream-Vera Sans".
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

    relation_kwargs = {'fontsize': "7.0", 'dir': 'both'}
    relation_kwargs.update(relation_options)

    if not metadata and not tables:
        raise ValueError("You need to specify at least tables or metadata")

    if metadata and not tables:
        metadata.reflect(bind=engine)
        tables = metadata.tables.values()

    _accepted_keys = {'color', 'fontsize', 'italics', 'bold'}

    # check if unexpected keys were used in format_schema_name param
    if format_schema_name is not None and len(
            set(format_schema_name.keys()).difference(_accepted_keys)) > 0:
        raise KeyError(
            'Unrecognized keys were used in dict provided for `format_schema_name` parameter'
        )
    # check if unexpected keys were used in format_table_name param
    if format_table_name is not None and len(
            set(format_table_name.keys()).difference(_accepted_keys)) > 0:
        raise KeyError(
            'Unrecognized keys were used in dict provided for `format_table_name` parameter'
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
        restrict_tables = set(t.name.lower() for t in tables)
    else:
        restrict_tables = set(t.lower() for t in restrict_tables)
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
            ), )

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
                taillabel='+ %s' % fk.parent.name,
                arrowhead=is_inheritance and 'none' or 'odot',
                arrowtail=(fk.parent.primary_key or fk.parent.unique)
                and 'empty' or 'crow',
                fontname=font,
                #samehead=fk.column.name, sametail=fk.parent.name,
                *edge,
                **relation_kwargs)
            graph.add_edge(graph_edge)

# not sure what this part is for, doesn't work with pydot 1.0.2
#            graph_edge.parent_graph = graph.parent_graph
#            if table.name not in [e.get_source() for e in graph.get_edge_list()]:
#                graph.edge_src_list.append(table.name)
#            if fk.column.table.name not in graph.edge_dst_list:
#                graph.edge_dst_list.append(fk.column.table.name)
#            graph.sorted_graph_elements.append(graph_edge)
    return graph


#def show_uml_graph(*args, **kwargs):
#    iostream = StringIO(create_uml_graph(*args, **kwargs).create_png())
#    Image.open(iostream).show(command=kwargs.get('command', 'gwenview'))

#def show_schema_graph(*args, **kwargs):
#    iostream = StringIO(create_schema_graph(*args, **kwargs).create_png())
#    Image.open(iostream).show(command=kwargs.get('command', 'gwenview'))
