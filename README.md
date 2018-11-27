To Add an Exporter:

- Create a folder for your exporters (i.e. exporters/myexporters)
- Create an __init__.py folder in myexporters
- Create any shared utility modules in the myexporters folder
- Optionally create a file for a shared class file myexporter
    - in shared class 'import exporter'
- Create a folder myexporter/myexporter_types
- Add your custom exporter files to the myexporter/myexporter_types folder
    - in your exporter files 'import exporter' or 'import myexporter/mysharedexporterclassfile

- modify cmd.py
- add your exporter to the 'EXPORTERS' class map