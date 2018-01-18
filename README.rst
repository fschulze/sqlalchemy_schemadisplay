sqlalchemy_schemadisplay
========================

Turn SQLAlchemy DB Model into a graph.

See http://www.sqlalchemy.org/trac/wiki/UsageRecipes/SchemaDisplay


Changelog
=========

1.4 - Unreleased
----------------

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
