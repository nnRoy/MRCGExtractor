# MRCGExtractor
## Components of MRCGExtractor
### Selection of Tree-sitter plugins and LSP language servers
|Programming Language | Tree-sitter Plugin| LSP Language Server|
|---|---|---|
| Python | py-tree-sitter[https://github.com/tree-sitter/py-tree-sitter] | jedi-language-server[https://github.com/pappasam/jedi-language-server] |
| Java | java-tree-sitter[https://github.com/tree-sitter/java-tree-sitter] | Eclipse JDTLS[https://projects.eclipse.org/projects/eclipse.jdt.ls] |
| Kotlin |kotlin-tree-sitter[http://github.com/tree-sitter/kotlin-tree-sitter]  |kotlin-language-server[https://github.com/fwcd/kotlin-language-server]  |
| Ruby | ruby-tree-sitter[https://github.com/Faveod/ruby-tree-sitter] | solargraph[https://github.com/castwide/solargraph] |


We use the open-source multilspy[https://github.com/microsoft/multilspy] library to access LSP.

### S-expression-style expression
#### Python
```
class_difinition_query = """
            (module
                (class_definition name: (identifier) @class_name) @class_def
            )
            (module
                (decorated_definition
                    (class_definition name: (identifier) @class_name) @class_def
                )
            )
            """
inclass_method_definition_query = """
            (block
                (function_definition name: (identifier) @function_name)@function_def
            )
            (block
                (decorated_definition
                    (function_definition name: (identifier) @function_name)@function_def
                )
            )
            """
module_function_definition_query = """
            (module
                (function_definition name: (identifier) @function_name) @function_def
            )
            (module
                (decorated_definition
                    (function_definition name: (identifier) @function_name)@function_def
                )
            )
            """
```
#### Java
```
class_difinition_query = """
            (program (class_declaration name: (identifier) @class_name) @class_def)
            """
inclass_method_definition_query = """
            (class_body (method_declaration name: (identifier) @function_name) @function_def)
            """
module_function_definition_query = """
            (program (method_declaration name: (identifier) @function_name) @function_def)
            """
```

#### Kotlin
```
class_difinition_query = """
            (source_file
                (class_declaration name: (identifier) @class_name) @class_def
            )
            """

inclass_method_definition_query = """
            (class_body
                (function_declaration name: (identifier) @function_name)@function_def
            )
            """

module_function_definition_query = """
            (source_file
                (function_declaration name: (identifier) @function_name) @function_def
            )
            """
```

#### Ruby
```
class_difinition_query = """
            (program
                (class name: (constant) @class_name) @class_def
            )
            """

inclass_method_definition_query = """
            (body_statement
                (method name: (identifier) @function_name)@function_def
            )
            """

module_function_definition_query = """
            (program
                (method name: (identifier) @function_name) @function_def
            )
            """
```

## Usage
First, you need to download the version of the LSP language server corresponding to your operating system (Windows, Linux, macOS) and place it in the language_servers folder.

Next, you can run the following command to generate the call information graph for the code repository.
```
python main.py -language <language> -repo_root_dir <repo_root_dir> -out_graph_file <repo_root_dir>
```

## Result
The call information graph extracted by MRCGExtractor is saved in the GraphML file format. 

### Node
The graph contains three types of nodes: files, classes, and functions (including in-class methods and module functions).

#### File
```
<node id="file_path"/>
```
#### Class
```
<node id="file_path::class_name::start_line::end_line::start_col"/>
```
#### Function
##### in-class method
```
<node id="file_path::class_name::funtion_name::start_line::end_line::start_col"/>
```

##### module function
```
<node id="file_path::::funtion_name::start_line::end_line::start_col"/>
```

### Relationship
The graph contains three types of relationship: Contains/Is Contained, Inherits/Is Inherited, Calls/Is Called.

#### Contains
```
<edge source="file_path" target="file_path::class_name::start_line::end_line::start_col">
  <data key="d0">contains</data>
</edge>

<edge source="file_path" target="file_path::::funtion_name::start_line::end_line::start_col">
  <data key="d0">contains</data>
</edge>

<edge source="file_path::class_name::start_line::end_line::start_col" target="file_path::class_name::funtion_name::start_line::end_line::start_col">
  <data key="d0">contains</data>
</edge>
```

#### Inherits
```
<edge source="file_path::class_name::start_line::end_line::start_col" target="file_path::class_name::start_line::end_line::start_col">
  <data key="d0">inherits</data>
</edge>
```

#### Calls
```
<edge source="function_node" target="funtion_node">
  <data key="d0">calls</data>
</edge>
```

## Example
In folder "MRCGExtractor/call_relationship_graph_example", we give an example for the repository "awsteiner".


# Experience Study
## Dataset, Prompt, and Results
### Datasets
The test samples of datasets, CoderEval and DevEval, after cleaning, has shown in "datasets".
### Prompts and Results
We will open-source the prompts and results.