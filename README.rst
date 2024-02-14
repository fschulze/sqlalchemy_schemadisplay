sqlalchemy_schemadisplay
========================

Turn SQLAlchemy DB Model into a graph.

.. image:: https://img.shields.io/pypi/v/sqlalchemy_schemadisplay
   :alt: PyPI
   :target: https://pypi.org/project/sqlalchemy_schemadisplay


See `SQLAlchemy wiki <https://github.com/sqlalchemy/sqlalchemy/wiki/SchemaDisplay>`_ for the previous version of this doc.

Usage
=====

You will need atleast SQLAlchemy and pydot along with graphviz for this. Graphviz-cairo is highly recommended to get tolerable image quality. If PIL and an image viewer are available then there are functions to automatically show the image. Some of the stuff, specifically loading list of tables from a database via a mapper and reflecting indexes currently only work on postgres.

This is an example of database entity diagram generation:

.. code-block:: python

    from sqlalchemy import MetaData
    from sqlalchemy_schemadisplay import create_schema_graph

    # create the pydot graph object by autoloading all tables via a bound metadata object
    graph = create_schema_graph(metadata=MetaData('postgres://user:pwd@host/database'),
       show_datatypes=False, # The image would get nasty big if we'd show the datatypes
       show_indexes=False, # ditto for indexes
       rankdir='LR', # From left to right (instead of top to bottom)
       concentrate=False # Don't try to join the relation lines together
    )
    graph.write_png('dbschema.png') # write out the file


And an UML class diagram from a model:

.. code-block:: python

    from myapp import model
    from sqlalchemy_schemadisplay import create_uml_graph
    from sqlalchemy.orm import class_mapper

    # lets find all the mappers in our model
    mappers = [model.__mapper__]
    for attr in dir(model):
        if attr[0] == '_': continue
        try:
            cls = getattr(model, attr)
            mappers.append(cls.property.entity)
        except:
            pass

    # pass them to the function and set some formatting options
    graph = create_uml_graph(mappers,
        show_operations=False, # not necessary in this case
        show_multiplicity_one=False # some people like to see the ones, some don't
    )
    graph.write_png('schema.png') # write out the file


Changelog
=========

1.4 - 2024-02-15
----------------

Last release to support Python 2.

- Limit SQLAlchemy dependency to < 2.0 to fix installation for Python 2

- Set dir kwarg in Edge instantiation to 'both' in order to show arrow heads and arrow tails.
  [bkrn - Aaron Di Silvestro]

- Add 'show_column_keys' kwarg to 'create_schema_graph' to allow a PK/FK suffix to be added to columns that are primary keys/foreign keys respectively [cchrysostomou - Constantine Chrysostomou]

- Add 'restrict_tables' kwarg to 'create_schema_graph' to restrict the desired tables we want to generate via graphviz and show relationships for [cchrysostomou - Constantine Chrysostomou]


1.3 - 2016-01-27
----------------

- Fix warning about illegal attribute in uml generation by using correct
  attribute.
  [electrocucaracha - Victor Morales]

- Use MIT license
  [fschulze]


1.2 - 2014-03-02
----------------

- Compatibility with SQLAlchemy 0.9.
  [fschulze]

- Compatibility with SQLAlchemy 0.8.
  [Surgo - Kosei Kitahara]

- Leave tables out even when a foreign key points to them but they are not in
  the table list.
  [tiagosab - Tiago Saboga]


1.1 - 2011-10-12
----------------

- New option to skip inherited attributes.
  [nouri]

- Quote class name, because some names like 'Node' confuse dot.
  [nouri - Daniel Nouri]


1.0 - 2011-01-07
----------------

- Initial release
  [fschulze - Florian Schulze]

- Original releases as recipe on SQLAlchemy Wiki by Ants Aasma
