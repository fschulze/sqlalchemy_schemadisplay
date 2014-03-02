try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
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
    if 'metadata' in kw:
        kw['metadata'].create_all()
    elif 'tables' in kw:
        if len(kw['tables']):
            kw['tables'][0].metadata.create_all()
    graph = sasd.create_schema_graph(**kw)
    result = {}
    sio = StringIO(graph.create_plain())
    graph = None
    for line in sio:
        line = line.strip()
        if not line:
            continue
        if line.startswith('graph'):
            parts = line.split(None, 4)
            graph = result.setdefault(parts[1], {'nodes': {}})
            if len(parts) > 4:
                graph['options'] = parts[4]
        elif line.startswith('node'):
            parts = line.split(None, 6)
            graph['nodes'][parts[1]] = parts[6]
        elif line.startswith('edge'):
            parts = line.split(None, 3)
            graph.setdefault('edges', {})[(parts[1], parts[2])] = parts[3]
        elif line == 'stop':
            graph = None
        else:
            raise ValueError("Don't know how to handle line:\n%s" % line)
    return result


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
    assert result.keys() == ['1']
    assert result['1']['nodes'].keys() == ['foo']
    assert '- id : INTEGER' in result['1']['nodes']['foo']


def test_foreign_key(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result_list(metadata=metadata)
    assert result.keys() == ['1']
    assert sorted(result['1']['nodes'].keys()) == ['bar', 'foo']
    assert '- id : INTEGER' in result['1']['nodes']['foo']
    assert '- foo_id : INTEGER' in result['1']['nodes']['bar']
    assert 'edges' in result['1']
    assert ('bar', 'foo') in result['1']['edges']


def test_table_filtering(metadata):
    foo = Table(
        'foo', metadata,
        Column('id', types.Integer, primary_key=True))
    bar = Table(
        'bar', metadata,
        Column('foo_id', types.Integer, ForeignKey(foo.c.id)))
    result = plain_result_list(tables=[bar])
    assert result.keys() == ['1']
    assert result['1']['nodes'].keys() == ['bar']
    assert '- foo_id : INTEGER' in result['1']['nodes']['bar']
