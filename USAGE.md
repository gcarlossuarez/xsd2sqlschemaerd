

Usage
=====
Ouput of ``--help``::

    usage: usage: xsd2sqlschemaerd.py [--host] [--fail] [--as-is] [--database [NAME]] [--user [USERNAME]] [--password [PASSWORD]] [-n [HOSTNAME]] [--port [PORT]] FILE [FILE ...]

    Create a database based on an XSD schema. If no database name is specified,
    SQL is output to stdout.

    positional arguments:
      FILE                  XSD file to base the Postgres Schema on

    optional arguments:
      -h, --help            show this help message and exit
      -f, --fail            Fail on finding a bad XS type
      -a, --as-is           Don't normalize element names
      -d [NAME], --database [NAME]
                            DB Name
      -u [USERNAME], --user [USERNAME]
                            DB Username
      -p [PASSWORD], --password [PASSWORD]
                            DB Password
      -n [HOSTNAME], --host [HOSTNAME]
                            DB Host
      -P [PORT], --port [PORT]
                            DB Port (Default: 5432)
~~~~
**Example:**
Without connecting DB
---------------------
python.exe xsd2sqlschemaerd.py ".\\tests\\my_example.xsd"
    
    
With connecting DB
------------------
python.exe xsd2sqlschemaerd.py --database PruebaXsd2DBSchema --host "my_server\my_instance" --user my_user --password my_password ".\\tests\\my_example.xsd"