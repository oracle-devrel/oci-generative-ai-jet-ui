# coding: utf-8
# Copyright (c) 2016, 2024, Oracle and/or its affiliates.  All rights reserved.
# This software is dual-licensed to you under the Universal Permissive License (UPL) 1.0 as shown at https://oss.oracle.com/licenses/upl or Apache License 2.0 as shown at http://www.apache.org/licenses/LICENSE-2.0. You may choose either license.


from oci.util import formatted_flat_dict, NONE_SENTINEL, value_allowed_none_or_none_sentinel  # noqa: F401
from oci.decorators import init_model_state_from_kwargs


@init_model_state_from_kwargs
class Attribute(object):
    """
    Attribute
    """

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_FIVE"
    MAXIMUM_LEN_LENGTH_FIVE = "LENGTH_FIVE"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_SIXTEEN"
    MAXIMUM_LEN_LENGTH_SIXTEEN = "LENGTH_SIXTEEN"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_THIRTYTWO"
    MAXIMUM_LEN_LENGTH_THIRTYTWO = "LENGTH_THIRTYTWO"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_SIXTYFOUR"
    MAXIMUM_LEN_LENGTH_SIXTYFOUR = "LENGTH_SIXTYFOUR"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_ONETWOEIGHT"
    MAXIMUM_LEN_LENGTH_ONETWOEIGHT = "LENGTH_ONETWOEIGHT"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_TWOFIFTYSIX"
    MAXIMUM_LEN_LENGTH_TWOFIFTYSIX = "LENGTH_TWOFIFTYSIX"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_FIVETWELVE"
    MAXIMUM_LEN_LENGTH_FIVETWELVE = "LENGTH_FIVETWELVE"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_SEVENFIFTY"
    MAXIMUM_LEN_LENGTH_SEVENFIFTY = "LENGTH_SEVENFIFTY"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_ONE_THOUSAND"
    MAXIMUM_LEN_LENGTH_ONE_THOUSAND = "LENGTH_ONE_THOUSAND"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_TWO_THOUSAND"
    MAXIMUM_LEN_LENGTH_TWO_THOUSAND = "LENGTH_TWO_THOUSAND"

    #: A constant which can be used with the maximum_len property of a Attribute.
    #: This constant has a value of "LENGTH_FOUR_THOUSAND"
    MAXIMUM_LEN_LENGTH_FOUR_THOUSAND = "LENGTH_FOUR_THOUSAND"

    #: A constant which can be used with the populated_by property of a Attribute.
    #: This constant has a value of "BACKEND_GEN"
    POPULATED_BY_BACKEND_GEN = "BACKEND_GEN"

    #: A constant which can be used with the populated_by property of a Attribute.
    #: This constant has a value of "CALLER_GEN"
    POPULATED_BY_CALLER_GEN = "CALLER_GEN"

    #: A constant which can be used with the required_in_json property of a Attribute.
    #: This constant has a value of "MANDATORY"
    REQUIRED_IN_JSON_MANDATORY = "MANDATORY"

    #: A constant which can be used with the required_in_json property of a Attribute.
    #: This constant has a value of "OPTIONAL"
    REQUIRED_IN_JSON_OPTIONAL = "OPTIONAL"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "CREATE"
    USAGE_SENARIO_CREATE = "CREATE"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "UPDATE"
    USAGE_SENARIO_UPDATE = "UPDATE"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "CREATE_AND_UPDATE"
    USAGE_SENARIO_CREATE_AND_UPDATE = "CREATE_AND_UPDATE"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "DELETE"
    USAGE_SENARIO_DELETE = "DELETE"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "RE_CREATE"
    USAGE_SENARIO_RE_CREATE = "RE_CREATE"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "DETAIL"
    USAGE_SENARIO_DETAIL = "DETAIL"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "LIST"
    USAGE_SENARIO_LIST = "LIST"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "FUNCTION_WITH_LOOKUP"
    USAGE_SENARIO_FUNCTION_WITH_LOOKUP = "FUNCTION_WITH_LOOKUP"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "DB_PATTERN"
    USAGE_SENARIO_DB_PATTERN = "DB_PATTERN"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "CREATE_FIRSTTIME_T1"
    USAGE_SENARIO_CREATE_FIRSTTIME_T1 = "CREATE_FIRSTTIME_T1"

    #: A constant which can be used with the usage_senario property of a Attribute.
    #: This constant has a value of "UPDATE_OOB_METRIC"
    USAGE_SENARIO_UPDATE_OOB_METRIC = "UPDATE_OOB_METRIC"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "INTEGER"
    VALUE_DATA_TYPE_INTEGER = "INTEGER"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "LONG"
    VALUE_DATA_TYPE_LONG = "LONG"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "FLOAT"
    VALUE_DATA_TYPE_FLOAT = "FLOAT"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "STRING"
    VALUE_DATA_TYPE_STRING = "STRING"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "TIMESTAMP"
    VALUE_DATA_TYPE_TIMESTAMP = "TIMESTAMP"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "DATE"
    VALUE_DATA_TYPE_DATE = "DATE"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "CLOB"
    VALUE_DATA_TYPE_CLOB = "CLOB"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "TAG_REF"
    VALUE_DATA_TYPE_TAG_REF = "TAG_REF"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "PARSER_REF"
    VALUE_DATA_TYPE_PARSER_REF = "PARSER_REF"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "STT_REF"
    VALUE_DATA_TYPE_STT_REF = "STT_REF"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "LOOKUP_REF"
    VALUE_DATA_TYPE_LOOKUP_REF = "LOOKUP_REF"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "META_FUNCTION_REF"
    VALUE_DATA_TYPE_META_FUNCTION_REF = "META_FUNCTION_REF"

    #: A constant which can be used with the value_data_type property of a Attribute.
    #: This constant has a value of "COMMON_FIELD_REF"
    VALUE_DATA_TYPE_COMMON_FIELD_REF = "COMMON_FIELD_REF"

    #: A constant which can be used with the value_population_priority property of a Attribute.
    #: This constant has a value of "NONE"
    VALUE_POPULATION_PRIORITY_NONE = "NONE"

    #: A constant which can be used with the value_population_priority property of a Attribute.
    #: This constant has a value of "LOW"
    VALUE_POPULATION_PRIORITY_LOW = "LOW"

    #: A constant which can be used with the value_population_priority property of a Attribute.
    #: This constant has a value of "HIGH"
    VALUE_POPULATION_PRIORITY_HIGH = "HIGH"

    def __init__(self, **kwargs):
        """
        Initializes a new Attribute object with values from keyword arguments.
        The following keyword arguments are supported (corresponding to the getters/setters of this class):

        :param default_value:
            The value to assign to the default_value property of this Attribute.
        :type default_value: object

        :param dynamic_value_range_ref_attr:
            The value to assign to the dynamic_value_range_ref_attr property of this Attribute.
        :type dynamic_value_range_ref_attr: str

        :param maximum_len:
            The value to assign to the maximum_len property of this Attribute.
            Allowed values for this property are: "LENGTH_FIVE", "LENGTH_SIXTEEN", "LENGTH_THIRTYTWO", "LENGTH_SIXTYFOUR", "LENGTH_ONETWOEIGHT", "LENGTH_TWOFIFTYSIX", "LENGTH_FIVETWELVE", "LENGTH_SEVENFIFTY", "LENGTH_ONE_THOUSAND", "LENGTH_TWO_THOUSAND", "LENGTH_FOUR_THOUSAND"
        :type maximum_len: str

        :param name:
            The value to assign to the name property of this Attribute.
        :type name: str

        :param populated_by:
            The value to assign to the populated_by property of this Attribute.
            Allowed values for this property are: "BACKEND_GEN", "CALLER_GEN"
        :type populated_by: str

        :param required_in_json:
            The value to assign to the required_in_json property of this Attribute.
            Allowed values for this property are: "MANDATORY", "OPTIONAL"
        :type required_in_json: str

        :param schema_column:
            The value to assign to the schema_column property of this Attribute.
        :type schema_column: str

        :param is_string_exceed_maximum_length:
            The value to assign to the is_string_exceed_maximum_length property of this Attribute.
        :type is_string_exceed_maximum_length: bool

        :param usage_senario:
            The value to assign to the usage_senario property of this Attribute.
            Allowed values for this property are: "CREATE", "UPDATE", "CREATE_AND_UPDATE", "DELETE", "RE_CREATE", "DETAIL", "LIST", "FUNCTION_WITH_LOOKUP", "DB_PATTERN", "CREATE_FIRSTTIME_T1", "UPDATE_OOB_METRIC"
        :type usage_senario: str

        :param value_data_type:
            The value to assign to the value_data_type property of this Attribute.
            Allowed values for this property are: "INTEGER", "LONG", "FLOAT", "STRING", "TIMESTAMP", "DATE", "CLOB", "TAG_REF", "PARSER_REF", "STT_REF", "LOOKUP_REF", "META_FUNCTION_REF", "COMMON_FIELD_REF"
        :type value_data_type: str

        :param value_population_priority:
            The value to assign to the value_population_priority property of this Attribute.
            Allowed values for this property are: "NONE", "LOW", "HIGH"
        :type value_population_priority: str

        """
        self.swagger_types = {
            'default_value': 'object',
            'dynamic_value_range_ref_attr': 'str',
            'maximum_len': 'str',
            'name': 'str',
            'populated_by': 'str',
            'required_in_json': 'str',
            'schema_column': 'str',
            'is_string_exceed_maximum_length': 'bool',
            'usage_senario': 'str',
            'value_data_type': 'str',
            'value_population_priority': 'str'
        }

        self.attribute_map = {
            'default_value': 'defaultValue',
            'dynamic_value_range_ref_attr': 'dynamicValueRangeRefAttr',
            'maximum_len': 'maximumLen',
            'name': 'name',
            'populated_by': 'populatedBy',
            'required_in_json': 'requiredInJSON',
            'schema_column': 'schemaColumn',
            'is_string_exceed_maximum_length': 'isStringExceedMaximumLength',
            'usage_senario': 'usageSenario',
            'value_data_type': 'valueDataType',
            'value_population_priority': 'valuePopulationPriority'
        }

        self._default_value = None
        self._dynamic_value_range_ref_attr = None
        self._maximum_len = None
        self._name = None
        self._populated_by = None
        self._required_in_json = None
        self._schema_column = None
        self._is_string_exceed_maximum_length = None
        self._usage_senario = None
        self._value_data_type = None
        self._value_population_priority = None

    @property
    def default_value(self):
        """
        Gets the default_value of this Attribute.
        default value


        :return: The default_value of this Attribute.
        :rtype: object
        """
        return self._default_value

    @default_value.setter
    def default_value(self, default_value):
        """
        Sets the default_value of this Attribute.
        default value


        :param default_value: The default_value of this Attribute.
        :type: object
        """
        self._default_value = default_value

    @property
    def dynamic_value_range_ref_attr(self):
        """
        Gets the dynamic_value_range_ref_attr of this Attribute.
        dynamic value range reference attribute


        :return: The dynamic_value_range_ref_attr of this Attribute.
        :rtype: str
        """
        return self._dynamic_value_range_ref_attr

    @dynamic_value_range_ref_attr.setter
    def dynamic_value_range_ref_attr(self, dynamic_value_range_ref_attr):
        """
        Sets the dynamic_value_range_ref_attr of this Attribute.
        dynamic value range reference attribute


        :param dynamic_value_range_ref_attr: The dynamic_value_range_ref_attr of this Attribute.
        :type: str
        """
        self._dynamic_value_range_ref_attr = dynamic_value_range_ref_attr

    @property
    def maximum_len(self):
        """
        Gets the maximum_len of this Attribute.
        maximum length

        Allowed values for this property are: "LENGTH_FIVE", "LENGTH_SIXTEEN", "LENGTH_THIRTYTWO", "LENGTH_SIXTYFOUR", "LENGTH_ONETWOEIGHT", "LENGTH_TWOFIFTYSIX", "LENGTH_FIVETWELVE", "LENGTH_SEVENFIFTY", "LENGTH_ONE_THOUSAND", "LENGTH_TWO_THOUSAND", "LENGTH_FOUR_THOUSAND"


        :return: The maximum_len of this Attribute.
        :rtype: str
        """
        return self._maximum_len

    @maximum_len.setter
    def maximum_len(self, maximum_len):
        """
        Sets the maximum_len of this Attribute.
        maximum length


        :param maximum_len: The maximum_len of this Attribute.
        :type: str
        """
        allowed_values = ["LENGTH_FIVE", "LENGTH_SIXTEEN", "LENGTH_THIRTYTWO", "LENGTH_SIXTYFOUR", "LENGTH_ONETWOEIGHT", "LENGTH_TWOFIFTYSIX", "LENGTH_FIVETWELVE", "LENGTH_SEVENFIFTY", "LENGTH_ONE_THOUSAND", "LENGTH_TWO_THOUSAND", "LENGTH_FOUR_THOUSAND"]
        if not value_allowed_none_or_none_sentinel(maximum_len, allowed_values):
            raise ValueError(
                "Invalid value for `maximum_len`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._maximum_len = maximum_len

    @property
    def name(self):
        """
        Gets the name of this Attribute.
        name


        :return: The name of this Attribute.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """
        Sets the name of this Attribute.
        name


        :param name: The name of this Attribute.
        :type: str
        """
        self._name = name

    @property
    def populated_by(self):
        """
        Gets the populated_by of this Attribute.
        populated by

        Allowed values for this property are: "BACKEND_GEN", "CALLER_GEN"


        :return: The populated_by of this Attribute.
        :rtype: str
        """
        return self._populated_by

    @populated_by.setter
    def populated_by(self, populated_by):
        """
        Sets the populated_by of this Attribute.
        populated by


        :param populated_by: The populated_by of this Attribute.
        :type: str
        """
        allowed_values = ["BACKEND_GEN", "CALLER_GEN"]
        if not value_allowed_none_or_none_sentinel(populated_by, allowed_values):
            raise ValueError(
                "Invalid value for `populated_by`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._populated_by = populated_by

    @property
    def required_in_json(self):
        """
        Gets the required_in_json of this Attribute.
        required in JSON

        Allowed values for this property are: "MANDATORY", "OPTIONAL"


        :return: The required_in_json of this Attribute.
        :rtype: str
        """
        return self._required_in_json

    @required_in_json.setter
    def required_in_json(self, required_in_json):
        """
        Sets the required_in_json of this Attribute.
        required in JSON


        :param required_in_json: The required_in_json of this Attribute.
        :type: str
        """
        allowed_values = ["MANDATORY", "OPTIONAL"]
        if not value_allowed_none_or_none_sentinel(required_in_json, allowed_values):
            raise ValueError(
                "Invalid value for `required_in_json`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._required_in_json = required_in_json

    @property
    def schema_column(self):
        """
        Gets the schema_column of this Attribute.
        schema column


        :return: The schema_column of this Attribute.
        :rtype: str
        """
        return self._schema_column

    @schema_column.setter
    def schema_column(self, schema_column):
        """
        Sets the schema_column of this Attribute.
        schema column


        :param schema_column: The schema_column of this Attribute.
        :type: str
        """
        self._schema_column = schema_column

    @property
    def is_string_exceed_maximum_length(self):
        """
        Gets the is_string_exceed_maximum_length of this Attribute.
        is string exceed maximum length


        :return: The is_string_exceed_maximum_length of this Attribute.
        :rtype: bool
        """
        return self._is_string_exceed_maximum_length

    @is_string_exceed_maximum_length.setter
    def is_string_exceed_maximum_length(self, is_string_exceed_maximum_length):
        """
        Sets the is_string_exceed_maximum_length of this Attribute.
        is string exceed maximum length


        :param is_string_exceed_maximum_length: The is_string_exceed_maximum_length of this Attribute.
        :type: bool
        """
        self._is_string_exceed_maximum_length = is_string_exceed_maximum_length

    @property
    def usage_senario(self):
        """
        Gets the usage_senario of this Attribute.
        usage senario

        Allowed values for this property are: "CREATE", "UPDATE", "CREATE_AND_UPDATE", "DELETE", "RE_CREATE", "DETAIL", "LIST", "FUNCTION_WITH_LOOKUP", "DB_PATTERN", "CREATE_FIRSTTIME_T1", "UPDATE_OOB_METRIC"


        :return: The usage_senario of this Attribute.
        :rtype: str
        """
        return self._usage_senario

    @usage_senario.setter
    def usage_senario(self, usage_senario):
        """
        Sets the usage_senario of this Attribute.
        usage senario


        :param usage_senario: The usage_senario of this Attribute.
        :type: str
        """
        allowed_values = ["CREATE", "UPDATE", "CREATE_AND_UPDATE", "DELETE", "RE_CREATE", "DETAIL", "LIST", "FUNCTION_WITH_LOOKUP", "DB_PATTERN", "CREATE_FIRSTTIME_T1", "UPDATE_OOB_METRIC"]
        if not value_allowed_none_or_none_sentinel(usage_senario, allowed_values):
            raise ValueError(
                "Invalid value for `usage_senario`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._usage_senario = usage_senario

    @property
    def value_data_type(self):
        """
        Gets the value_data_type of this Attribute.
        value data type

        Allowed values for this property are: "INTEGER", "LONG", "FLOAT", "STRING", "TIMESTAMP", "DATE", "CLOB", "TAG_REF", "PARSER_REF", "STT_REF", "LOOKUP_REF", "META_FUNCTION_REF", "COMMON_FIELD_REF"


        :return: The value_data_type of this Attribute.
        :rtype: str
        """
        return self._value_data_type

    @value_data_type.setter
    def value_data_type(self, value_data_type):
        """
        Sets the value_data_type of this Attribute.
        value data type


        :param value_data_type: The value_data_type of this Attribute.
        :type: str
        """
        allowed_values = ["INTEGER", "LONG", "FLOAT", "STRING", "TIMESTAMP", "DATE", "CLOB", "TAG_REF", "PARSER_REF", "STT_REF", "LOOKUP_REF", "META_FUNCTION_REF", "COMMON_FIELD_REF"]
        if not value_allowed_none_or_none_sentinel(value_data_type, allowed_values):
            raise ValueError(
                "Invalid value for `value_data_type`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._value_data_type = value_data_type

    @property
    def value_population_priority(self):
        """
        Gets the value_population_priority of this Attribute.
        value population priority

        Allowed values for this property are: "NONE", "LOW", "HIGH"


        :return: The value_population_priority of this Attribute.
        :rtype: str
        """
        return self._value_population_priority

    @value_population_priority.setter
    def value_population_priority(self, value_population_priority):
        """
        Sets the value_population_priority of this Attribute.
        value population priority


        :param value_population_priority: The value_population_priority of this Attribute.
        :type: str
        """
        allowed_values = ["NONE", "LOW", "HIGH"]
        if not value_allowed_none_or_none_sentinel(value_population_priority, allowed_values):
            raise ValueError(
                "Invalid value for `value_population_priority`, must be None or one of {0}"
                .format(allowed_values)
            )
        self._value_population_priority = value_population_priority

    def __repr__(self):
        return formatted_flat_dict(self)

    def __eq__(self, other):
        if other is None:
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
