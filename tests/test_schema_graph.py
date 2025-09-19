"""Set of tests for database diagrams"""
import pydot
import pytest
from sqlalchemy import Column, ForeignKey, MetaData, Table, create_engine, types

import sqlalchemy_schemadisplay
from .utils import parse_graph


@pytest.fixture
def metadata(request):
    engine = create_engine("sqlite:///:memory:")
    _metadata = MetaData()
    _metadata.reflect(engine)
    return _metadata


@pytest.fixture
def engine():
    return create_engine("sqlite:///:memory:")


def plain_result(**kw):
    if "metadata" in kw:
        kw["metadata"].create_all(kw['engine'])
    elif "tables" in kw:
        if len(kw["tables"]):
            kw["tables"][0].metadata.create_all(kw['engine'])
    return parse_graph(sqlalchemy_schemadisplay.create_schema_graph(**kw))


def test_no_args(engine):
    with pytest.raises(ValueError) as e:
        sqlalchemy_schemadisplay.create_schema_graph(engine=engine)
    assert e.value.args[0] == "You need to specify at least tables or metadata"


def test_default_graph_args(metadata, engine):
    graph = sqlalchemy_schemadisplay.create_schema_graph(engine=engine,
                                                         metadata=metadata)
    assert graph.get_attributes() == {
        "prog": "dot",
        "mode": "ipsep",
        "overlap": "ipsep",
        "sep": "0.01",
        "concentrate": "True",
        "rankdir": "TB",
    }

def test_custom_graph_args(metadata, engine):
    graph = sqlalchemy_schemadisplay.create_schema_graph(engine=engine,
                                                         metadata=metadata,
                                                         format_graph={"sep": "0.5", "rankdir":"LR", "dpi": 300})
    assert graph.get_attributes() == {
        "prog": "dot",
        "mode": "ipsep",
        "overlap": "ipsep",
        "sep": "0.5",
        "concentrate": "True",
        "rankdir": "LR",
        "dpi": 300,
    }


def test_empty_db(metadata, engine):
    graph = sqlalchemy_schemadisplay.create_schema_graph(engine=engine,
                                                         metadata=metadata)
    assert isinstance(graph, pydot.Graph)
    assert graph.create_plain() == b"graph 1 0 0\nstop\n"


def test_empty_table(metadata, engine):
    foo = Table("foo", metadata, Column("id", types.Integer, primary_key=True))
    result = plain_result(engine=engine, metadata=metadata)
    assert list(result.keys()) == ["1"]
    assert list(result["1"]["nodes"].keys()) == ["foo"]
    assert "- id : INTEGER" in result["1"]["nodes"]["foo"]


def test_empty_table_with_key_suffix(metadata, engine):
    foo = Table("foo", metadata, Column("id", types.Integer, primary_key=True))
    result = plain_result(
        engine=engine,
        metadata=metadata,
        show_column_keys=True,
    )
    print(result)
    assert list(result.keys()) == ["1"]
    assert list(result["1"]["nodes"].keys()) == ["foo"]
    assert "- id(PK) : INTEGER" in result["1"]["nodes"]["foo"]


def test_foreign_key(metadata, engine):
    foo = Table(
        "foo",
        metadata,
        Column("id", types.Integer, primary_key=True),
    )
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
    )
    result = plain_result(engine=engine, metadata=metadata)
    assert list(result.keys()) == ["1"]
    assert sorted(result["1"]["nodes"].keys()) == ["bar", "foo"]
    assert "- id : INTEGER" in result["1"]["nodes"]["foo"]
    assert "- foo_id : INTEGER" in result["1"]["nodes"]["bar"]
    assert "edges" in result["1"]
    assert ("bar", "foo") in result["1"]["edges"]


def test_foreign_key_with_key_suffix(metadata, engine):
    foo = Table(
        "foo",
        metadata,
        Column("id", types.Integer, primary_key=True),
    )
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
    )
    result = plain_result(engine=engine,
                          metadata=metadata,
                          show_column_keys=True)
    assert list(result.keys()) == ["1"]
    assert sorted(result["1"]["nodes"].keys()) == ["bar", "foo"]
    assert "- id(PK) : INTEGER" in result["1"]["nodes"]["foo"]
    assert "- foo_id(FK) : INTEGER" in result["1"]["nodes"]["bar"]
    assert "edges" in result["1"]
    assert ("bar", "foo") in result["1"]["edges"]


def test_table_filtering(engine, metadata):
    foo = Table(
        "foo",
        metadata,
        Column("id", types.Integer, primary_key=True),
    )
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
    )
    result = plain_result(engine=engine, tables=[bar])
    assert list(result.keys()) == ["1"]
    assert list(result["1"]["nodes"].keys()) == ["bar"]
    assert "- foo_id : INTEGER" in result["1"]["nodes"]["bar"]


def test_table_rendering_without_schema(metadata, engine):
    foo = Table(
        "foo",
        metadata,
        Column("id", types.Integer, primary_key=True),
    )
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
    )

    try:
        sqlalchemy_schemadisplay.create_schema_graph(
            engine=engine, metadata=metadata).create_png()
    except Exception as ex:
        assert (
            False
        ), f"An exception of type {ex.__class__.__name__} was produced when attempting to render a png of the graph"


def test_table_rendering_with_schema(metadata, engine):
    foo = Table("foo",
                metadata,
                Column("id", types.Integer, primary_key=True),
                schema="sch_foo")
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
        schema="sch_bar",
    )

    try:
        sqlalchemy_schemadisplay.create_schema_graph(
            engine=engine,
            metadata=metadata,
            show_schema_name=True,
        ).create_png()
    except Exception as ex:
        assert (
            False
        ), f"An exception of type {ex.__class__.__name__} was produced when attempting to render a png of the graph"


def test_table_rendering_with_schema_and_formatting(metadata, engine):
    foo = Table("foo",
                metadata,
                Column("id", types.Integer, primary_key=True),
                schema="sch_foo")
    bar = Table(
        "bar",
        metadata,
        Column("foo_id", types.Integer, ForeignKey(foo.c.id)),
        schema="sch_bar",
    )

    try:
        sqlalchemy_schemadisplay.create_schema_graph(
            engine=engine,
            metadata=metadata,
            show_schema_name=True,
            format_schema_name={
                "fontsize": 8.0,
                "color": "#888888"
            },
            format_table_name={
                "bold": True,
                "fontsize": 10.0
            },
        ).create_png()
    except Exception as ex:
        assert (
            False
        ), f"An exception of type {ex.__class__.__name__} was produced when attempting to render a png of the graph"
