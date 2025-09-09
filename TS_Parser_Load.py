import tree_sitter_python as pyts
import tree_sitter_java as javats
import tree_sitter_c_sharp as csharpts
import tree_sitter_ruby as rbts
import tree_sitter_kotlin as kots
from tree_sitter import Language, Parser

class TS_Parser_Load:
    def __init__(self, language):
        self.TS_LANGUAGE, self.parser = self.get_parser(language)
        self.queries = self.get_queries(language)

    def get_parser(self,language):
        if language == "python":
            TS_LANGUAGE = Language(pyts.language())
            parser = Parser(TS_LANGUAGE)
        elif language == "java":
            TS_LANGUAGE = Language(javats.language())
            parser = Parser(TS_LANGUAGE)
        elif language == "ruby":
            TS_LANGUAGE = Language(rbts.language())
            parser = Parser(TS_LANGUAGE)
        elif language == "kotlin":
            TS_LANGUAGE = Language(kots.language())
            parser = Parser(TS_LANGUAGE)
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        return TS_LANGUAGE, parser
    
    def get_queries(self, language):
        
        if language == "python":
            class_difinition_query = """
            (module
                (class_definition name: (identifier) @class_name) @class_def
            )
            """

            class_function_definition_query = """
            (block
                (function_definition name: (identifier) @function_name)@function_def
            )
            """

            ston_function_definition_query = """
            (module
                (function_definition name: (identifier) @function_name) @function_def
            )
            """
        elif language == "java":
            class_difinition_query = """
            (program (class_declaration name: (identifier) @class_name) @class_def)
            """

            class_function_definition_query = """
            (class_body (method_declaration name: (identifier) @function_name) @function_def)
            """

            ston_function_definition_query = """
            (program (method_declaration name: (identifier) @function_name) @function_def)
            """
        elif language == "csharp":
            class_difinition_query = """
            (namespace_declaration
                (declaration_list
                    (class_declaration name: (identifier) @class_name) @class_def
                )
            )
            """

            class_function_definition_query = """
            (declaration_list
                (property_declaration name: (identifier) @function_name)@function_def
            )
            """

            ston_function_definition_query = """
            (namespace_declaration
                (declaration_list
                    (property_declaration name: (identifier) @function_name) @function_def
                )
            )
            """
        elif language == "ruby":
            class_difinition_query = """
            (program
                (class name: (constant) @class_name) @class_def
            )
            """

            class_function_definition_query = """
            (body_statement
                (method name: (identifier) @function_name)@function_def
            )
            """

            ston_function_definition_query = """
            (program
                (method name: (identifier) @function_name) @function_def
            )
            """
        elif language == "kotlin":
            class_difinition_query = """
            (source_file
                (class_declaration name: (identifier) @class_name) @class_def
            )
            """

            class_function_definition_query = """
            (class_body
                (function_declaration name: (identifier) @function_name)@function_def
            )
            """

            ston_function_definition_query = """
            (source_file
                (function_declaration name: (identifier) @function_name) @function_def
            )
            """
        else:
            raise ValueError(f"Unsupported language: {language}")
        return self.TS_LANGUAGE.query(class_difinition_query), self.TS_LANGUAGE.query(class_function_definition_query), self.TS_LANGUAGE.query(ston_function_definition_query)
        