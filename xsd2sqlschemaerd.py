# This script creates a SQL Server Database Schema based on an XSD (XML Schema Definition) file. It parses the XSD file, translates the XML schema types to PostgreSQL data types, and generates SQL statements to create the corresponding database tables and relationships.
'''
xsd2sqlschemaerd.py
Functions
- readable_file(string): Validates if the provided string is a readable file.
- sql_normalize(string): Normalizes strings like column names for SQL Server.
- look4element(ns, el, parent=None, recurse_level=0, fail=False, normalize=True, comesFromChoice=False): Recursively looks for elements in the XSD and generates SQL for table creation.
- GetParentTableName(parent): Returns the parent table name.
- buildTypes(ns, root_element): Processes defined types in the XSD and stores them in USER_TYPES.
- create_graph(arrCreateTables): Creates a directed graph of table dependencies based on SQL create table statements.
- analize_instruction(instruction): Analyzes a SQL create table instruction to extract the table name and referenced tables.
- get_table_name(instruction, pref='CREATE TABLE '): Extracts the table name from a SQL create table instruction.
- create_plantuml_diagram(graph, arrCreateTables): Generates a PlantUML diagram from the table dependency graph.
- create_table_definitios_in_plantuml_diagram(arrCreateTables): Generates PlantUML entity definitions for tables.
- create_relationships_in_plantuml_diagram(graph): Generates PlantUML relationships between tables.
Exceptions
- InvalidXMLType: Raised when an invalid XML type is encountered.
- MaxRecursion: Raised when the maximum recursion level is exceeded.
Main Execution
- Parses command-line arguments.
- Reads and parses the XSD file.
- Builds types and parses the structure.
- Generates SQL statements for table creation.
- Optionally connects to a Sql Server Database and executes the SQL statements.
- Generates a PlantUML diagram of the database schema.
'''

import argparse
import re
import networkx as nx
import os
# import sys
import xml.etree.ElementTree as ET
import lxml

# ! /usr/bin/python
""" xsd2sqlschemaerd.py
========================================

Create a database based on an XSD schema. 

Usage
========================================
    <file>  XSD file to base the SQL Server Schema on

    -f  --fail  Fail on finding a bad XS type
    -a  --as-is     Don't normalize element names.

    -d  --database  DB name
    -u  --user  DB Username
    -p  --password  DB Password
    -h  --host  DB host
    -P  --port  DB port

Without connecting DB
python.exe xsd2sqlschemaerd.py ".\\tests\\private\\my_example.xsd"
    
With connecting DB
python.exe xsd2sqlschemaerd.py --database PruebaXsd2DBSchema --host "my_server\my_instance" --user my_user --password my_user ".\\tests\\private\\my_example.xsd"
"""

""" Constants
"""
CONSTANT_COUNTER_CHOICE_STR = "/*counter_choice="

""" You can set default DB connection settings here if you'd like
"""
DB = {
    'user': None,
    'pass': None,
    'port': None,
    'host': 'localhost',
}

""" Some configuration items """
MAX_RECURSE_LEVEL = 1000

""" XSD to Sql Server data type translation dictionary. 
"""


class SDict(dict):
    def __getitem__(self, item):
        return dict.__getitem__(self, item) % self

    def get(self, item):
        try:
            return dict.__getitem__(self, item) % self
        except KeyError:
            return None


# Dictionary that stores SQL Server Data Types
DEFX2SQLSERVER = SDict({
    'string': 'nvarchar(max)',
    'boolean': 'bit',
    'decimal': 'decimal(18,2)',
    'float': 'float',
    'double': 'float',
    'duration': 'time',  # No exact SQL Server type for interval
    'dateTime': 'datetime2',
    'time': 'time',
    'date': 'date',
    'gYearMonth': 'datetime2',
    'gYear': 'datetime2',
    'gMonthDay': 'datetime2',
    'gDay': 'datetime2',
    'gMonth': 'datetime2',
    'hexBinary': 'varbinary(max)',
    'base64Binary': 'varbinary(max)',
    'anyURI': 'nvarchar(max)',
    'QName': None,
    'NOTATION': None,
    'normalizedString': 'nvarchar(max)',
    'token': 'nvarchar(max)',
    'language': 'nvarchar(max)',
    'NMTOKEN': None,
    'NMTOKENS': None,
    'Name': 'nvarchar(max)',
    'NCName': 'nvarchar(max)',
    'ID': None,
    'IDREF': None,
    'IDREFS': None,
    'ENTITY': None,
    'ENTITIES': None,
    'integer': 'bigint',
    'nonPositiveInteger': 'bigint',
    'negativeInteger': 'bigint',
    'long': 'bigint',
    'int': 'int',
    'short': 'smallint',
    'byte': 'tinyint',
    'nonNegativeInteger': 'bigint',
    'unsignedLong': 'bigint',
    'unsignedInt': 'int',
    'unsignedShort': 'smallint',
    'unsignedByte': 'tinyint',
    'positiveInteger': 'bigint',
})

# Dictionary where the mapping of element and type names to the user-defined types within the application is store
USER_TYPES = {}

# Dictionary that keeps a trace for generated tables
HASH_TABLE_TABLES_GENERATED = {}

# Dictionary that stores the accumulated columns for each table
TABLE_COLUMNS = {}

# XMLS = "{http://www.w3.org/2001/XMLSchema}"
# XMLS_PREFIX = "xs:"

# This dictionary that stores store namespaces in format XMLS_PREFIX : XMLS
# Example
#NAMESPACE_DICT = {
#    # XMLS_PREFIX : XMLS
#    "{http://www.w3.org/2001/XMLSchema}": "xs:",
#    "{http://www.w3.org/2000/09/xmldsig#}": "ds:"
#}
NAMESPACE_DICT = {}


""" Helpers
"""


class InvalidXMLType(Exception): pass


class MaxRecursion(Exception): pass


def readable_file(string):
    """
    Validates if a given string is a path to a readable file.

    This function attempts to open the file at the given path in read mode
    to confirm that it is readable. If successful, it returns the original
    string. If the file cannot be opened due to an IOError (e.g., the file
    does not exist or there are permission issues), it raises an
    `argparse.ArgumentTypeError`, which is useful when using this function
    for command-line argument validation.

    Parameters:
    - string (str): A string representing the file path to be validated.

    Returns:
    - str: The original string if the file at the specified path is readable.

    Raises:
    - argparse.ArgumentTypeError: If the file at the specified path cannot
      be opened for reading, providing a message that the file is not
      readable.

    Usage:
    - Commonly used in conjunction with Python's argparse module to ensure
      that command-line arguments specifying file paths point to valid,
      readable files.

    Example:
        parser = argparse.ArgumentParser(description="Process some files.")
        parser.add_argument("input_file", type=readable_file, help="Path to a readable file.")
        args = parser.parse_args()

    Notes:
    - The function simply checks for the ability to open the file in read mode
      and does not read or process the file content.
    - It assumes that the `argparse` module has been imported, as the
      error type raised is intended for use with argparse.
    """

    try:
        with open(string, 'r') as f:
            pass
        return string
    except IOError:
        msg = f"{string} no es un archivo legible"
        raise argparse.ArgumentTypeError(msg)


def sql_normalize(string, ns):
    """
    Normalizes a given string by replacing certain characters with underscores and analizing special cases for `ns` prefix.

    This function performs several transformations on the input string:
    - Strips leading whitespace.
    - Replaces hyphens ('-'), periods ('.'), and spaces (' ') with underscores ('_').
    - Note that the line for converting the string to lowercase is commented out, indicating it is not currently in use.

    Args:
        string (str): The input string to be normalized. If `None` or an empty string is provided, it defaults to an
        empty string.
        ns: key in dictionary NAMESPACE_DICT

    Global Variables:
        NAMESPACE_DICT[ns] (str): A prefix (XMLS_PREFIX) to be removed from XML type names before performing the mapping.

    Returns:
        str: The normalized string with specified character replacements applied.

    Note:
        - This function is typically used to transform strings for consistent internal use, such as converting XML
        element names to a format suitable for identifiers in various programming contexts.
    """
    if not string: string = ''
    string = string.lstrip()
    string = string.replace('-', '_')
    string = string.replace('.', '_')
    string = string.replace(' ', '_')
    if(len(NAMESPACE_DICT.keys()) > 1 and ns is not None and ns.lstrip() != '' and string.lstrip() != ''):
        string = process_prefix(string, NAMESPACE_DICT, ns)

    # string = string.lower()
    return string


def process_prefix(value, namespace_dict, ns):
    """
    Processes a value by handling its prefix according to a namespace dictionary.

    This function checks if a given value has a colon-separated prefix and processes
    the value based on whether this prefix exists in a given namespace dictionary.
    If the prefix exists, it transforms the value according to that prefix. If not,
    it uses a default namespace.

    Args:
        value (str): The string to be processed, which may include a prefix followed
                     by a colon (':').
        namespace_dict (dict): A dictionary where keys are namespaces and values are prefixes.
        ns (str): The namespace key to use when a prefix in the value is not found in
                  `namespace_dict`.

    Returns:
        str: The processed string where the prefix has been handled according to the
             presence in the `namespace_dict`. If the prefix exists, it prefixes the
             remainder with the given prefix. If the prefix doesn’t exist, it uses
             `ns`'s corresponding replacement. If no prefix is present originally,
             `ns`'s replacement is used.

    Example:
        ### 1. Scenario with an Existing Prefix ###

        Suppose we have the following setup:
        - `value = "abc:example"`
        - `namespace_dict = {"ns1": "abc:", "ns2": "def:"}`

        #### Process:
        1. **Split**: The function splits `value` into `["abc", "example"]` due to the separating colon `:`.
        2. **Prefix and Remainder**: `prefix = "abc"` and `rest = "example"`.
        3. **Prefix Construction**: `prefix_two_points = "abc:"`.
        4. **Prefix Check**: The prefix `"abc:"` exists in `namespace_dict.values()`.
        5. **Result**: Returns `f"{prefix}_{rest}"`, which becomes `"abc_example"`.


        ### 2. Scenario with a Non-Existent Prefix ###
        Suppose the value and dictionary are:

        - `value = "xyz:example"`
        - `namespace_dict = {"ns1": "abc:", "ns2": "def:"}`
        - `ns = "ns2"`

        #### Process:

        1. **Split**: The function splits `value` into `["xyz", "example"]`.
        2. **Prefix and Remainder**: `prefix = "xyz"` and `rest = "example"`.
        3. **Prefix Construction**: `prefix_two_points = "xyz:"`.
        4. **Prefix Check**: Prefix `"xyz:"` **does not** exist in `namespace_dict.values()`.
        5. **Use Default Namespace**: Replaces the prefix with `ns` using its value in `namespace_dict: "def_"`. It is
           assumed that `ns` exists in the dictionary.
        6. **Result**: Returns `f"{namespace_dict.get(ns).replace(two_points, '')}_{rest}"`, which becomes `"def_example"`.


        ### 3. Scenario without Prefix ###

        Consider the situation:
        - `value = "example"`
        - `namespace_dict = {"ns1": "abc:", "ns2": "def:"}`
        - `ns = "ns1"`

        #### Process:

        1. **Split**: The function does not find `:`, so `parts` is `["example"]`.
        2. **No Prefix Detected**: There is no split in `prefix` and `rest`, so `{len(parts)}` is not 2.
        3. **Use of Default Namespace**: There is no prefix, so ensure the default prefix `ns` is used.
        4. **Result**: Returns `f"{namespace_dict.get(ns).replace(two_points, '')}_{value}"`, becoming `"abc_example"`.

        ### Summary

        The function considers whether a value has a prefix according to a namespace dictionary, and determines whether
        it should be preserved, replaced by a default namespace, or simply prepended with the value from the default
        namespace if no leading prefix exists.
    """

    two_points =':'
    # Splits the value on a prefix and the remainder if a ':' is found
    parts = value.split(two_points, 1)

    if len(parts) == 2:
        prefix, rest = parts
        prefix_two_points = f"{prefix}:"
        # Check if the prefix exists in the NAMESPACE_DICT dictionary
        if prefix_two_points in namespace_dict.values():
            return f"{prefix}_{rest}"  # Return ns + "_" + value
        else:
            # If the prefix does not exist, replace it with `ns:`
            return f"{namespace_dict.get(ns).replace(two_points, '')}_{rest}"
    else:
        # If there is no prefix in the dictionary, returns ns + "_" + value. It is assumed that `ns` exists in the dictionary.
        return f"{namespace_dict.get(ns).replace(two_points, '')}_{value}"  # Returns ns + "_" + value


def look4element(dict_relationships, root, ns, el, parent=None, recurse_level=0, fail=False, normalize=True,
                 counter_choice=0):
    """
    Recursively processes XML schema elements and generates SQL table definitions based on their structure.

    This function traverses XML schema elements (`<element>`, `<complexType>`, `<sequence>`, `<choice>`),
    processes them, and dynamically constructs SQL table definitions. It also handles complex types and
    nested structures, ensuring that the generated SQL reflects the relationships and hierarchy defined
    in the XML schema.

    Documentation can be found here: <file://./docs/look4element.md>

    Args:
        dict_relationships (dict): A dictionary to store relationships between elements and their parents.
        root (Element): The root node of the XML schema document being processed.
        ns (str): The namespace prefix for the XML schema elements (e.g., `'{http://www.w3.org/2001/XMLSchema}'`).
        el (Element): The current XML element being processed.
        parent (str, optional): The parent element's name, used to establish relationships. Defaults to None.
        recurse_level (int, optional): The current recursion depth, used to prevent infinite loops. Defaults to 0.
        fail (bool, optional): Flag indicating whether to fail on errors (e.g., missing attributes). Defaults to False.
        normalize (bool, optional): Flag to normalize column names during processing. Defaults to True.
        counter_choice (int, optional): Value greater 0, indicates if the current element originates from a `<choice>` structure. Defaults to 0.

    Raises:
        MaxRecursion: If the recursion depth exceeds the maximum allowed (`MAX_RECURSE_LEVEL`).

    Globals:
        TABLE_COLUMNS (dict): A global dictionary where keys are table names
        and values are the columns and their specifications.
        HASH_TABLE_TABLES_GENERATED (dict): A global dictionaru that keeps a trace for generated tables

    Returns:
        tuple:
            - children (bool): True if the current element has children; otherwise, False.
            - cols (str): The accumulated column definitions for the current table or element.

    Notes:
        - The function processes child elements by type: `<element>`, `<complexType>`, `<sequence>`, and `<choice>`.
        - For complex types, it checks if they are defined and processes them recursively.
        - SQL table definitions are updated dynamically to reflect new columns and relationships.

    Examples:
        Process a simple `<element>`:
        ```python
        result = look4element(
            dict_relationships={},
            root=xml_root,
            ns='{http://www.w3.org/2001/XMLSchema}',
            el=xml_element,
            parent='ParentTable'
        )
        print(result[1])  # Outputs the generated SQL
        ```

        Handle a `<complexType>` with nested elements:
        ```xml
        <xs:complexType name="PersonType">
            <xs:sequence>
                <xs:element name="FirstName" type="xs:string"/>
                <xs:element name="LastName" type="xs:string"/>
            </xs:sequence>
        </xs:complexType>
        ```
        The function will generate SQL for a `PersonType` table with `FirstName` and `LastName` columns.


    ### Handling Parent Names:
    - The expression `e.get('name') or parent` ensures that unnamed elements (e.g., `<sequence>`, `<choice>`,
      `<complexType>`) inherit their parent's name.
    - This is particularly useful when dealing with **nested sequences**, where an element does not have an
      explicit name but still belongs to a logical structure.
    - Named elements (e.g., `<element name="X">`) will always use their own name.
    - If an element does not have a name, the parent name is used to maintain hierarchical consistency.

    ### Example:

    Given the following XSD:

    ```xml
    <xs:complexType name="PersonType">
        <xs:sequence>
            <xs:element name="FirstName" type="xs:string"/>
            <xs:element name="LastName" type="xs:string"/>
            <xs:sequence>
                <xs:element name="PhoneNumber" type="xs:string"/>
            </xs:sequence>
        </xs:sequence>
    </xs:complexType>
    ```

    The first `<sequence>` does not have a name, so it inherits `"PersonType"` as its reference.
    The second nested `<sequence>` also does not have a name, but it remains under `"PersonType"`,
    ensuring that `PhoneNumber` is correctly associated with the `"PersonType"` structure.

    This approach prevents the loss of hierarchical relationships and maintains structural integrity
    when generating SQL schema definitions.

    """

    if recurse_level > MAX_RECURSE_LEVEL: raise MaxRecursion()

    CONST_POS_COLS_IN_RES = 1
    children = False
    cols = ''

    # Finds all <element> elements that are direct children of node "el", and the loop goes through them one by one
    # assigning them to "e"
    for e in el.findall(ns + 'element'):
        # Has <element> children
        children = True

        rez = look4element(dict_relationships, root, ns, e, e.get('name') or parent, recurse_level + 1, fail=fail)
        cols = process_element(e, parent, fail, normalize, counter_choice, concat_cols(cols, rez[CONST_POS_COLS_IN_RES]),
                               ns, root, dict_relationships)

    # Finds all <complexType> elements that are direct children of node "el", and the loop goes through them one by one
    # assigning them to "e"
    for e in el.findall(ns + 'complexType'):
        # Has <complexType> children
        children = True

        rez = look4element(dict_relationships, root, ns, e, e.get('name') or parent, recurse_level + 1, fail=fail)
        cols = process_element(e, parent, fail, normalize, counter_choice, concat_cols(cols, rez[CONST_POS_COLS_IN_RES]),
                               ns, root, dict_relationships)

    # Finds all <sequence> elements that are direct children of node "el", and the loop goes through them one by one
    # assigning them to "e"
    for e in el.findall(ns + 'sequence'):
        # Has <secuence> children
        children = True

        look4element(dict_relationships, root, ns, e, e.get('name') or parent, recurse_level + 1, fail=fail)

        # "process_element" should not be needed
        # Example:
        # <xs:complexType name="AdditionalDataType">
        # 		<xs:sequence>
        # 			<xs:element name="RelatedInvoice" type="TextMax40Type" minOccurs="0">

    # Finds all <choice> elements that are direct children of node "el", and the loop goes through them one by one
    # assigning them to "e"
    current_counter_choice = counter_choice
    for e in el.findall(ns + 'choice'):
        # Has <choice> children
        children = True

        current_counter_choice += 1
        rez = look4element(dict_relationships, root, ns, e, e.get('name') or parent, recurse_level + 1, fail=fail,
                           counter_choice=current_counter_choice)
        cols = process_element(e, parent, fail, normalize, current_counter_choice,
                               concat_cols(cols, rez[CONST_POS_COLS_IN_RES]), ns, root, dict_relationships)

    if cols and parent is not None and parent.lstrip() != "" and counter_choice == 0:
        create_table_in_sql_sentence(cols, parent, ns)
        cols = ''

    # Tf the element "el" has no children (i.e. none of the previous findalls could find any children); it checks to
    # see if "el" is a complex type and processes the complex type in a recursive call
    if not children:
        try:
            thisType = el.get('type')
        except:
            thisType = None

        if not thisType is None:
            complex_type = find_complex_type(root, ns, thisType)
            # NOTE. - If it is not a complex data type, then its data type should be
            # defined in DEFX2SQLSERVER or USER_TYPES. Later, in the "process_element" function,
            # its data type is determined
            if complex_type is not None:
                children = True

                look4element(dict_relationships, root, ns, complex_type, complex_type.get('name') or parent,
                             recurse_level + 1, fail=fail, counter_choice=counter_choice)

                if not table_was_created(complex_type, ns):
                    create_table_in_sql_sentence('', complex_type.get('name'), ns)

    return (children, cols)


def concat_cols(cols, previous_cols):
    """
    Concatenates a specified column value to an existing string of column values.

    This function checks if the provided column value (previous_cols) is not None or empty,
    and then concatenates it to the existing `cols` string, separated by a comma.
    If `cols` is None or empty, it simply returns the value of previous_cols.

    Args:
        cols (str): A string representing the existing concatenated column values.
        previous_cols (str): A previos columns string.

    Returns:
        str: The concatenated string of column values, or the single column value
             if `cols` is None or an empty string.
    """
    if previous_cols is None:
        return cols

    if previous_cols.lstrip() == "":
        return cols

    if cols is not None and cols.lstrip() != "":
        return cols + ', ' + previous_cols

    return previous_cols


def is_complex_type(root, ns, type_name):
    """
    Determines if a given type is a complex type within an XML schema.

    Args:
        root (Element): The root element of the XML schema.
        ns (str): The namespace used in the schema.
        type_name (str): The name of the type to check.

    Returns:
        bool: Returns True if the specified type is a complex type, otherwise False.
    """
    complex_type = find_complex_type(root, ns, type_name)
    if complex_type is not None:
        return True
    return False


def table_was_created(el, ns):
    '''
    Verify if a table exists in global dictionary HASH_TABLE_TABLES_GENERATED.

    First, get the atribute 'name' from el param (Xml element)
    Then, looks for table name in HASH_TABLE_TABLES_GENERATED dictionary

    Args:
        el: XML element from which its name atribute is obtained and checked if it exists in the HASH_TABLE_TABLES_GENERATED dictionary
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.
    Returns:
        True if the table was previously created
        False otherwise
    '''
    if sql_normalize(el.get('name'), ns) in HASH_TABLE_TABLES_GENERATED:
        return True
    else:
        return False


def create_table_in_sql_sentence(cols, table_name, ns):
    """
    This function is designed to create and manage SQL table creation statements, ensuring the appropriate structure for
    primary and foreign keys, as well as updating existing table definitions if needed.

    Documentation can be found here: <file://./docs/create_table_in_sql_sentence.md>

    Args:
        cols:
        table_name:
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.

    Globals:
        TABLE_COLUMNS (dict): A global dictionary where keys are table names
        and values are the columns and their specifications.
        HASH_TABLE_TABLES_GENERATED (dict): A global dictionaru that keeps a trace for generated tables

    Returns:
        In indirect way TABLE_COLUMNS and HASH_TABLE_TABLES_GENERATED, modified

    """
    # Create normalized the primary key
    normalized_table_id = create_primary_key(table_name, ns)

    # Create normalized table name
    normalized_table_name = sql_normalize(table_name, ns)

    # Concat primary key with other columns
    new_cols = [normalized_table_id]
    if cols is not None and cols.lstrip() != '':
        new_cols = new_cols + cols.split(', ')

    if normalized_table_name in TABLE_COLUMNS:
        # Set of new columns
        new_cols_set = set(new_cols)

        # Set of existing columns
        existing_cols_set = TABLE_COLUMNS[normalized_table_name]

        # Find the difference between existing and new columns
        difference = new_cols_set.symmetric_difference(existing_cols_set)

        # if difference: # Warning in debug mode
        #    If there is a difference, a message is printed on the screen.
        #       print(f"Difference in table '{table_name}': {difference}")

        # Update the acumulated columns for the existant table
        TABLE_COLUMNS[normalized_table_name].update(new_cols)
    else:
        # Create new entrance for the table
        TABLE_COLUMNS[normalized_table_name] = set(new_cols)

    # Ensures that the table is marked as generated
    HASH_TABLE_TABLES_GENERATED[normalized_table_name] = 1


def update_table_creation_in_sql(sql, table_name):
    """
    Updates the SQL creation statement for a specified table by rearranging columns
    and integrating any changes into an existing SQL script.

    This function ensures that the primary key is placed at the beginning of the
    column list and foreign keys at the end when reconstructing the CREATE TABLE
    statement.

    Parameters:
    - sql (str): The current complete SQL script containing one or more table definitions.
    - table_name (str): The name of the table to update or create within the SQL script.

    Globals:
        TABLE_COLUMNS (dict): A global dictionary where keys are table names
        and values are the columns and their specifications.

    Returns:
    - new_table_sql (str): The newly constructed CREATE TABLE SQL statement for the specified table.
    - updated_sql (str): The updated SQL script with the old table definition removed and
      replaced by the new CREATE TABLE statement.

    Notes:
    - Assumes that `TABLE_COLUMNS` is a dictionary containing the table name as keys,
      and lists of column definitions as values.
    - The function utilizes regular expressions to strip out existing table
      definitions to avoid duplicates when updating the script.
    """
    pk = None
    foreign_keys = []
    other_columns = []
    for col in TABLE_COLUMNS[table_name]:
        if 'PRIMARY KEY' in col:
            pk = col
        elif 'FOREIGN KEY' in col:
            foreign_keys.append(col)
        else:
            other_columns.append(col)
    # Make sure the PRIMARY KEY is at the beginning and FOREIGN KEYS at the end
    ordered_cols = [pk] + other_columns + foreign_keys
    combined_cols = ', '.join(ordered_cols)
    new_table_sql = f"CREATE TABLE {table_name} ({combined_cols});"
    # Remove any existing table definition in SQL using regex
    table_pattern = re.compile(rf"CREATE TABLE {table_name} \(.*?\);", re.DOTALL)
    sql = re.sub(table_pattern, "", sql)

    # Add the new definition to SQL sentence
    sql += new_table_sql + "\n"  # Add new line to split definitions

    return new_table_sql, sql



def create_primary_key(table_name, ns):
    """
    Args:
        table_name: Name of the table from which the primary key will be created

    Returns:
        string: A string containing de primary key definition
    """
    normalized_table_id = sql_normalize(table_name + 'Id', ns) + ' bigint PRIMARY KEY NOT NULL'
    return normalized_table_id


def process_element(el, parent, fail, normalize, counter_choice, cols, ns, root,
                    dict_relationships):
    """
    Processes an XML element to generate or update the column definitions for an SQL table,
    potentially handling foreign key relationships and complex types.

    Documentation can be found here: <file://./docs/process_element.md>

    Args:
        el: The XML element to process, which contains the information needed to define a table column.
        parent: The parent element in the XML hierarchy, providing context for nested or hierarchical data.
        fail: A boolean flag indicating whether the function should raise an exception if an invalid data type is encountered.
        normalize: A boolean that determines whether column names should be normalized, potentially transforming them to a standard format.
        counter_choice: Value greater 0, indicates if the current element originates from a `<choice>` structure.
        cols: A string representing the list of columns that have already been defined for the current table context.
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.
        root: The root element of the XML document, providing a starting point for certain type checks or hierarchy validations.
        dict_relationships: A dictionary used to manage and store relationships between XML elements and their corresponding SQL representations.

    Globals:
        DEFX2SQLSERVER (dict): A global dictionary that stores SQL Server Data Types
        USER_TYPES (dict): A global dictionary dwhere the mapping of element and type names to the user-defined
                           types within the application is store.
        TABLE_COLUMNS (dict): A global dictionary where keys are table names
        and values are the columns and their specifications.
        HASH_TABLE_TABLES_GENERATED (dict): A global dictionaru that keeps a trace for generated tables
        NAMESPACE_DICT (dict): A global dictionary that store namespaces in format XMLS_PREFIX : XMLS

    Returns:
        A string representing the updated list of columns for the SQL table, including any new or modified definitions based on the processed element.

    """
    ns_table_name = sql_normalize(el.get('name'), ns)
    # Validate if a table was created
    if ns_table_name in HASH_TABLE_TABLES_GENERATED and parent is not None and parent != '':
        table_name = el.get('name')
        cols = create_fk_field(el, cols, parent, table_name, table_name, counter_choice, dict_relationships, ns)
        return cols

    # Validate if "el" is a complex type
    if parent is not None and parent.lstrip() != "" and is_complex_type(root, ns, el.get('name')):
        cols = create_fk_field(el, cols, parent, el.get('name'), el.get('name'), counter_choice, dict_relationships, ns)
        return cols

    thisType = el.get('type') or el.get('ref') or 'string'  # thisType will be set to the first truthy value found
    # among el.get('type'), el.get('ref'), or 'string'. If neither of the values for the 'type' or 'ref' keys is truthy,
    # then 'thisType' will be 'string'

    if (el.get('ref') is not None):  # Of course, 'thisType' is 'ref' type too. See the previos instruction
        cols = create_fk_field(el, cols, parent,
                               el.get('name') or el.get('ref'), # By example in some cases ds:Signature not exists in xsd file. Exist in extern file
                               thisType, counter_choice, dict_relationships, ns)
        return cols

    # Removes the prefix from the data type
    k = thisType.replace(NAMESPACE_DICT[ns], '')

    # Determines whether the data type is a data type of the Database Server being worked with
    # or is a user-defined data type
    sql_type = DEFX2SQLSERVER.get(k) or USER_TYPES.get(sql_normalize(k, ns)) or None

    if not sql_type and fail:  # Raise an exception if DataType is invalid and fail was setted in True in arguments program
        raise InvalidXMLType("%s is an invalid XSD type." % (NAMESPACE_DICT[ns] + thisType))
    elif sql_type:  # If DataType is valid
        if not sql_type in DEFX2SQLSERVER.values():  # Valid again, against valid data types in DBSchema
            sql_type = DEFX2SQLSERVER.get(sql_type)

        if not sql_type and fail:  # Raise an exception if DataType is invalid and fail was setted in True in arguments program
            raise InvalidXMLType("%s is an invalid Database Schema type." % (NAMESPACE_DICT[ns] + thisType))

        col_name = el.get('name') or el.get('ref')
        if col_name is None:
            return cols

        if normalize:
            col_name = sql_normalize(col_name, ns)

        str_counter_choice = generate_str_counter_choice(counter_choice)
        col_definition = "%s %s" % (col_name, sql_type)
        col_definition = get_nullable_attribute_from_col_definition(counter_choice, el, col_definition)
        if not cols:  # if NOT exists  columns previously definided, for this table
            cols = col_definition
        else:  # if exists  columns previously definided, for this table
            cols += ", %s" % col_definition
        return cols

    if parent is not None and parent.lstrip() != "" and thisType is not None and is_complex_type(root, ns,
                                                                                                 thisType if isinstance(
                                                                                                     thisType,
                                                                                                     str) else thisType.get(
                                                                                                     'name')):
        cols = create_fk_field(el, cols, parent, el.get('name'), thisType, counter_choice, dict_relationships, ns)
        return cols


def generate_str_counter_choice(counter_choice):
    """
    Generates a commented string containing the value of counter_choice if it is greater than 0.
    If counter_choice is 0 or less, returns an empty string.

    Parameters:
        - counter_choice (int): The value to be evaluated.

    Returns:
        - str: The generated string or an empty string.
    Note:
        - It is important that there are no spaces to the right of the data type and that the
        counter_choice specification starts with the string "/*counter_choice=" and ends with "=/".
        This will make it easier to specify the choice fields for the ERD and for the table fields
        in the CREATE TABLE statements.
        See its use in the create_table_definitios_in_plantuml_diagram function
    """
    return f'{CONSTANT_COUNTER_CHOICE_STR}{counter_choice}*/' if counter_choice > 0 else ''


def create_fk_field(el, cols, parent, field_fk_name, table_reference_name, counter_choice, dict_relationships, ns):
    """
    This function is responsible for creating foreign key fields as part of SQL table creation or modification.

    Documentation can be found here: <file://./docs/create_fk_field.md>

    Parameters:
        el:
        cols:
        parent:
        field_fk_name:
        table_reference_name:
        counter_choice:
        dict_relationships:
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.

    Returns:

    """

    fk_field_normalized = sql_normalize(field_fk_name + 'Id', ns)
    parent_table_fk = get_parent_table_name(parent, ns)
    table_reference_name_fk_normalized = sql_normalize(table_reference_name, ns)
    foreign_key_name = get_foreign_key_name(fk_field_normalized, parent_table_fk)

    cardinality = get_cardinality(el)
    if cardinality_right_is_n(cardinality):
        foreign_key_name_update = get_foreign_key_name(field_fk_name, parent_table_fk)

        # Inverse relationship. Useful in create_relationships_in_plantuml_diagram function
        # See documentation here: <file://./docs/create_relationships_in_plantuml_diagram.md>
        remove_relationship_dict_relationships(dict_relationships, parent_table_fk, foreign_key_name)
        add_relationship_dict_relationships(dict_relationships, parent_table_fk, foreign_key_name_update,
                                            table_reference_name_fk_normalized, cardinality,
                                            replace_previous_relationship=True)

        # Note. - It is assumed that there are no equal tag names in nested hierarchies. Therefore, it is always "0"
        number = 0
        new_col_name = parent_table_fk + 'Id' + '_' + str(number)
        new_col_definition = new_col_name + ' bigint'
        new_col_definition = get_nullable_attribute_from_col_definition(counter_choice, el, new_col_definition)

        # Create table with primary key and foreign key, at least. Primary key will ber created in
        # create_table_in_sql_sentence function. If the table already exists, it's no matters, so the
        # new column (the foreign key), will be added to the previous columns. Repeated fields are
        # ignorated in create_table_in_sql_sentence function
        cols_update = new_col_definition + ", " + "CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s(%s)" % (
            foreign_key_name_update, new_col_name, parent_table_fk, parent_table_fk + 'Id')
        create_table_in_sql_sentence(cols_update, table_reference_name, ns)

        if not cols or cols.lstrip() == '':
            # So that, in the worst case, you have at least one column. Anyway, in the create_table function,
            # the repeated fields are filtered, in case if you were to generate again
            # cols = create_primary_key(table_reference_name)
            cols = create_primary_key(parent, ns)

    else:  # if not cardinality_right_is_n(cardinality):
        # Normal relationship. Useful in create_relationships_in_plantuml_diagram function
        # See documentation here: <file://./docs/create_relationships_in_plantuml_diagram.md>
        add_relationship_dict_relationships(dict_relationships, parent_table_fk, foreign_key_name,
                                            table_reference_name_fk_normalized, cardinality)

        new_col_definition = fk_field_normalized + ' bigint'
        new_col_definition = get_nullable_attribute_from_col_definition(counter_choice, el, new_col_definition)

        comma_space = ', '
        if not cols or cols.lstrip() == '':
            cols = ""
            comma_space = ''
        cols += "%s%s" % (comma_space, new_col_definition)
        cols += ", CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s(%s)" % (
            foreign_key_name, fk_field_normalized, table_reference_name_fk_normalized,
            table_reference_name_fk_normalized + 'Id')

        # Create table with primary key, at least. Primary key will ber created in
        # create_table_in_sql_sentence function. If the table already exists, it's no matters,
        # so the new column, will be added to the previous columns. Repeated fields are
        # ignorated in create_table_in_sql_sentence function
        create_table_in_sql_sentence('', table_reference_name, ns)

    return cols


def get_nullable_attribute_from_col_definition(counter_choice, el, col_definition):
    """
    Modifies and returns the column definition based on the nullability analysis.

    This function appends 'NULL' to the column definition if the counter_choice is greater than 0.
    Otherwise, it performs a nullability analysis using the get_nullable_attribute function.

    Parameters:
        - counter_choice (int): A counter that influences whether 'NULL' should be appended directly.
        - el (Any): An element that is part of the nullability analysis.
        - col_definition (str): The initial column definition string.

    Returns:
        - str: The modified column definition, with nullability attributes updated.
    """
    if counter_choice > 0:
        col_definition += f' NULL{generate_str_counter_choice(counter_choice)}'
    else:
        # Nullability analisis
        col_definition = get_nullable_attribute(el, col_definition)
    return col_definition


def get_nullable_attribute(el, col_definition):
    """
    Determines and adjusts the nullable attribute of a database column definition
    based on XML element attributes.

    This function verifies the 'minOccurs' and 'nillable' attributes of an XML
    element and modifies the given column definition accordingly.

    - If `minOccurs="0"`, the element is optional and should allow NULL.
    - If `nillable="true"`, the element can be explicitly NULL (`xsi:nil="true"` in XML).
    - If both `minOccurs="0"` and `nillable="true"`, the column allows NULL.
    - If `minOccurs="1"` and `nillable="false"`, the column is required (`NOT NULL`).

    Parameters:
        el (dict): A dictionary representing the attributes of the XML element.
        col_definition (str): The initial column definition string.

    Returns:
        str: The modified column definition string with 'NULL' or 'NOT NULL'.

    Examples:
        - element = {"minOccurs": "0", "nillable": "false"}
        - print(get_nullable_attribute(element, "CustomerName VARCHAR(255)"))
        - Output:CustomerName VARCHAR(255) NULL
        -
        - element = {"minOccurs": "1", "nillable": "true"}
        - print(get_nullable_attribute(element, "Email VARCHAR(100)"))
        - Output:Email VARCHAR(100) NULL
        -
        - element = {"minOccurs": "1", "nillable": "false"}
        - print(get_nullable_attribute(element, "UserID INT"))
        - Output:UserID INT NOT NULL
        -
        - element = {"minOccurs": "0", "nillable": "true"}
        - print(get_nullable_attribute(element, "Address NVARCHAR(500)"))
        - Output:Address NVARCHAR(500) NULL

    """
    # Get attributes with default values
    min_occurs = int(el.get("minOccurs", "1"))  # Default 1, convert to int
    nillable = el.get("nillable", "false").lower() == "true"  # Convert to boolean

    # Determine NULL or NOT NULL
    if min_occurs == 0 or nillable:
        col_definition += " NULL"
    else:
        col_definition += " NOT NULL"

    return col_definition



def ends_with_integer(s):
    # Reverse the string to make the final part easier to read
    # Examples:
    # print(ends_with_integer("abcd123"))       # Returns True, 123
    # print(ends_with_integer("abcd"))          # Returns False, ''
    # print(ends_with_integer("abcd123xyz"))    # Returns  False, ''
    # print(ends_with_integer("number45"))      # Returns True, 45
    reversed_string = s[::-1]
    integer_part = ""

    # Iterate through the string in reverse, stopping when the character is not a digit.
    for char in reversed_string:
        if char.isdigit():
            integer_part = char + integer_part
        else:
            break

    # Returns True if we get an integer and it is not empty
    return (integer_part != "" and integer_part.isdigit(), integer_part)


def get_foreign_key_name(field_fk_name, parent_table_fk):
    """
    Constructs and returns a foreign key name based on a field name and its parent table.

    This function generates a foreign key name using the format "FK_<parent_table>_<field>",
    which is commonly used in database schemas to maintain consistency and clarity in naming
    conventions for foreign keys.

    Parameters:
        field_fk_name (str): The name of the field that serves as the foreign key.
        parent_table_fk (str): The name of the parent table to which the foreign key is related.

    Returns:
        str: A string representing the constructed foreign key name using the format "FK_<parent_table>_<field>".
    """
    foreign_key_name = "FK_%s_%s" % (parent_table_fk, field_fk_name)
    return foreign_key_name


def remove_relationship_dict_relationships(dict_relationships, parent_table, foreign_key_name):
    """
    Removes a relationship entry from a dictionary of database relationships.

    This function deletes an entry from a dictionary that stores relationships between
    tables in a database. Each relationship is identified by a key that combines the
    parent table name and foreign key name. If the key exists in the dictionary, the
    corresponding relationship is removed.

    Parameters:
        dict_relationships (dict): A dictionary storing relationships, keyed by "parent_table;foreign_key_name",
                                   where each key refers to a specific foreign key relationship.
        parent_table (str): The name of the parent table involved in the relationship.
        foreign_key_name (str): The name of the foreign key in the parent table.

    Returns:
        None
    """
    # Verify key in dictionary
    key = parent_table + ";" + foreign_key_name
    if key in dict_relationships:
        # Add key-value
        del dict_relationships[key]


def add_relationship_dict_relationships(dict_relationships, parent_table, foreign_key_name, table_reference_name,
                                        cardinality, replace_previous_relationship=False):
    """
    Adds or replaces a relationship entry in a dictionary of database relationships.

    This function updates a dictionary that stores relationships between tables in a database.
    Each relationship is keyed by a combination of the parent table name and foreign key name.
    If the key does not exist in the dictionary, or if the 'replace_previous_relationship' flag
    is set to True, the function adds or replaces the entry with the specified relationship details.

    Parameters:
        dict_relationships (dict): A dictionary storing relationships, keyed by "parent_table;foreign_key_name",
                                   with values as lists of tuples containing the table reference name and cardinality.
        parent_table (str): The name of the parent table involved in the relationship.
        foreign_key_name (str): The name of the foreign key in the parent table.
        table_reference_name (str): The name of the table being referenced in the relationship.
        cardinality (str): The cardinality of the relationship (e.g., "one-to-many", "many-to-one").
        replace_previous_relationship (bool, optional): Flag indicating if the existing relationship should
                                                        be replaced if the key already exists. Defaults to False.

    Returns:
        None
    """
    # Verify key in dictionary
    key = parent_table + ";" + foreign_key_name
    if key not in dict_relationships or replace_previous_relationship:
        # Add key-value
        dict_relationships[key] = [(table_reference_name, cardinality)]


def cardinality_right_is_n(cardinality):
    """
    Determines if the right side of a cardinality indicates a "many" relationship.

    Args:
        cardinality (str): A string representing the cardinality, typically in the form "min..max".

    Returns:
        bool: True if the right side of the cardinality is '*' or an integer greater than 1,
              indicating a "many" relationship; otherwise, False.
    """
    s = cardinality.split('..')
    index = 1
    if (s[1] is not None and (s[index] == '*' or s[index].isdigit() and int(s[index]) > 1)):
        return True
    return False


def get_cardinality(element):
    """
    Deduces cardinality from minOccurs and maxOccurs attributes in an XSD element.

    Args:
        element (Element): An XML element from an XSD file for which cardinality is determined.
                            It should have 'minOccurs' and 'maxOccurs' attributes.

    Returns:
        str: A string representing the cardinality. Common formats include "1..*", "0..1",
             or a specific range like "0..5". The '*' symbol is used to denote an unbounded
             maximum.
    """
    # Get minOccurs and maxOccurs values, with default values
    min_occurs = int(element.get('minOccurs', '1'))  # Por defecto 1
    max_occurs = element.get('maxOccurs', '1')  # Por defecto 1

    # Handling the "unbounded" case
    if max_occurs == 'unbounded':
        max_occurs = '*'
    else:
        max_occurs = int(max_occurs)

    # Detect specific cardinalities
    if min_occurs == 1 and max_occurs == '*':
        return "1..*"
    if min_occurs == 0 and max_occurs == 1:
        return "0..1"

    # Other cardinalities
    return f"{min_occurs}..{max_occurs}"


def find_simple_type(xsd_tree, ns, type_name):
    """
    Look for simpleType in XSD schema.

    Args:
        xsd_tree: Parsed tree from XSD (ElementTree).
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.
        type_name: Type name looked.

    Returns:
        Finded element or None.
    """
    # Look for all simpleTypes in XSD
    simple_types = xsd_tree.findall(f".//{ns}simpleType")

    for ct in simple_types:
        if ct.get("name") == type_name:
            return ct
    return None


def find_complex_type(xsd_tree, ns, type_name):
    """
    Look for simpleType in XSD schema.

    Args:
        xsd_tree: Parsed tree from XSD (ElementTree).
        ns: The namespace used in the XML document, which may be necessary for correctly resolving element types or references.
        type_name: Type name looked.

    Returns:
        Finded element or None.
    """
    if type_name is None:
        return None

    # Look for all complexTypes in XSD
    complex_types = xsd_tree.findall(f".//{ns}complexType")

    for ct in complex_types:
        if ct.get("name") == type_name:
            return ct
    return None


def get_parent_table_name(parent, ns):
    """
    Determines the normalized name of a parent table from an SQL element.

    This function extracts and normalizes the name of a parent table given
    an SQL element. It uses a helper function to apply normalization based
    on a specified namespace.

    Parameters:
    - parent: The SQL element representing a parent table, possibly in a raw
      or complex form requiring normalization.
    - ns: The namespace or context used for normalizing the table name. This
      could include schema information or other relevant context needed by
      the normalization process.

    Returns:
    - str: A string representing the normalized name of the parent table. If
      the `parent` element is `None`, it returns an empty string.

    Behavior:
    - Checks if the `parent` element is not `None`.
    - Normalizes the `parent` element using the `sql_normalize` function,
      which applies context provided by `ns`.
    - If `parent` is `None`, directly returns an empty string, indicating no
      parent table name could be derived.

    Examples:
        If `parent` is a complex identifier like `scc:Table`, and `ns` provides
        context to strip or modify the identifier, the function returns the
        simplified version like `Table`.

    Dependencies:
    - This function relies on the implementation of the `sql_normalize` helper
      function to perform the actual normalization process.

    Notes:
    - Assumes that `sql_normalize` correctly interprets and processes the provided
      SQL elements and namespaces.
    - The exact behavior of `sql_normalize` is crucial in determining the output,
      thus it is assumed to be correctly implemented.

    """

    parent_table = ''
    if (parent is not None):
        parent_table = sql_normalize(parent, ns)
    return parent_table


def build_user_types(ns, root_element):
    """
    Constructs a user-defined types dictionary based on the type definitions from an XML document.

    This function iterates over the `<element>` and `<simpleType>` elements in the given XML document,
    populating the `USER_TYPES` dictionary with normalized keys derived from the names of these elements,
    mapping them to internally defined types within the application.

    Args:
        ns (str): The namespace prefix used in the XML document, applied for locating specific elements.
        root_element (Element): The root element of the XML document containing the elements and types
                                to be processed.

    Global Variables:
        USER_TYPES (dict): A global dictionary where the mapping of element and type names to the user-defined
                           types within the application is stored.
        DEFX2SQLSERVER (dict): A global dictionary that stores SQL Server Data Types
        NAMESPACE_DICT[ns] (str): A prefix (XMLS_PREFIX) to be removed from XML type names before performing the mapping.

    Considerations:
        - The function requires `sql_normalize` to be a function that normalizes (likely cleans or standardizes)
          the names of XML elements for internal use.
        - It will remove the `NAMESPACE_DICT[ns]` (`XMLS_PREFIX`) from type names before performing the mapping.

    """

    # Translates the information about elements and types in an XML document to an internal structure that is compatible
    # with SQL Server or the Database Server you are working with
    for el in root_element.findall(ns + 'element'):
        if el.get('name') and el.get(
                'type'):  # checks if the found `<element>` element has the attributes 'name' and 'type'
            USER_TYPES[sql_normalize(el.get('name'), ns)] = DEFX2SQLSERVER.get(
                el.get('type').replace(NAMESPACE_DICT[ns], ''))

    # Looks for elements "simpleType" and gets its data type from atribute "base" from restriction node and loads
    # this value in USER_TYPES dictionary
    # By example <xs:simpleType name="AttachmentEncodingType">
    # 		<xs:restriction base="xs:string">
    # Here, this code fragment gets "string"
    for el in root_element.findall(ns + 'simpleType'):
        restr = el.find(ns + 'restriction')
        USER_TYPES[sql_normalize(el.get('name'), ns)] = restr.get('base').replace(NAMESPACE_DICT[ns], '')


""" Do it
"""


def create_graph(arr_create_tables):
    """
    Constructs a directed graph representing table dependencies from SQL CREATE TABLE statements.

    This function processes a list of SQL CREATE TABLE statements to identify table dependencies
    and builds a directed graph (using NetworkX's `DiGraph`) where nodes represent tables and edges
    represent dependencies (i.e., references to other tables).

    Parameters:
    - arr_create_tables (list of str): A list of strings, each representing a SQL CREATE TABLE statement.
      These statements are analyzed to determine table names and their referenced tables.

    Returns:
    - DiGraph: A NetworkX directed graph where each node is a table and each directed edge from
      one node to another indicates a dependency (a "references" relationship) from the first table
      to the second.

    Behavior:
    - Iterates through each SQL create table statement.
    - Extracts the table name and its referenced tables using the `analize_instruction` function.
    - Adds each table as a node in the directed graph.
    - For each referenced table, adds a directed edge from the table to the referenced table.

    Dependencies:
    - This function assumes the presence and correct implementation of:
      - `analize_instruction(instruction)`: A helper function that returns the table name and a list
        of referenced tables from a SQL statement.
    - It also requires NetworkX for creating and managing the graph structure.

    Example:
        Given SQL statements that define tables and specify foreign key relationships,
        this function returns a graph that represents these relationships.

    Note:
    - Empty or malformed SQL statements are ignored.
    """

    graph = nx.DiGraph()
    for instruction in arr_create_tables:
        table_name, referenced_tables = analize_instruction(instruction)
        if (table_name == ''):
            continue
        graph.add_node(table_name)
        for table_ref in referenced_tables:
            graph.add_edge(table_name, table_ref)
    return graph


def analize_instruction(instruction):
    """
    Analyzes a SQL CREATE TABLE statement to extract the table name and referenced foreign tables.

    This function processes a single SQL CREATE TABLE statement to determine the primary table name
    and any tables it references through foreign key constraints. It outputs the table name and a
    list of referenced table names.

    Parameters:
    - instruction (str): A SQL CREATE TABLE statement provided as a string, which may include
      foreign key definitions pointing to other tables.

    Returns:
    - tuple: A tuple containing:
      - (str): The primary table's name extracted from the instruction.
      - (list of str): A list of table names that the primary table references through
        foreign key relationships.

    Behavior:
    - Utilizes `get_table_name(instruction)` to extract the primary table name.
    - Parses the statement to find 'REFERENCES' keywords and extracts table names that are
      referenced as foreign keys.
    - If no table name or references are found, returns an empty string and an empty list
      respectively.

    Edge Cases:
    - If no table name is found in the instruction, the function returns an empty string for
      the table name and an empty list for referenced tables.

    Example:
        For an input like "CREATE TABLE orders (id INT, user_id INT REFERENCES users(id));",
        the function returns ('orders', ['users']).

    Notes:
    - Assumes SQL is well-formed with 'REFERENCES' indicating foreign key references.
    - Ignores malformed statements or those without references by appending an empty string
      if no references are found after parsing.
    """

    table_name = get_table_name(instruction)
    if (table_name is None or table_name.strip() == ''):
        return '', []
    array_foreign_keys = instruction.replace('\n', '').split('REFERENCES')
    referenced_tables = []
    for item in enumerate(array_foreign_keys[1:]):
        new_item = item[1].lstrip()
        index = new_item.find('(')
        if index != -1:
            new_item = new_item[:index]
            referenced_tables.append(new_item)
    if (len(referenced_tables) == 0):
        referenced_tables.append('')

    return table_name, referenced_tables


def get_table_name(instruction, pref='CREATE TABLE '):
    table_name = ''
    match = re.search(rf"{pref}(\S+)", instruction.lstrip())
    if match:
        table_name = match.group(1)
    return table_name


def break_cycles(graph):
    """
    It breaks cycles in the graph, deleting an edge in every cycle detected.
    Returns an acyclic graph.
    Parameters:
        graph: Graph that may possibly have cycles
    Return:
        graph_copy: graph without cycles
    """
    graph_copy = graph.copy()
    try:
        while True:
            cycle = nx.find_cycle(graph_copy)
            edge_to_remove = cycle[0]  # Choose the first edge of the cycle
            graph_copy.remove_edge(*edge_to_remove)
            print(f"Removed edge to break cycle: {edge_to_remove}")
    except nx.NetworkXNoCycle:
        pass  # there are no mor cycles
    return graph_copy


def create_plantuml_diagram(graph, arr_create_tables, dict_relationships):
    """
    Generates a complete Entity Relationship PlantUML Diagram from SQL table
    definitions and relationships.

    This function combines SQL table definitions and their relationships to produce
    a Entity Relationship PlantUML Diagram. It prints the complete syntax required to
    render the diagram, starting with `@startuml` and ending with `@enduml`. It utilizes
    helper functions to convert each table definition and relationship into PlantUML
    format.

    Parameters:
    - graph: The graph structure that assists in determining the relationships and order
      of table rendering. The specific structure and type are not defined here and depend
      on implementation details of related helper functions.
    - arr_create_tables (list of str): A list of SQL CREATE TABLE statements, where each
      string represents a table's definition.
    - dict_relationships (dict): A dictionary mapping relationships between the tables. The
      specific structure and types of keys and values depend on the implementation of the
      relationships helper function.

    Behavior:
    - Begins the diagram with the `@startuml` statement.
    - Calls `create_table_definitions_in_plantuml_diagram(arr_create_tables)` to generate
      PlantUML entity definitions from SQL table definitions.
    - Calls `create_relationships_in_plantuml_diagram(graph, dict_relationships)` to map the
      relationships between entities in PlantUML format.
    - Ends the diagram with the `@enduml` statement, marking the close of the PlantUML code.

    Note:
    - This function directly prints to the console; it does not return any value.
    - It utilizes external helper functions to convert and print each part of the diagram.

    Example:
        Given a set of SQL tables and relationships, it outputs a full Entity Realtionship
        PlantUML Diagram representation that can be used for generating UML visualizations.
    """
    print("@startuml")

    create_table_definitios_in_plantuml_diagram(arr_create_tables)

    create_relationships_in_plantuml_diagram(graph, dict_relationships)

    print("@enduml")


def create_table_definitios_in_plantuml_diagram(arr_create_tables):
    """
    Converts SQL CREATE TABLE definitions into Entity Relationship PlantUML Diagram.

    This function takes a list of SQL CREATE TABLE statements, parses each statement
    to extract table and field names along with their data types, and prints a Entity
    Relationship PlantUML Diagram. It handles primary keys and foreign key constraints
    by prefixing fields with specific symbols: "+" for primary keys and "-" for foreign
    keys.

    Parameters:
    - arr_create_tables (list of str): A list of strings, each representing a SQL CREATE TABLE
      statement to be converted into a PlantUML entity diagram.

    Behavior:
    - Extracts the table name by parsing each CREATE TABLE statement.
    - Captures the content within the parentheses to identify the table's fields.
    - Distinguishes between regular fields, primary keys, and foreign key constraints.
    - Outputs each table as an "entity" in PlantUML, with appropriate notations for keys.
      - "+" for primary key fields.
      - "- " prefix added to the preceding field for foreign key constraints.

    Note:
    - This function directly prints to the console; it does not return any value.
    - It assumes the CREATE TABLE statements are structured in a typical SQL format.

    Example input:
        [
            "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100), age INT);",
            "CREATE TABLE orders (order_id INT, user_id INT, CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id));"
        ]

    Example output:
        entity "users" {
            + id: INT
            name: VARCHAR(100)
            age: INT
        }
        entity "orders" {
            order_id: INT
            - user_id: INT
        }
    """
    for i, create_table in enumerate(arr_create_tables, start=1):
        table_name = get_table_name(create_table)

        # Extract content inside parentheses
        content = re.search(r'\((.*)\)', create_table, re.DOTALL).group(1)

        # Write the entity and open the key of the entity
        print("entity \"" + table_name.strip() + "\" {")

        # Separated by commas
        elements = content.split(',')
        i = 0
        lines = []
        for element in elements:
            # Using split with a maximun of 1 division to separate in two parts: field name and data type
            parts = element.split(maxsplit=10)
            field_name = parts[0]
            data_type = parts[1]
            if field_name.strip().upper() == 'CONSTRAINT' and len(parts) >= 6:
                if parts[2].strip().upper() == 'FOREIGN' and parts[3].strip().upper() == 'KEY' and parts[
                    5].strip().upper() == 'REFERENCES' and i > 0:
                    if not lines[i - 1].startswith("- "):
                        lines[i - 1] = "- " + lines[i - 1]
            elif len(parts) == 3 and parts[2].strip().strip().lower().startswith('null'):
                # For the correct use of this "if" statement, it is important that there are no blank spaces after
                # the data type and the current_choice specification. See Note on the "generate_str_counter_choice"
                # function
                lines.append(f"{field_name}: {data_type}{get_substring_from(parts[2].strip().strip().lower(), CONSTANT_COUNTER_CHOICE_STR)}")
                i += 1
            elif len(parts) == 4 and parts[2].strip().lower() == 'not' and parts[3].strip().lower().startswith('null'):
                # For the correct use of this "if" statement, it is important that there are no blank spaces after
                # the data type and the current_choice specification. See Note on the "generate_str_counter_choice"
                # function
                lines.append(f"{field_name}: {data_type}{get_substring_from(parts[3].strip().strip().lower(), CONSTANT_COUNTER_CHOICE_STR)}")
                i += 1
            else:
                if len(parts) == 2:
                    lines.append(f"{field_name}: {data_type}")
                    i += 1
                else:
                    if len(parts) >= 4:
                        if parts[2].strip().upper() == 'PRIMARY' and parts[3].strip().upper() == 'KEY':
                            lines.append(f"+ {field_name}: {data_type}")
                            i += 1
        # Print the fields with its data types
        for line in lines:
            print(line)

        # Close the key of the entity
        print("}")

def get_substring_from(string, substring):
    """
    Returns the part of the string starting from the beginning of the substring to the end.
    If the substring is not found, returns None.

    Parameters:
        string (str): The string to search within.
        substring (str): The substring to find.

    Returns:
        str or string empty: The part of the string from the substring to the end, or string empty if the
        substring is not found.
    """
    index = string.find(substring)  # Find the starting index of the substring
    if index != -1:  # If the substring exists
        return string[index:]  # Return from the index to the end
    else:
        return ''  # Return string empty if the substring is not found

def create_relationships_in_plantuml_diagram(graph, dict_relationships):
    """
    The purpose of the function is to create and print PlantUML-compatible relationship
    representations between nodes of the `graph` according to specified relationships in `dict_relationships`.

    Documentation can be found here: <file://./docs/create_relationships_in_plantuml_diagram.md>

    Args:
        graph: represents a directed graph
        dict_relationships: dictionary of relationships

    Returns:
    """
    for node in graph.nodes():
        if (node is None):
            continue
        if node.strip() == '':
            continue

        # Get all nodes that this node points to (sucessors)
        successors = list(graph.successors(node))

        # Get all nodes pointing to this node (predecessors)
        predecessors = list(graph.predecessors(node))

        for p in predecessors:
            if (p is not None and p.strip() != ''):
                founded = False
                for key, relationships in dict_relationships.items():
                    parent_table = key.split(";")[0]
                    if (parent_table != p):
                        continue

                    # Print relationship
                    for table_reference_name, cardinality in relationships:
                        if table_reference_name == node:
                            founded = True
                            s = cardinality.split('..')
                            left_cardinality = translate_cardinality_to_plantuml_notation(s, 0)
                            right_cardinality = translate_cardinality_to_plantuml_notation(s, 1)
                            print(p + f" {left_cardinality}--{right_cardinality} " + node)

                # For the case where the cardinality is inverse due to the case of 1..* or o..*
                if not founded:
                    # Print inverse relationship
                    for key, relationships in dict_relationships.items():
                        parent_table = key.split(";")[0]
                        if (parent_table != node):
                            continue
                        for table_reference_name, cardinality in relationships:
                            if table_reference_name == p:
                                founded = True
                                s = cardinality.split('..')
                                left_cardinality = translate_cardinality_to_plantuml_notation(s, 0)
                                right_cardinality = translate_cardinality_to_plantuml_notation(s, 1)
                                print(node + f" {left_cardinality}--{right_cardinality} " + p)

                if not founded:
                    # Print default relationship
                    print(p + " ||--o" + "{ " + node)

        print()  # white line to separate every node


def translate_cardinality_to_plantuml_notation(s, index):
    """
    Translates a given cardinality from a string to PlantUML notation.

    The function takes a character from a sequence representing a cardinality
    and translates it to its corresponding symbol in the PlantUML notation used
    to represent multiplicity limits in class diagrams.

    Args:
        s (str): The string containing the cardinality representation.
        index (int): The index of the character in the string `s` to be converted.

    Returns:
        str: The equivalent PlantUML notation for the cardinality character
        at the specified index. Possible return values are '||', 'o', 'o{', or '|{'.

    Examples:
    translate_cardinality_to_plantuml_notation("01*", 0) # Returns 'o'
    translate_cardinality_to_plantuml_notation("01*", 2) # Returns 'o{'
    """
    cardinality_plantuml = '||'
    if s[index] == '0':
        cardinality_plantuml = 'o'
    elif s[index] == '*':
        cardinality_plantuml = 'o{'
    elif s[index].isdigit() and int(s[index]) > 1:
        cardinality_plantuml = '|{'

    return cardinality_plantuml


def load_user_types_to_dictionary(file_path):
    """
    Loads user-defined types from a file into a dictionary.

    This function reads a file where each line contains a key-value pair
    separated by a colon. It parses these pairs and stores them in a dictionary
    with the trimmed keys and values.

    Args:
        file_path (str): The path to the text file containing the key-value
        pairs separated by colons.

    Returns:
        dict: A dictionary containing the key-value pairs with stripped keys
        and values. Returns `None` if an error occurs during file reading.

    Raises:
        Any exceptions that occur while attempting to open or read the file
        are caught and the function returns `None`.

    Examples:
        load_user_types_to_dictionary('user_types.txt')
        # Returns something like {'	<xs:simpleType name="TextMax10Type">': 'xs_string', 'DoubleUpToEightDecimalType': 'xs:double'}
    """
    types = {}
    try:
        with open(file_path, 'r') as text_file:
            for line in text_file:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    types[key] = value
        return types
    except:
        return None



def create_sql_from_tables_columns_dictionary():
    """
    Generates an SQL string to create tables based on a global table-columns dictionary.

    This function iterates over a dictionary (assumed to be named `TABLE_COLUMNS`
    and defined globally) that contains table names as keys. It uses this information
    to generate SQL statements for creating the corresponding tables. The SQL
    statements are accumulated and returned as a single string.

    Globals:
        TABLE_COLUMNS (dict): A global dictionary where keys are table names
        and values are the columns and their specifications.

    Returns:
        str: A string containing the SQL statements for creating all the tables
        defined in the `TABLE_COLUMNS` dictionary.

    Note:
        This function relies on another function `update_table_creation_in_sql`
        which is expected to take the current SQL string and table name, and
        update the SQL statement accordingly.

    Examples:
        Assuming TABLE_COLUMNS = {'users': {'id': 'INT PRIMARY KEY', 'name': 'VARCHAR(100)'}},
        create_sql_from_tables_columns_dictionary() might return:
        "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));"
    """
    sql = ''
    for table_name in TABLE_COLUMNS.keys():
        new_table_sql, sql = update_table_creation_in_sql(sql, table_name)

    return sql


def extract_namespaces(xsd_file):
    """
     Extracts namespaces from the XSD file, with namespaces as keys and prefixes as values.

    Args:
        xsd_file (str): Path to the XSD file.

    Returns:
        dict: A dictionary with namespaces as keys and prefixes as values.
    """
    try:
        tree = etree.parse(xsd_file)
        root = tree.getroot()

        # Extrae todos los namespaces declarados en el elemento raíz
        namespaces = root.nsmap

        # Normaliza los prefijos vacíos para usarlos como claves
        if None in namespaces:
            namespaces["default"] = namespaces.pop(None)

        # Invert the dictionary to have namespaces as keys and prefixes as values
        inverted_namespaces = { "{" + value + "}": key + ":" for key, value in namespaces.items()}

        return inverted_namespaces
    except Exception as e:
        print(f"Error al extraer namespaces: {e}")
        return {}


def replace_characters(file_name):
    """
    Replaces spaces and dots in a file name with underscores, except for the last dot.

    The function get the base file name and then preserves the file extension by
    identifying the last dot in the file name and applying the replacement only to the
    preceding portion. If no dot is found, all spaces and dots in the file name are
    replaced with underscores.

    Parameters:
        file_name (str): The original file name including the extension.

    Returns:
        str: The modified file name with spaces and dots replaced by underscores, maintaining the original extension.
    """
    # Find the last dot to preserve the file extension
    base_file_name = os.path.basename(file_name)
    last_dot_index = base_file_name.rfind('.')
    if last_dot_index != -1:
        # File name without the extension
        name_part = base_file_name[:last_dot_index]
        # Replace spaces and dots in the file name part
        modified_name_part = re.sub(r'[ .]', '_', name_part)
        return modified_name_part + "_schema_xsd"
    else:
        # No dot found, replace all spaces and dots
        return re.sub(r'[ .]', '_', base_file_name)


def update_TABLE_COLUMNS_with_xsd_file(f, failOnBadType, as_is):
    """
   Updates the table columns structure (TABLE_COLUMNS) using data from an XSD file.

   This function parses an XSD (XML Schema Definition) file to extract and update
   the structural relationships of table columns (TABLE_COLUMNS). It utilizes global
   and helper functions to manage namespaces and user-defined types.

   Parameters:
   - f (str): A file path to the XSD file to be parsed.
   - failOnBadType: Fail on finding a bad XS type
   - as_is: Don't normalize element names

   Returns:
   - dict: A dictionary (`dict_relationships`) containing the relationships and
     structures parsed from the XSD file. The keys typically represent element names,
     and the values provide metadata and structural information.

   Global Variables:
   - NAMESPACE_DICT: A global dictionary that is updated with namespaces extracted
     from the XSD file. Holds namespace URIs against their prefixes.

   Behavior:
   - Parses the XSD file using `etree.parse` to construct an XML tree.
   - Extracts the root element and initializes an empty dictionary to store
     relationships.
   - Updates the `NAMESPACE_DICT` using the `extract_namespaces` function.
   - Iterates over each namespace in `NAMESPACE_DICT`:
       - Builds user-defined types using `build_user_types`.
       - Determines whether the structure should be normalized based on global `args`.
       - Calls `look4element` to analyze the elements in the schema and update
         `dict_relationships` with relationships and structural information.

   Dependencies:
   - Requires `etree` for XML parsing.
   - Relies on global settings and helper functions like `extract_namespaces`,
     `build_user_types`, and `look4element` for namespace management and schema parsing.
   - Assumes the presence of a global `args` object for configuration flags
     (`as_is` and `failOnBadType`).

   Notes:
   - The function behavior may depend significantly on the structure of the XSD file
     and the implementation of the helper functions.
   - It assumes proper XML schema syntax and may raise parsing errors if the file
     structure is invalid or namespaces are improperly defined.
   """
    global NAMESPACE_DICT
    xsd = etree.parse(f)
    root = xsd.getroot()  # Define root element
    dict_relationships = {}
    NAMESPACE_DICT = extract_namespaces(f)
    for key_namespace in NAMESPACE_DICT.keys():
        # Build the USER_TYPES dictionary
        build_user_types(key_namespace, xsd)

        # parse structure
        if as_is:
            norm = False
        else:
            norm = True

        # The file name is the root node and the master table that links to all tables.
        parent = replace_characters(f)
        look4element(dict_relationships, root, key_namespace, xsd, parent, fail=failOnBadType, normalize=norm)

    return dict_relationships


def process_xsd_files(xsd_files, db_name, db_host, db_username, db_password, db_port):
    """
    Processes a list of XSD (XML Schema Definition) files to generate a database schema.

    This function reads one or more XSD files, extracts the elements, types, and relationships defined in them,
    and generates SQL statements to create tables and relationships in a database. Optionally, it connects to a
    database and executes the generated SQL statements. Additionally, it can generate a PlantUML ERD Diagram to visualize
    the database schema.

    Args:
        xsd_files (list[str]): A list of paths to XSD files to be processed.
        db_name (str): The name of the database to connect to. If not provided, the SQL statements are printed to stdout.
        db_host (str): The host where the database is located.
        db_port (int): The port number to connect to the database.
        db_username (str): The username to authenticate with the database.
        db_password (str): The password to authenticate with the database.

    Steps:
        1. Parse the XSD files to extract namespaces, types, and structure.
        2. Build SQL statements to create tables and relationships.
        3. Analyze dependencies between tables to determine the order of creation and deletion.
        4. Generate SQL statements for table creation and optional table deletion.
        5. Optionally, execute the SQL statements in the specified database.
        6. Generate a PlantUML diagram to visualize the schema.

    Raises:
        ValueError: If the dependency graph contains cycles and cannot be resolved.
        Exception: If no table definitions are found or another unexpected error occurs.

    Outputs:
        - SQL statements for creating and optionally dropping tables.
        - PlantUML diagrams for visualizing the schema.
        - Executes SQL statements directly on the database if database credentials are provided.

    Notes:
        - The function expects the XSD files to define valid XML schemas.
        - If multiple namespaces are present, the function processes each namespace individually.

    Example Usage:
        process_xsd_files(
            xsd_files=['schema1.xsd', 'schema2.xsd'],
            db_name='my_database',
            db_host='localhost',
            db_port=1433,
            db_username='admin',
            db_password='password'
        )
    """
    for f in xsd_files:
        """ Parse the XSD file
        """

        # This part is useful if you want to increase the level recursion
        # print(sys.getrecursionlimit())
        # sys.setrecursionlimit(5000)
        # print(sys.getrecursionlimit())

        dict_relationships = update_TABLE_COLUMNS_with_xsd_file(f, args.failOnBadType, args.as_is)
    if TABLE_COLUMNS is not None and len(TABLE_COLUMNS) > 0 and not db_name:
        arr_create_tables, graph, list_drop_table_sentences, list_create_table_sentences =(
            generate_sql_statements_in_topological_order())

        print('--BEGIN DROP TABLE Statements')
        for drop_table in list_drop_table_sentences:
            print(drop_table)
        print('--END DROP TABLE Statements\n')

        print('--BEGIN CREATE TABLE Statements')
        for create_table in list_create_table_sentences:
            print(create_table)
        print('--END CREATE TABLE Statements\n')

        # Generate the full ERD Diagram
        print('--BEGIN PlantUml Statements')
        create_plantuml_diagram(graph, arr_create_tables, dict_relationships)
        print('--END PlantUml Statements\n')

    elif TABLE_COLUMNS is not None and len(TABLE_COLUMNS) > 0:
        arr_create_tables, graph, list_drop_table_sentences, list_create_table_sentences = (
            generate_sql_statements_in_topological_order())

        # Connect to SQL Server and run the SQL script
        try:
            import pymssql

            # Establecer conexión
            conn = pymssql.connect(
                server=f"{db_host},{db_port}" if db_port is not None else f"{db_host}",
                #server=f"{db_host}:{db_port}",
                #server=f"{db_host}",
                user=db_username,
                password=db_password,
                database=db_name
            )
            print("Connection successful")

            # Crear cursor
            cursor = conn.cursor()

            # Execute DROP TABLE statements
            for statement in list_drop_table_sentences:
                # Ignorar sentencias vacías
                if statement.strip():
                    cursor.execute(statement)
                    print(f"Executed: {statement.strip()}")

            # Execute CREATE TABLE statements
            for statement in list_create_table_sentences:
                # Ignorar sentencias vacías
                if statement.strip():
                    cursor.execute(statement)
                    print(f"Executed: {statement.strip()}")

            # Confirmar los cambios
            conn.commit()
            print("Script executed successfully on SQL Server.")
        except Exception as e:
            print(f"Error during connection or execution: {e}")
        finally:
            # Cerrar cursor y conexión de forma segura
            if 'cursor' in locals() and cursor is not None:
                cursor.close()
            if 'conn' in locals() and conn is not None:
                conn.close()

    else:
        raise Exception("This shouldn't happen.")


def generate_sql_statements_in_topological_order():
    """
    Generates SQL CREATE and DROP TABLE statements in topological order.

    This function processes a set of SQL CREATE TABLE statements extracted from a
    dictionary of tables and columns. It performs the following tasks:

    1. Extracts CREATE TABLE statements using regular expressions and identifies unique
       table definitions. Warns of any duplicate table definitions.
    2. Uses a graph-based approach to analyze dependencies between tables, such as foreign
       key constraints, to ensure correct order of SQL statement execution.
    3. Temporarily breaks cycles in the dependency graph to facilitate topological sorting,
       ensuring no cyclic dependencies persist in the output order.
    4. Generates DROP TABLE statements in topological order to safely remove tables with
       dependencies.
    5. Generates CREATE TABLE statements in the reverse topological order to establish
       tables with dependencies correctly.

    Returns:
    - tuple: A tuple containing:
        - arr_create_tables (list): A list of individual SQL CREATE TABLE instructions parsed
          from the original SQL.
        - graph (networkx.DiGraph): A directed acyclic graph representing table dependencies.
        - list_drop_table_sentences (list): SQL statements to drop tables in the correct order.
        - list_create_table_sentences (list): SQL statements to create tables in the correct order.

    Exceptions:
    - Raises a ValueError if it detects cycles in the dependency graph after attempting to
      break them, indicating the presence of irreducible cyclic dependencies.

    Dependencies:
    - Utilizes regular expressions for SQL parsing.
    - Requires NetworkX for graph construction and topological sorting.
    - Relies on helper functions `create_sql_from_tables_columns_dictionary`, `create_graph`,
      `break_cycles`, `generate_drop_table_statements`, and `generate_create_table_statements`.

    Notes:
    - The function assumes SQL input is complex and potentially contains cycles
      that must be broken temporarily for correct execution order.
    - The detailed cycle management system aims to highlight and resolve dependencies
      that would otherwise prevent successful SQL execution.

    Example Usage:
        arr_create_tables, graph, drop_statements, create_statements = generate_sql_statements_in_topological_order()
        for stmt in drop_statements:
            execute_sql(stmt)
        for stmt in create_statements:
            execute_sql(stmt)
    """
    sql = create_sql_from_tables_columns_dictionary()
    # Regular expression to find all CREATE TABLE statements, capturing the table name
    table_pattern = re.compile(r"CREATE TABLE [a-zA-Z_][a-zA-Z0-9_]* \(.*?\);", re.DOTALL)
    # Find all matches in result[1], and store them in a set to avoid duplicates
    matches = set(re.findall(table_pattern, sql))
    processed_tables = {}
    for m in matches:
        table_patern_unique = re.compile(r"CREATE TABLE ([a-zA-Z_][a-zA-Z0-9_]*) \(.*?\);", re.DOTALL)
        matches_unique = re.findall(table_patern_unique, m)
        if matches_unique is not None and not matches_unique[0] in processed_tables:
            processed_tables[matches_unique[0]] = m
        else:
            if matches_unique is not None and matches_unique[0] in processed_tables:
                print(f"WARNING!!!. Duplicated table definition:'{matches_unique[0]}'")

    # Concat matches separated by "\n"
    arr_create_tables = sql.replace('\n\n', '').split(";")
    # Use list comprehension to filter out empty or whitespace-only elements
    arr_create_tables = [element.strip() for element in arr_create_tables if element.strip()]

    # Analyze the instructions to extract dependencies
    graph = create_graph(arr_create_tables)
    # Detectar y romper ciclos temporalmente para generar las sentencias CREATE TABLE
    graph = break_cycles(graph)
    if not nx.is_directed_acyclic_graph(graph):
        print("El grafo contiene ciclos:")
        print(nx.find_cycle(graph))
        raise ValueError("The graph must be acyclic in order to perform a topological ordering.")

    # Delete order
    drop_order = list(nx.topological_sort(graph))
    # Create order is reverse of delete order
    create_order = reversed(drop_order)
    # Generate SQL DROP TABLE statements
    list_drop_table_sentences = generate_drop_table_statements(arr_create_tables, drop_order)
    # Generate SQL CREATE TABLE statements
    list_create_table_sentences = generate_create_table_statements(arr_create_tables, create_order, sql)

    return arr_create_tables, graph, list_drop_table_sentences, list_create_table_sentences


def generate_create_table_statements(arr_create_tables, create_order, sql):
    """
    Extracts and orders SQL CREATE TABLE statements according to a specified order.

    This function processes a SQL script containing CREATE TABLE statements and
    organizes them into a list, ensuring each statement is ordered as specified
    by the `create_order` list. It returns the statements as a list of strings,
    each formatted as a complete CREATE TABLE query.

    Parameters:
    - arr_create_tables (list of str): Initially expected to be a list to hold individual
      SQL CREATE TABLE statement strings, though it's reconstructed within the function.
    - create_order (list of str): A list specifying the desired order for creating tables.
      Each element corresponds to a table name in the dependency order.
    - sql (str): A string containing the SQL script with all CREATE TABLE statements.

    Returns:
    - list of str: A list containing the SQL CREATE TABLE statements, ordered according
      to the `create_order` list and formatted as complete queries.
    """
    list_create_table = []
    for table_graph in create_order:
        arr_create_tables = sql.replace('\n\n', '').split("CREATE TABLE ")[1:]
        for i, createTable in enumerate(arr_create_tables, start=1):
            table_name = get_table_name(createTable, '')
            if table_name is not None and table_name != '' and table_graph == table_name:
                list_create_table.append(f"CREATE TABLE {createTable}")
                break
    return list_create_table


def generate_drop_table_statements(arr_create_tables, drop_order):
    """
    Generates SQL DROP TABLE statements for tables specified in drop_order.

    This function takes a list of table creation statements and a drop order list,
    and constructs DROP TABLE statements for each table in the order specified by
    drop_order. The DROP TABLE statement is generated only if the table exists in
    the INFORMATION_SCHEMA.TABLES system view.

    Parameters:
        - arr_create_tables (list of str): A list containing SQL CREATE TABLE statements.
        - drop_order (list of str): A list specifying the order in which tables should
          be dropped. Each entry corresponds to a table name.

    Returns:
        - list of str: A list of SQL DROP TABLE statements formatted to check for
          table existence before attempting to drop it.
    """
    list_drop_table_sentences = []
    for table_graph in drop_order:
        for create_table in reversed(arr_create_tables):
            table_name = get_table_name(create_table)
            if table_name is not None and table_name != '' and table_graph == table_name:
                # We build the DROP TABLE statement
                drop_table = f"IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}') DROP TABLE {table_name};"
                list_drop_table_sentences.append(drop_table)

    return list_drop_table_sentences


if __name__ == '__main__':

    """ Imports
    """
    import argparse
    # import pyxb.utils.domutils as domutils
    from lxml import etree

    """ Handle options
    """
    parser = argparse.ArgumentParser(
        description='Create a database based on an XSD schema.  If no database name is specified, SQL is output to stdout.')
    parser.add_argument(
        'xsd',
        metavar='FILE',
        type=readable_file,
        nargs='+',
        help='XSD file to base the Sql Server Schema on'
    )
    parser.add_argument(
        '-f', '--fail',
        dest='failOnBadType',
        action='store_true',
        default=False,
        help='Fail on finding a bad XS type'
    )
    parser.add_argument(
        '-a', '--as-is',
        dest='as_is',
        action='store_true',
        default=False,
        help="Don't normalize element names"
    )
    parser.add_argument(
        '-d', '--database',
        metavar='NAME',
        dest='db_name',
        type=str,
        nargs='?',
        help='DB Name'
    )
    parser.add_argument(
        '-u', '--user',
        metavar='USERNAME',
        dest='db_username',
        type=str,
        nargs='?',
        help='DB Username'
    )
    parser.add_argument(
        '-p', '--password',
        metavar='PASSWORD',
        dest='db_password',
        type=str,
        nargs='?',
        help='DB Password'
    )
    parser.add_argument(
        '-n', '--host',
        metavar='HOSTNAME',
        dest='db_host',
        type=str,
        nargs='?',
        default='localhost',
        help='DB Host'
    )
    parser.add_argument(
        '-P', '--port',
        metavar='PORT',
        dest='db_port',
        type=int,
        nargs='?',
        help='DB Port'
    )
    args = parser.parse_args()
    """ MEAT
    """
    if not args.xsd:
        print('XSD file not specified.')
        exit
    else:
        process_xsd_files(args.xsd, args.db_name, args.db_host, args.db_username, args.db_password, args.db_port)
