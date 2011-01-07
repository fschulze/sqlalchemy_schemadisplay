from sqlalchemy.orm.properties import PropertyLoader
from sqlalchemy.orm import sync
import pydot
import types

__all__ = ['create_uml_graph', 'create_schema_graph', 'show_uml_graph', 'show_schema_graph']

def _mk_label(mapper, show_operations, show_attributes, show_datatypes, bordersize):
    html = '<<TABLE CELLSPACING="0" CELLPADDING="1" BORDER="0" CELLBORDER="%d" BALIGN="LEFT"><TR><TD><FONT POINT-SIZE="10">%s</FONT></TD></TR>' % (bordersize, mapper.class_.__name__)
    def format_col(col):
        colstr = '+%s' % (col.name)
        if show_datatypes:
            colstr += ' : %s' % (col.type.__class__.__name__)
        return colstr
            
    if show_attributes:
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(format_col(col) for col in sorted(mapper.columns, key=lambda col:not col.primary_key))
    else:
        [format_col(col) for col in sorted(mapper.columns, key=lambda col:not col.primary_key)]
    if show_operations:
        html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % '<BR ALIGN="LEFT"/>'.join(
            '%s(%s)' % (name,", ".join(default is _mk_label and ("%s") % arg or ("%s=%s" % (arg,repr(default))) for default,arg in 
                zip((func.func_defaults and len(func.func_code.co_varnames)-1-(len(func.func_defaults) or 0))*[_mk_label]+list(func.func_defaults or []), func.func_code.co_varnames[1:])
            ))
            for name,func in mapper.class_.__dict__.items() if isinstance(func, types.FunctionType) and func.__module__ == mapper.class_.__module__
        )
    html+= '</TABLE>>'
    return html


def create_uml_graph(mappers, show_operations=True, show_attributes=True, show_multiplicity_one=False, show_datatypes=True, linewidth=1.0, font="Bitstream-Vera Sans"):
    graph = pydot.Dot(prog='neato',mode="major",overlap="0",sep=0.01,pack=True,dim=3)
    relations = []
    for mapper in mappers:
        graph.add_node(pydot.Node(mapper.class_.__name__,
            shape="plaintext", label=_mk_label(mapper, show_operations, show_attributes, show_datatypes, linewidth),
            fontname=font, fontsize=8.0,
        ))
        if mapper.inherits:
            graph.add_edge(pydot.Edge(mapper.inherits.class_.__name__,mapper.class_.__name__,
                arrowhead='none',arrowtail='empty', style="setlinewidth(%s)" % linewidth, arrowsize=linewidth))
        for from_property, loader in mapper.properties.items():
            if isinstance(loader, PropertyLoader) and loader.select_mapper in mappers:
                lcollection = False
                for join, loaders in relations:
                    if ((isinstance(join,tuple) and (
                        join[0].compare(loader.primaryjoin) and join[1].compare(loader.secondaryjoin)
                                or
                        join[1].compare(loader.primaryjoin) and join[0].compare(loader.secondaryjoin)
                        ))
                            or loader.primaryjoin.compare(join)):
                        lcollection = loaders
                if not lcollection:
                    lcollection = []
                    relations.append((not loader.secondaryjoin and loader.primaryjoin or (loader.primaryjoin,loader.secondaryjoin),lcollection))
                lcollection.append((from_property,loader))
    for join, loaders in relations:
        if len(loaders) > 2:
            raise Exception("Warning: too many loaders for join %s" % join)
        args = {}
        if len(loaders) == 1:
            from_ = loaders[0][1].parent.class_
            to = loaders[0][1].argument
            args['headlabel'] = "+%s" % loaders[0][0]
            if loaders[0][1].direction in (sync.ONETOMANY, sync.MANYTOMANY):
                args['headlabel'] += " *"
            elif any(col.nullable for col in loaders[0][1].remote_side):
                args['headlabel'] += " 0..1"
            elif show_multiplicity_one:
                args['headlabel'] += " 1"
            if loaders[0][1].direction in (sync.MANYTOONE, sync.MANYTOMANY):
                args['taillabel'] = "*"
            elif show_multiplicity_one:
                args['taillabel'] = " 1"
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'vee'
        else:
            if loaders[0][1].parent.class_ != loaders[1][1].argument or loaders[1][1].parent.class_ != loaders[0][1].argument:
                raise Exception("A merged join %s has more than two associated classes %s" % (join,
                    ", ".join(cls.__name__ for cls in set([
                        loaders[0][1].parent.class_, loaders[1][1].argument,
                        loaders[1][1].parent.class_, loaders[0][1].argument
                    ]))
                ))
            from_ = loaders[0][1].argument
            to = loaders[1][1].argument
            args['headlabel'] = "+%s" % loaders[1][0]
            args['taillabel'] = "+%s" % loaders[0][0]
            if loaders[1][1].uselist:
                args['headlabel'] += " *"
            elif any(col.nullable for col in loaders[0][1].remote_side):
                args['headlabel'] += " 0..1"
            elif show_multiplicity_one:
                args['headlabel'] += " 1"
            if loaders[0][1].uselist:
                args['taillabel'] += " *"
            elif any(col.nullable for col in loaders[1][1].remote_side):
                args['taillabel'] += " 0..1"
            elif show_multiplicity_one:
                args['taillabel'] += " 1"
            args['constraint'] = False
            args['arrowtail'] = 'none'
            args['arrowhead'] = 'none'
        graph.add_edge(pydot.Edge(from_.__name__,to.__name__,
            fontname=font, fontsize=7.0, style="setlinewidth(%s)"%linewidth, arrowsize=linewidth,
            **args)
        )
    return graph

from sqlalchemy.databases.postgres import PGDialect
from sqlalchemy import Table, text

def _render_table_html(table, metadata, show_indexes, show_datatypes):
    def format_col_type(col):
        try:
            return col.type.get_col_spec()
        except NotImplementedError:
            return str(col.type)
    def format_col_str(col):
         if show_datatypes:
             return "- %s : %s" % (col.name, format_col_type(col))
         else:
             return "- %s" % col.name
    html = '<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0"><TR><TD ALIGN="CENTER">%s</TD></TR><TR><TD BORDER="1" CELLPADDING="0"></TD></TR>' % table.name 

    html += ''.join('<TR><TD ALIGN="LEFT" PORT="%s">%s</TD></TR>' % (col.name, format_col_str(col)) for col in table.columns)
    if isinstance(metadata.engine.dialect, PGDialect):
        # postgres engine doesn't reflect indexes
        indexes = dict((name,defin) for name,defin in metadata.engine.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = '%s'" % table.name)))
        if indexes and show_indexes:
            html += '<TR><TD BORDER="1" CELLPADDING="0"></TD></TR>'
            for index, defin in indexes.items():
                ilabel = 'UNIQUE' in defin and 'UNIQUE' or 'INDEX'
                ilabel += defin[defin.index('('):]
                html += '<TR><TD ALIGN="LEFT">%s</TD></TR>' % ilabel
    html += '</TABLE>>'
    return html

def create_schema_graph(tables=None, metadata=None, show_indexes=True, show_datatypes=True, font="Bitstream-Vera Sans",
    concentrate=True, relation_options={}, rankdir='TB'):
    relation_kwargs = {
        'fontsize':7.0
    }
    relation_kwargs.update(relation_options)
    
    if not metadata and len(tables):
        metadata = tables[0].metadata
    elif not tables and metadata:
        if isinstance(metadata.engine.dialect, PGDialect):
            tables = [Table(name, metadata, autoload=True) for (name,) in metadata.engine.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))]
        else:
            raise Exception("Autloading tables currently works only on postgres")
    else:
        raise Exception("You need to specify at least tables or metadata")
    
    graph = pydot.Dot(prog="dot",mode="ipsep",overlap="ipsep",sep=0.01,concentrate=concentrate, rankdir=rankdir)
    for table in tables:
        graph.add_node(pydot.Node(str(table.name),
            shape="plaintext",
            label=_render_table_html(table, metadata, show_indexes, show_datatypes),
            fontname=font, fontsize=7.0
        ))
    
    for table in tables:
        for fk in table.foreign_keys:
            edge = [table.name, fk.column.table.name]
            is_inheritance = fk.parent.primary_key and fk.column.primary_key
            if is_inheritance:
                edge = edge[::-1]
            graph_edge = pydot.Edge(
                headlabel="+ %s"%fk.column.name, taillabel='+ %s'%fk.parent.name,
                arrowhead=is_inheritance and 'none' or 'odot' ,
                arrowtail=(fk.parent.primary_key or fk.parent.unique) and 'empty' or 'crow' ,
                fontname=font, 
                #samehead=fk.column.name, sametail=fk.parent.name,
                *edge, **relation_kwargs
            )
            graph_edge.parent_graph = graph.parent_graph
            if table.name not in graph.edge_src_list:
                graph.edge_src_list.append(table.name)
            if fk.column.table.name not in graph.edge_dst_list:
                graph.edge_dst_list.append(fk.column.table.name)
            graph.sorted_graph_elements.append(graph_edge)
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
