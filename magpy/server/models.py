"""Models for Magpy server application.

Many of these are designed to have custom fields and therefore
it is not possible to validate them in the normal way.

The primary use of _model and _settings to give them custom fields.

_user and_group do not need custom fields, but they are often useful,
so nothing in Magpy stops applications from adding them.

To load these models into your database, use the following command:

mag.py load_models magpy.server

"""

MODELS = (
    {
        '_id': '_model',
        '_model': '_model',
        'modeldescription': 'A resource type definition.',
        },
    {
        '_id': '_history',
        '_model': '_model',
        'modeldescription': 'A version of a resource instance.',
        'document_id': {
            'field': 'Char',
            },
        'document': {
            'field': 'Char',
            },
        'operation': {
            'field': 'Char',
            },
        'comment': {
            'field': 'Char',
            'required': False,
            }
        },
    {
        '_id': '_settings',
        '_model': '_model',
        'modeldescription': 'Site specific settings.',
        },
    {
        '_id': '_user',
        '_model': '_model',
        'modeldescription': 'A user',
        'email': {
            'field': 'Email',
            },
        'name': {
            'field': 'Char',
            'required': False,
            },
        'first_name': {
            'field': 'Char',
            'required': False,
            },
        'last_name': {
            'field': 'Char',
            'required': False,
            },
        'locale': {
            'field': 'Char',
            'required': False,
            },
        },
    {
        '_id': '_group',
        '_model': '_model',
        'modeldescription': 'A group of users',
        'members': {
            'field': 'List',
            'required': False,
            },
        },
    )
