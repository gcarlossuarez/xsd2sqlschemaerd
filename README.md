# Enhanced xsd2sqlschemaerd: A Continuation of Mike Shultz's Project

This project is a continuation of the [xsd2pgsql](https://github.com/mikeshultz/xsd2pgsql) project by Mike Shultz. The original project is licensed under the MIT License, as confirmed by the author. Below, you'll find details about the enhancements and extensions made to the original project. The improvements (creating and deleting tables with script) were created with SQL Server syntax (that's what I work with); but, they can be easily adapted to PostgreSQL.

---

# xsd2sqlschemaerd

This script creates a SQL Server Database Schema based on an XSD (XML Schema Definition) file. It parses the XSD file, translates the XML schema types to PostgreSQL data types, and generates SQL statements to create the corresponding database tables and relationships

# Demo
https://youtu.be/1koj7333RS4

## Prerequisites

1. **Python Version**:
   - This script requires Python 3.6 or higher.

2. **Required Python Packages**:
   - `appdirs`
   - `lxml`
   - `networkx`
   - `packaging`
   - `pymssql`
   - `pyparsing`
   - `six`

3. **SQL Server**:
   - A SQL Server database instance must be available if you plan to execute the SQL directly.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/xsd2sqlschemaerd.git
   cd xsd2sqlschemaerd


## **Overview**

The original project provides functionality to generate PostgreSQL schemas from XSD files. The enhanced version introduces several new features, focusing on database consistency, automation, and visualization.

---

## **New Features and Enhancements**

### 1. **Primary and Foreign Key Creation**
   - Automatically generates primary keys for all tables.
   - Identifies relationships in the XSD and generates foreign keys to maintain table dependencies.
   - Supports SQL Server syntax for initialization scripts, including dropping tables if they exist.

### 2. **Dependency Management with Graphs**
   - Uses the `networkx` library to construct a directed graph representing table dependencies.
   - Performs a topological sort to ensure that tables are created and deleted in the correct order, avoiding conflicts between primary and foreign keys.

### 3. **Entity Relationship Diagram (ERD) in PlantUML**
   - Generates a PlantUML representation of the database schema.
   - Tables are represented as entities, and relationships are visualized as edges between nodes.
   - Provides a clear, graphical overview of the schema for documentation and analysis.
   
### 4. **Handling `xs:choice` Elements**
- The script now supports xs:choice elements, allowing for better representation of mutually exclusive fields in SQL Server. Choices are represented as a single table with nullable columns, ensuring exclusivity while maintaining database integrity.
For a detailed explanation and examples, see [Handling xs:choice in SQL](docs/handling_xs_choice.md).

---

## **Key Functionalities**

1. **XSD to SQL Translation**:
   - Extends the mapping of XSD types to PostgreSQL types for broader compatibility.
   - Adds logic to identify and normalize table and column names.

2. **Table Creation and Deletion**:
   - Dynamically generates `CREATE TABLE` and `DROP TABLE` statements, ensuring proper ordering and dependency resolution.

3. **Graph Analysis**:
   - Detects and raises exceptions for cyclic dependencies, ensuring that the graph is a Directed Acyclic Graph (DAG).
   - Validates the schema´s consistency before executing SQL scripts.

4. **PlantUML Diagram Generation**:
   - Outputs the schema as a PlantUML diagram for easy visualization.
   - Differentiates between primary keys, foreign keys, and other columns in the visualization.

---

## Improvements
- Extracted table names using `os.path.basename` to ensure concise and clear identifiers.
- Normalized table names for compatibility with PostgreSQL and PlantUML standards.
  
---

## **License**

The original project by Mike Shultz is licensed under the MIT License, as confirmed by the author. This enhanced version respects the original license terms. You can freely use, modify, and distribute the code, provided the original license terms are respected.

---

## **How to Use the Enhanced Version**

1. **Input**: Provide an XSD file to generate the schema.

```text
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
python.exe xsd2sqlschemaerd.py ".\\tests\\my_example.xsd"
    
With connecting DB
python.exe xsd2sqlschemaerd.py --database PruebaXsd2DBSchema --host "my_server\my_instance" --user my_user --password my_user ".\\tests\\my_example.xsd"
```

2. **Output**: The script produces:
   - SQL scripts for creating and deleting tables in the correct order.
   - A PlantUML file visualizing the Entity Relationship Diagram (ERD).
3. **Customization**: Adjust the configurations for different databases if needed (default is Sql Server).


---

Feel free to explore this enhanced version of `xsd2pgsql`! Feedback is welcome.

## Limitations and Scope

This script processes an XSD file to generate SQL Server database schemas. While it handles many common use cases, there are some limitations to consider:

1. **Support for Basic Types and Simple Structures:**
   - The script supports standard XSD types and simple structures. Advanced constructs like restrictions, unions, and lists are not fully supported.

2. **Recursion Depth Limit:**
   - Processing stops if the recursion depth exceeds the defined `MAX_RECURSE_LEVEL` (default: 1000).

3. **Single Namespace:**
   - The script assumes a single namespace (`xmlns`) for the XSD and may not handle multiple namespaces correctly.

4. **Partial Support for `<choice>`:**
   - `<choice>` elements are partially processed. Some complex cases with mutually exclusive options might not be handled accurately.

5. **Unsupported XSD Constructs:**
   - The script does not process `<union>`, `<list>`, or advanced constraints like `<key>`, `<keyref>`, and `<unique>`.

6. **No Support for External XSD References:**
   - If the XSD includes or imports other XSD files, those references are not resolved.

7. **Attributes Are Ignored:**
   - Element attributes defined in the XSD are not converted into database columns.

8. **Circular References:**
   - Circular references between complex types or elements might cause errors or require manual intervention.

9. **XSD Validation Required:**
   - The script assumes the input XSD is error-free and valid. Invalid XSD files may result in unpredictable behavior.

10. **Character Normalization:**
    - The script normalizes column and table names (e.g., replacing `-` or `.` with `_`). However, edge cases with unsupported characters might require manual adjustment.

11. **Performance on Large XSD Files:**
    - For very large XSD files, the recursive processing and graph analysis may lead to performance issues or long execution times.

By understanding these limitations, you can better assess whether this script meets your requirements or if additional manual adjustments are necessary for your use case.


