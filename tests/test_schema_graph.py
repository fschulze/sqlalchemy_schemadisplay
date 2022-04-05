from sqlalchemy import types
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy import Table
from utils import parse_graph
import pydot
import pytest
import sqlalchemy_schemadisplay as sasd


@pytest.fixture
def metadata(request):
    return MetaData('sqlite:///:memory:')


def plain_result(**kw):
    if 'metadata' in kw:
        kw['metadata'].create_all()
    elif 'tables' in kw:
        if len(kw['tables']):
            kw['tables'][0].metadata.create_all()
    return parse_graph(sasd.create_schema_graph(**kw))


def test_no_args():
    with pytest.raises(ValueError) as e:
        sasd.create_schema_graph()
    assert e.value.args[0] == 'You need to specify at least tables or metadata'


def test_empty_db(metadata):
    graph = sasd.create_schema_graph(metadata=metadata)
    assert isinstance(graph, pydot.Graph)
    assert graph.create_plain() == b'graph 1 0 0\nstop\n'


def test_empty_table(metadata):
    Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    result = plain_result(metadata=metadata)
    assert list(result.keys()) == ['1']
    assert list(result['1']['nodes'].keys()) == ['foo']
    assert '- id : INTEGER' in result['1']['nodes']['foo']


def test_empty_table_with_key_suffix(metadata):
    Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    result = plain_result(metadata=metadata, show_column_keys=True)
    print(result)
    assert list(result.keys()) == ['1']
    assert list(result['1']['nodes'].keys()) == ['foo']
    assert '- id(PK) : INTEGER' in result['1']['nodes']['foo']


def test_foreign_key(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result(metadata=metadata)
    assert list(result.keys()) == ['1']
    assert sorted(result['1']['nodes'].keys()) == ['bar', 'foo']
    assert '- id : INTEGER' in result['1']['nodes']['foo']
    assert '- foo_id : INTEGER' in result['1']['nodes']['bar']
    assert 'edges' in result['1']
    assert ('bar', 'foo') in result['1']['edges']


def test_foreign_key_with_key_suffix(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result(metadata=metadata, show_column_keys=True)
    assert list(result.keys()) == ['1']
    assert sorted(result['1']['nodes'].keys()) == ['bar', 'foo']
    assert '- id(PK) : INTEGER' in result['1']['nodes']['foo']
    assert '- foo_id(FK) : INTEGER' in result['1']['nodes']['bar']
    assert 'edges' in result['1']
    assert ('bar', 'foo') in result['1']['edges']


def test_table_filtering(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    bar = Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result(tables=[bar])
    assert list(result.keys()) == ['1']
    assert list(result['1']['nodes'].keys()) == ['bar']
    assert '- foo_id : INTEGER' in result['1']['nodes']['bar']

def test_table_rendering_without_schema(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    bar = Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))

    try:
        sasd.create_schema_graph(metadata=metadata).create_png()
    except Exception as ex:
        assert False, "An exception of type {} was produced when attempting to render a png of the graph".format(ex.__class__.__name__)

def test_table_rendering_with_schema(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True),
        schema='sch_foo'
    )
    bar = Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)),
        schema='sch_bar'
    )

    try:
        sasd.create_schema_graph(
            metadata=metadata,
            show_schema_name=True,
        ).create_png()
    except Exception as ex:
        assert False, "An exception of type {} was produced when attempting to render a png of the graph".format(ex.__class__.__name__)

def test_table_rendering_with_schema_and_formatting(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True),
        schema='sch_foo'
    )
    bar = Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)),
        schema='sch_bar'
    )

    try:
        sasd.create_schema_graph(
            metadata=metadata,
            show_schema_name=True,
            format_schema_name={'fontsize':8.0, 'color': '#888888'},
            format_table_name={'bold':True, 'fontsize': 10.0},
        ).create_png()
    except Exception as ex:
        assert False, "An exception of type {} was produced when attempting to render a png of the graph".format(ex.__class__.__name__)
