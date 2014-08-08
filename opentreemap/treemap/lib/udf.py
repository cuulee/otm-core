import json

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as trans

from treemap.audit import Role, FieldPermission
from treemap.udf import (UserDefinedFieldDefinition)


@transaction.atomic
def udf_create(params, instance):
    data = _parse_params(params)
    name, model_type, datatype = (data['name'], data['model_type'],
                                  data['datatype'])

    udfs = UserDefinedFieldDefinition.objects.filter(
        instance=instance,
        # TODO: why isn't this also checking model name
        # is there some reason the same name can't appear
        # on more than one model?
        # Too scared to change this.
        name=name)

    if udfs.exists():
        raise ValidationError(
            {'udf.name':
             trans("A user defined field with name "
                   "'%(udf_name)s' already exists") % {'udf_name': name}})

    if model_type not in ['Tree', 'Plot']:
        raise ValidationError(
            {'udf.model': trans('Invalid model')})

    udf = UserDefinedFieldDefinition(
        name=name,
        model_type=model_type,
        iscollection=False,
        instance=instance,
        datatype=datatype)
    udf.save()

    field_name = udf.canonical_name

    # Add a restrictive permission for this UDF to all roles in the
    # instance
    for role in Role.objects.filter(instance=instance):
        FieldPermission.objects.get_or_create(
            model_name=model_type,
            field_name=field_name,
            permission_level=FieldPermission.NONE,
            role=role,
            instance=role.instance)

    return udf


def _parse_params(params):
    name = params.get('udf.name', None)
    model_type = params.get('udf.model', None)
    udf_type = params.get('udf.type', None)

    datatype = {'type': udf_type}

    if udf_type == 'choice':
        datatype['choices'] = params.get('udf.choices', None)

    datatype = json.dumps(datatype)

    return {'name': name, 'model_type': model_type,
            'datatype': datatype}
