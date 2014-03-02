from sqlalchemy import types
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import MetaData
from sqlalchemy import Table
import pydot
import pytest
import sqlalchemy_schemadisplay as sasd


@pytest.fixture
def metadata(request):
    return MetaData('sqlite:///:memory:')


def plain_result_list(**kw):
    kw['metadata'].create_all()
    graph = sasd.create_schema_graph(**kw)
    return filter(None, (x.strip() for x in graph.create_plain().split('\n')))


def test_no_args():
    with pytest.raises(ValueError) as e:
        sasd.create_schema_graph()
    assert e.value.args[0] == 'You need to specify at least tables or metadata'


def test_empty_db(metadata):
    graph = sasd.create_schema_graph(metadata=metadata)
    assert isinstance(graph, pydot.Graph)
    assert graph.create_plain() == 'graph 1 0 0\nstop\n'


def test_empty_table(metadata):
    Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    result = plain_result_list(metadata=metadata)
    assert len(result) == 3
    assert result[0].startswith('graph 1')
    assert result[1].startswith('node foo')
    assert '- id : INTEGER' in result[1]
    assert result[2] == 'stop'


def test_foreign_key(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result_list(metadata=metadata)
    assert result[0].startswith('graph 1')
    assert result[1].startswith('node foo')
    assert '- id : INTEGER' in result[1]
    assert result[2].startswith('node bar')
    assert '- foo_id : INTEGER' in result[2]
    assert result[3].startswith('edge bar foo')
    assert result[4] == 'stop'
