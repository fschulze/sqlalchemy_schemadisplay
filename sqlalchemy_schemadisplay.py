# updated SQLA schema display to work with pydot 1.0.2

from sqlalchemy.orm.properties import RelationshipProperty
from sqlalchemy.orm import sync
import pydot
import types

__all__ = ['create_uml_graph', 'create_schema_graph', 'show_uml_graph', 'show_schema_graph']

def _mk_label(mapper, show_operations, show_attributes, show_datatypes, show_inherited, bordersize):
    html = '<<TABLE CELLSPACING="0" CELLPADDING="1" BORDER="0" CELLBORDER="%d" ALIGN="LEFT"><TR><TD><FONT POINT-SIZE="10">%s</FONT></TD></TR>' % (bordersize, mapper.class_.__name__)
    def format_col(col):
        colstr = '+%s' % (col.name)
        if show_datatypes:
            colstr += ' : %s' % (col.type.__class__.__name__)
        return colstr

    if show_attributes:
        if not show_inherited:
            cols = [c for c in mapper.columns if c.table == mapper.tables[0]]
        else:
            cols = mapper.columns
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(format_col(col) for col in cols)
    else:
        [format_col(col) for col in sorted(mapper.columns, key=lambda col:not col.primary_key)]
    if show_operations:
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(
            '%s(%s)' % (name,", ".join(default is _mk_label and ("%s") % arg or ("%s=%s" % (arg,repr(default))) for default,arg in
                zip((func.func_defaults and len(func.func_code.co_varnames)-1-(len(func.func_defaults) or 0) or func.func_code.co_argcount-1)*[_mk_label]+list(func.func_defaults or []), func.func_code.co_varnames[1:])
            ))
            for name,func in mapper.class_.__dict__.items() if isinstance(func, types.FunctionType) and func.__module__ == mapper.class_.__module__
        )
    html+= '</TABLE>>'
    return html


def escape(name):
    return '"%s"' % name


def create_uml_graph(mappers, show_operations=True, show_attributes=True, show_inherited=True, show_multiplicity_one=False, show_datatypes=True, linewidth=1.0, font="Bitstream-Vera Sans"):
    graph = pydot.Dot(prog='neato',mode="major",overlap="0", sep="0.01",dim="3", pack="True", ratio=".75")
    relations = set()
    for mapper in mappers:
        graph.add_node(pydot.Node(escape(mapper.class_.__name__),
            shape="plaintext", label=_mk_label(mapper, show_operations, show_attributes, show_datatypes, show_inherited, linewidth),
            fontname=font, fontsize="8.0",
        ))
        if mapper.inherits:
            graph.add_edge(pydot.Edge(escape(mapper.inherits.class_.__name__),escape(mapper.class_.__name__),
                arrowhead='none',arrowtail='empty', style="setlinewidth(%s)" % linewidth, arrowsize=str(linewidth)))
        for loader in mapper.iterate_properties:
            if isinstance(loader, RelationshipProperty) and loader.mapper in mappers:
                if hasattr(loader, 'reverse_property'):
                    relations.add(frozenset([loader, loader.reverse_property]))
                else:
                    relations.add(frozenset([loader]))

    for relation in relations:
        #if len(loaders) > 2:
        #    raise Exception("Warning: too many loaders for join %s" % join)
        args = {}
        def multiplicity_indicator(prop):
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

        if len(relation) == 2:
            src, dest = relation
            from_name = escape(src.parent.class_.__name__)
            to_name = escape(dest.parent.class_.__name__)

            def calc_label(src,dest):
                return '+' + src.key + multiplicity_indicator(src)
            args['headlabel'] = calc_label(src,dest)

            args['taillabel'] = calc_label(dest,src)
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'none'
            args['constraint'] = False
        else:
            prop, = relation
            from_name = escape(prop.parent.class_.__name__)
            to_name = escape(prop.mapper.class_.__name__)
            args['headlabel'] = '+%s%s' % (prop.key, multiplicity_indicator(prop))
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'vee'

        graph.add_edge(pydot.Edge(from_name,to_name,
            fontname=font, fontsize="7.0", style="setlinewidth(%s)"%linewidth, arrowsize=str(linewidth),
            **args)
        )

    return graph

from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy import Table, text, ForeignKeyConstraint

def _render_table_html(table, metadata, show_indexes, show_datatypes, show_column_keys):
    # add in (PK) OR (FK) suffixes to column names that are considered to be primary key or foreign key
    use_column_key_attr = hasattr(ForeignKeyConstraint, 'column_keys')  # sqlalchemy > 1.0 uses column_keys to return list of strings for foreign keys, previously was columns
    if show_column_keys:
        if (use_column_key_attr):
            # sqlalchemy > 1.0
            fk_col_names = set([h for f in table.foreign_key_constraints for h in f.columns.keys()])
        else:
            # sqlalchemy pre 1.0?
            fk_col_names = set([h.name for f in table.foreign_keys for h in f.constraint.columns])
        # fk_col_names = set([h for f in table.foreign_key_constraints for h in f.columns.keys()])
        pk_col_names = set([f for f in table.primary_key.columns.keys()])
    else:
        fk_col_names = set()
        pk_col_names = set()

    def format_col_type(col):
        try:
            return col.type.get_col_spec()
        except (AttributeError, NotImplementedError):
            return str(col.type)
    def format_col_str(col):
         # add in (PK) OR (FK) suffixes to column names that are considered to be primary key or foreign key
         suffix = '(FK)' if col.name in fk_col_names else '(PK)' if col.name in pk_col_names else ''
         if show_datatypes:
             return "- %s : %s" % (col.name + suffix, format_col_type(col))
         else:
             return "- %s" % (col.name + suffix)
    html = '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"><TR><TD ALIGN="CENTER">%s</TD></TR><TR><TD BORDER="1" CELLPADDING="0"></TD></TR>' % table.name

    html += ''.join('<TR><TD ALIGN="LEFT" PORT="%s">%s</TD></TR>' % (col.name, format_col_str(col)) for col in table.columns)
    if metadata.bind and isinstance(metadata.bind.dialect, PGDialect):
        # postgres engine doesn't reflect indexes
        indexes = dict((name,defin) for name,defin in metadata.bind.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '%s'" % table.name)))
        if indexes and show_indexes:
            html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'
            for index, defin in indexes.items():
                ilabel = 'UNIQUE' in defin and 'UNIQUE ' or 'INDEX '
                ilabel += defin[defin.index('('):]
                html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % ilabel
    html += '</TABLE>>'
    return html

def create_schema_graph(tables=None, metadata=None, show_indexes=True, show_datatypes=True, font="Bitstream-Vera Sans",
    concentrate=True, relation_options={}, rankdir='TB', show_column_keys=False, restrict_tables=None):
    """
    Args:
      show_column_keys (boolean, default=False): If true then add a PK/FK suffix to columns names that are primary and foreign keys
      restrict_tables (None or list of strings): Restrict the graph to only consider tables whose name are defined restrict_tables
    """

    relation_kwargs = {
        'fontsize':"7.0"
    }
    relation_kwargs.update(relation_options)

    if metadata is None and tables is not None and len(tables):
        metadata = tables[0].metadata
    elif tables is None and metadata is not None:
        if not len(metadata.tables):
            metadata.reflect()
        tables = metadata.tables.values()
    else:
        raise ValueError("You need to specify at least tables or metadata")

    graph = pydot.Dot(prog="dot",mode="ipsep",overlap="ipsep",sep="0.01",concentrate=str(concentrate), rankdir=rankdir)
    if restrict_tables is None:
        restrict_tables = set([t.name.lower() for t in tables])
    else:
        restrict_tables = set([t.lower() for t in restrict_tables])
    tables = [t for t in tables if t.name in restrict_tables]
    for table in tables:

        graph.add_node(pydot.Node(str(table.name),
            shape="plaintext",
            label=_render_table_html(table, metadata, show_indexes, show_datatypes, show_column_keys),
            fontname=font, fontsize="7.0"
        ))

    for table in tables:
        for fk in table.foreign_keys:
            if fk.column.table not in tables:
                continue
            edge = [table.name, fk.column.table.name]
            is_inheritance = fk.parent.primary_key and fk.column.primary_key
            if is_inheritance:
                edge = edge[::-1]
            graph_edge = pydot.Edge(
                dir='both',
                headlabel="+ %s"%fk.column.name, taillabel='+ %s'%fk.parent.name,
                arrowhead=is_inheritance and 'none' or 'odot' ,
                arrowtail=(fk.parent.primary_key or fk.parent.unique) and 'empty' or 'crow' ,
                fontname=font,
                #samehead=fk.column.name, sametail=fk.parent.name,
                *edge, **relation_kwargs
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

def show_uml_graph(*args, **kwargs):
    from cStringIO import StringIO
    from PIL import Image
    iostream = StringIO(create_uml_graph(*args, **kwargs).create_png())
    Image.open(iostream).show(command=kwargs.get('command','gwenview'))

def show_schema_graph(*args, **kwargs):
    from cStringIO import StringIO
    from PIL import Image
    iostream = StringIO(create_schema_graph(*args, **kwargs).create_png())
    Image.open(iostream).show(command=kwargs.get('command','gwenview'))
