from TS_Parser_Load import TS_Parser_Load
import os
import networkx as nx
from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger
from tqdm import tqdm
  
class Repo_Graph:
    def __init__(self, language, repo_root_dir, out_graph_file):
        self.parser, self.queries = self.load_ts_parser(language)
        self.all_file_abs = self.get_all_files(language, repo_root_dir)
        self.all_classes = {}
        self.all_functions = {}
        self.nx_graph = nx.DiGraph()
        self.lsp = self.load_lsp(language, repo_root_dir)
        self.out_graph_file = out_graph_file
        self.repo_root_dir = repo_root_dir

    def load_ts_parser(self, language):
        parser_loader = TS_Parser_Load(language)
        return parser_loader.parser, parser_loader.queries
    
    def get_all_files(self, language, repo_root_dir):
        all_files_abs = []
        end_tag = {
            "java": ".java",
            "kotlin": ".kt",
            "python": ".py",
            "ruby": ".rb",
        }
        for root, _, files in os.walk(repo_root_dir):
            # 跳过包含test或tests的目录路径
            if 'test' in root.lower():
                continue
            for file in files:
                if file.endswith(end_tag[language]):
                    all_files_abs.append(os.path.join(root, file))
        return all_files_abs
    
    def get_relative_path(self, file_path):
        return file_path.replace(self.repo_root_dir + '\\', '')
    

    def open_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return code

    def get_file_tree(self, code):
        tree = self.parser.parse(bytes(code, "utf8"))
        return tree.root_node
    

    def get_classes_definition(self, tree, file_path_rel):
        class_definition_query = self.queries[0]
        try:
            matches = class_definition_query.captures(tree)
            class_defs = matches["class_def"]
            class_names = matches["class_name"]
        except:
            class_defs = []
            class_names = []
        for class_name in class_names:
            for class_def in class_defs:
                if self.find_name_def_is_a_item(class_def, class_name):
                    node_info = self.get_info(class_def, class_name)
                    class_name_in_graph = file_path_rel+"::"+node_info[0]+"::"+str(node_info[3])+"::"+str(node_info[4])
                    self.nx_graph.add_node(class_name_in_graph)
                    self.nx_graph.add_edge(file_path_rel, class_name_in_graph, relationship="contains")
                    self.all_classes[file_path_rel].append(node_info)
                    self.get_class_function_definition(class_def, file_path_rel, node_info[0], class_name_in_graph)
                    break
    
    def get_class_function_definition(self, tree, file_path_rel, class_name, class_name_in_graph):
        class_function_definition_query = self.queries[1]
        try:
            matches = class_function_definition_query.captures(tree)
            function_defs = matches["function_def"]
            function_names = matches["function_name"]
        except:
            function_defs = []
            function_names = []
        for function_name in function_names:
            for function_def in function_defs:
                if self.find_name_def_is_a_item(function_def, function_name):
                    node_info = self.get_info(function_def, function_name)
                    function_name_in_graph = file_path_rel+"::"+class_name+"::"+node_info[0]+"::"+str(node_info[3])+"::"+str(node_info[4])
                    self.nx_graph.add_node(function_name_in_graph)
                    self.nx_graph.add_edge(class_name_in_graph, function_name_in_graph, relationship="contains")
                    node_info.insert(0, class_name)
                    self.all_functions[file_path_rel].append(node_info)
                    break

    def get_ston_function_definition(self, tree, file_path_rel):
        function_definition_query = self.queries[2]
        try:
            matches = function_definition_query.captures(tree)
            function_defs = matches["function_def"]
            function_names = matches["function_name"]
        except Exception as e:
            function_defs = []
            function_names = []
        for function_name in function_names:
            for function_def in function_defs:
                if self.find_name_def_is_a_item(function_def, function_name):
                    node_info = self.get_info(function_def, function_name)
                    function_name_in_graph = file_path_rel+"::::"+node_info[0]+"::"+str(node_info[3])+"::"+str(node_info[4])
                    self.nx_graph.add_node(function_name_in_graph)
                    self.nx_graph.add_edge(file_path_rel, function_name_in_graph, relationship="contains")
                    node_info.insert(0, "")
                    self.all_functions[file_path_rel].append(node_info)
                    break

    def get_info(self, node_def, node_name):
        node_name_text = node_name.text.decode("utf-8")
        node_name_start_line = node_name.start_point[0]
        node_name_start_col = node_name.start_point[1]
        node_def_start_line = node_def.start_point[0]
        node_def_end_line = node_def.end_point[0]
        return [node_name_text, node_name_start_line, node_name_start_col, node_def_start_line, node_def_end_line]
    
       
    def find_name_def_is_a_item(self, node_def, node_name):
        if node_name.parent.id == node_def.id:
            return True

    def parse_file(self, file_path_abs):
        file_path_rel = self.get_relative_path(file_path_abs)
        code = self.open_file(file_path_abs)
        root_node = self.get_file_tree(code)
        self.all_classes[file_path_rel] = []
        self.all_functions[file_path_rel] = []

        self.nx_graph.add_node(file_path_rel)

        self.get_classes_definition(root_node, file_path_rel)
        self.get_ston_function_definition(root_node, file_path_rel)
    
    def get_all_nodes_in_graph(self):
        for file_path_abs in tqdm(self.all_file_abs):
            try:
                self.parse_file(file_path_abs)
            except Exception as e:
                print(f"Error in parse_file: {e}")
                continue
    

    def load_lsp(self, language, repo_root_dir):
        config = MultilspyConfig.from_dict({"code_language": language})
        logger = MultilspyLogger()
        #return SyncLanguageServer.create(config, logger, repo_root_dir)
        return SyncLanguageServer.create(config, logger, repo_root_dir)
    
    def get_graph_name_class_node(self, file_path_rel, class_node):
        class_name = file_path_rel+"::"+class_node[0]+"::"+str(class_node[3])+"::"+str(class_node[4])
        return class_name
    
    def get_graph_name_function_node(self, file_path_rel, function_node):
        function_name = file_path_rel+"::"+function_node[0]+"::"+function_node[1]+"::"+str(function_node[4])+"::"+str(function_node[5])
        return function_name

    def find_class_ref(self, file_path_rel, class_node):
        try:
            call_list = self.lsp.request_references(file_path_rel, class_node[1], class_node[2])
        except Exception as e:
            print(f"Error in find_class_ref: {e}")
            call_list = []


        for call_item in call_list:
            if call_item["relativePath"] in self.all_classes:
                classes_list = self.all_classes[call_item["relativePath"]]
            else:
                classes_list = []

            for class_item in classes_list:
                if call_item["range"]["start"]["line"] == class_item[1]:
                    if self.get_graph_name_class_node(call_item["relativePath"], class_item) != self.get_graph_name_class_node(file_path_rel, class_node):
                        self.nx_graph.add_edge(self.get_graph_name_class_node(call_item["relativePath"], class_item), self.get_graph_name_class_node(file_path_rel, class_node), relationship="inherit")
                    break
            
            if call_item["relativePath"] in self.all_functions:
                functions_list = self.all_functions[call_item["relativePath"]]
            else:
                functions_list = []
            for function_item in functions_list:
                if call_item["range"]["start"]["line"] == function_item[2]:
                    self.nx_graph.add_edge(self.get_graph_name_function_node(call_item["relativePath"], function_item), self.get_graph_name_class_node(file_path_rel, class_node), relationship="parameter")
                    break
            
    
    def find_function_ref(self, file_path_rel, function_node):
        try:
            call_list = self.lsp.request_references(file_path_rel, function_node[2], function_node[3])
        except Exception as e:
            print(f"Error in find_function_ref: {e}")
            call_list = []

        for call_item in call_list:
            if call_item["relativePath"] in self.all_functions:
                functions_list = self.all_functions[call_item["relativePath"]]
            else:
                functions_list = []

            for function_item in functions_list:
                if call_item["range"]["start"]["line"] >= function_item[4] and call_item["range"]["end"]["line"] <= function_item[5]:
                    if self.get_graph_name_function_node(call_item["relativePath"], function_item) != self.get_graph_name_function_node(file_path_rel, function_node):
                        self.nx_graph.add_edge(self.get_graph_name_function_node(call_item["relativePath"], function_item), self.get_graph_name_function_node(file_path_rel, function_node), relationship="call")
                    break


    def parse_all_classes(self):
        for file_path_abs in tqdm(self.all_file_abs):
            file_path_rel = self.get_relative_path(file_path_abs)
            if file_path_rel in self.all_classes:
                classes_list = self.all_classes[file_path_rel]
            else:
                classes_list = []
            for class_node in classes_list:
                self.find_class_ref(file_path_rel, class_node)

    def parse_all_functions(self):
        for file_path_abs in tqdm(self.all_file_abs):
            file_path_rel = self.get_relative_path(file_path_abs)
            if file_path_rel in self.all_functions:
                functions_list = self.all_functions[file_path_rel]
            else:
                functions_list = []
            for function_node in functions_list:
                self.find_function_ref(file_path_rel, function_node)

    def save_graph_file(self, output_graph_file):
        nx.write_graphml(self.nx_graph, output_graph_file)


    def parse_repo_graph(self):
        self.get_all_nodes_in_graph()
        with self.lsp.start_server():
            self.parse_all_classes()
            self.parse_all_functions()
        self.save_graph_file(self.out_graph_file)






                





