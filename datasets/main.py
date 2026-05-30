from model_load import *
from data_load import *
import config as config
from utils import *
from argparse import ArgumentParser
from build_corpus import TS_Parser_Load

import ast
from asdl import ASDLGrammar
from lang.py.py_asdl_helper import python_ast_to_asdl_ast
import astor

from asdl import ASDLGrammar
from lang.java.java_asdl_helper import java_ast_to_asdl_ast
import javalang.parse

import numpy as np
import sys

def load_model(model_name):
    if "gpt-4o-mini" in model_name:
        client = GPTClient(model_name)
    elif "deepseek-chat" in model_name:
        client = DeepSeekClient(model_name)
    elif "qwen2.5-coder" in model_name:
        client = QwenCoderClient(model_name)
    elif "deepseek-coder" in model_name:
        client = DeepSeekCoderClient(model_name)
    else:
        raise ValueError("Unsupported model name: {}".format(model_name))


def checker(function_code, parser):
    tree = parser.parser.parse(bytes(function_code, "utf8"))
    root_node = tree.root_node
    if root_node.has_error:
        return False
    return True


def extract_key_syntactic_structure(ppl_calculator, language, req, code, asdl_ast, coarse_tag = True, fine_tag = True):
    if language == "python":
        return extract_python_key_syntactic_structure(ppl_calculator, language, req, code, asdl_ast, coarse_tag, fine_tag)
    elif language == "java":
        return extract_java_key_syntactic_structure(ppl_calculator, language, req, code, asdl_ast, coarse_tag, fine_tag)
    else:
        raise ValueError(f"Unsupported language: {language}")  

def extract_python_key_syntactic_structure(ppl_calculator, language, req, code, asdl_ast, coarse_tag = True, fine_tag = True):
    asdl_text = open('./asdl/lang/py3/py3_asdl.simplified.txt').read()
    grammar = ASDLGrammar.from_text(asdl_text)

    tag = asdl_ast.production.constructor.name
    tag_type = asdl_ast.production.type.name
    xml_content = ""

    for field in asdl_ast.fields:
        field_tag = field.name
        field_xml = ""
        if field.cardinality == 'multiple':
            if field.value:
                for val in field.value:
                    if hasattr(val, 'production'):
                        field_xml += extract_python_key_syntactic_structure(ppl_calculator, language, req, code, val, coarse_tag, fine_tag)
                    else:
                        if coarse_tag:
                            if val not in [None, [], '']:
                                field_xml += f"<value>{val}</value>"
                        else:
                            field_xml += f"<value>{val}</value>"
            if field_xml:
                xml_content += f"<{field_tag}>{field_xml}</{field_tag}>"
        else:
            if hasattr(field.value, 'production'):
                field_xml = extract_python_key_syntactic_structure(ppl_calculator, language, req, code, field.value, coarse_tag, fine_tag)
            else:
                if coarse_tag:
                    if field.value not in [None, [], '']:
                        field_xml = f"{field.value}"
                else:
                    field_xml = f"{field.value}"
            if field_xml:
                xml_content += f"<{field_tag}>{field_xml}</{field_tag}>"
    if xml_content:
        if fine_tag:
            return fine_purning(req, code, language, tag_type, f"<{tag}>{xml_content}</{tag}>", asdl_ast, ppl_calculator, grammar)
        else:
            return f"<{tag}>{xml_content}</{tag}>"
    else:
        return ""

def extract_java_key_syntactic_structure(ppl_calculator, language, req, code, asdl_ast, coarse_tag = True, fine_tag = True):
    asdl_text = open('./asdl/lang/java/java_asdl.simplified.txt').read()
    grammar = ASDLGrammar.from_text(asdl_text)

    tag = asdl_ast.production.constructor.name
    tag_type = asdl_ast.production.type.name
    xml_content = ""
    for field in asdl_ast.fields:
        field_tag = field.name
        field_xml = ""
        if field.cardinality == 'multiple':
            if field.value and isinstance(field.value, list) and len(field.value) > 0:
                for val in field.value:
                    if hasattr(val, 'production'):
                        sub_xml = extract_java_key_syntactic_structure(ppl_calculator, language, req, code, val, coarse_tag, fine_tag)
                        if sub_xml: 
                            field_xml += sub_xml
                    else:
                        if coarse_tag:
                            if val not in [None, [], '']:
                                field_xml += f"<value>{val}</value>"
                        else:
                            field_xml += f"<value>{val}</value>"
            if field_xml:
                xml_content += f"<{field_tag}>{field_xml}</{field_tag}>"
        else:
            if hasattr(field.value, 'production'):
                field_xml = extract_java_key_syntactic_structure(ppl_calculator, language, req, code, field.value, coarse_tag, fine_tag)
            else:
                if coarse_tag:
                    if field.value not in [None, [], '']:
                        field_xml = f"{field.value}"
                else:
                    field_xml = f"{field.value}"
            if field_xml:
                xml_content += f"<{field_tag}>{field_xml}</{field_tag}>"
    if xml_content:
        if fine_tag:
            return fine_purning(req, code, language, tag_type, f"<{tag}>{xml_content}</{tag}>", asdl_ast, ppl_calculator, grammar)
        else:
            return f"<{tag}>{xml_content}</{tag}>"
    else:
        return ""

def get_token_length(tokenizer, text, add_special_tokens=True):
    token_length = len(tokenizer.encode(text, add_special_tokens=add_special_tokens))
    return token_length


def fine_purning(req, code, language, tag_type, xml, asdl_ast, ppl_calculator, grammar):
    if language == "python":
        if tag_type != "expr":
            return xml
    if language == "java":
        if tag_type != "expression":
            return xml

    
    conditional_text = xml + "\n\n" + code + "\n" + req
    prefix_text = xml + "\n\n"

    ppl = ppl_calculator.calculate_ppl_qwen(conditional_text, prefix_text)


    try:

        if language == "python":
            py_ast = asdl_ast_to_python_ast(asdl_ast, grammar)
            source_code = astor.to_source(py_ast)
        elif language == "java":
            java_ast = asdl_ast_to_java_ast(asdl_ast, grammar)
            source_code = java_ast_to_code(java_ast)

        token_conditional_text = source_code+ "\n\n" + code + "\n" + req
        token_prefix_text = source_code + "\n\n"

        token_ppl = ppl_calculator.calculate_ppl_qwen(token_conditional_text, token_prefix_text)
    except:

        token_conditional_text = asdl_ast.to_string()+ "\n\n" + code + "\n" + req
        token_prefix_text = asdl_ast.to_string() + "\n\n"

        token_ppl = ppl_calculator.calculate_ppl_qwen(token_conditional_text, token_prefix_text)

    if ppl < token_ppl:
        return xml
    else:
        return "<PAD>"

class QwenPPL:
    def __init__(self):
        self.tokenizer, self.model, self.config = load_model("qwen2.5-coder-0.5b")
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

    def get_token_length(self, text, add_special_tokens=True):
        token_length = len(self.tokenizer.encode(text, add_special_tokens=add_special_tokens))
        return token_length


    def calculate_ppl_qwen(self, text, prefix_text):

        prefix_len = self.get_token_length(prefix_text, add_special_tokens=True)
        condition_pos_id=prefix_len - 1

        max_position_embeddings = getattr(self.model.config, "max_position_embeddings", 4096)

        encoding = self.tokenizer(text, return_tensors="pt", padding=True)
        input_ids = encoding["input_ids"].cuda(self.model.device)
        attention_mask = encoding["attention_mask"].cuda(self.model.device)

        end = input_ids.shape[1]
        end = min(end, max_position_embeddings)


        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids[:, :end],
                attention_mask=attention_mask[:, :end],
                return_dict=True,
                output_hidden_states=True,
                use_cache=True,
            )

        shift_logits = outputs.logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:end].contiguous()

        active = (attention_mask[:, :end] == 1)[..., :-1].view(-1)
        active_logits = shift_logits.view(-1, shift_logits.size(-1))[active]
        active_labels = shift_labels.view(-1)[active]

        loss_fct = torch.nn.CrossEntropyLoss(reduction="none")
        loss = loss_fct(active_logits, active_labels)

        loss = loss[condition_pos_id:]

        mean_loss = loss.mean() if len(loss) > 0 else torch.tensor(0.0)
        ppl = torch.exp(mean_loss).item() if mean_loss.item() != float('inf') else float('inf')

        return ppl

def load_TS(language):
    if language == "python":
        TS_LANGUAGE = Language(py_ts.language())
    elif language == "java":
        TS_LANGUAGE = Language(java_ts.language())
    else:
        raise ValueError("Unsupported language")
    
    parser =Parser(TS_LANGUAGE)
    return parser


def remove_comments_java(source: str, language: str) -> str:
    parser = load_TS(language)
    codebytes = bytes(source, "utf8")
    codebytes_list = codebytes.split(b'\n')
    tree = parser.parse(codebytes)
    root = tree.root_node

    comment_points = []

    def traverse(node):
        if node.type in ['block_comment', 'line_comment']:
            start_row, start_col = node.start_point
            end_row, end_col = node.end_point
            comment_points.append((start_row, start_col, end_row, end_col))
        
        
        for child in node.children:
            traverse(child)

    traverse(root)

    result = delete_content_with_markers(codebytes_list, comment_points)
    return delete_block_line(b'\n'.join(result).decode("utf-8"))


def remove_comments_py(source: str, language: str) -> str:
    parser = load_TS(language)
    codebytes = bytes(source, "utf8")
    codebytes_list = codebytes.split(b'\n')
    tree = parser.parse(codebytes)
    root = tree.root_node

    comment_points = []


    def traverse(node):
        if node.type == 'comment':
            start_row, start_col = node.start_point
            end_row, end_col = node.end_point
            comment_points.append((start_row, start_col, end_row, end_col))
        
        if node.type == 'string':
            if len(node.parent.children) == 1 and node.parent.type == 'expression_statement':
                start_row, start_col = node.start_point
                end_row, end_col = node.end_point
                comment_points.append((start_row, start_col, end_row, end_col))
        
        for child in node.children:
            traverse(child)
    
    traverse(root)

    result = delete_content_with_markers(codebytes_list, comment_points)
    return remove_tab(delete_block_line(b'\n'.join(result).decode("utf-8")))

def remove_tab(code):
    if code.split("\n")[0].startswith("    "):
        codes = []
        for line in code.split("\n"):
            codes.append(line[4:] if line.startswith("    ") else line)
        return "\n".join(codes)
    else:
        return code
def delete_content_with_markers(content_list, position_list):
    str_list = [item.decode('utf-8') if isinstance(item, bytes) else str(item) for item in content_list]
    
    markers = [[True] * len(line) for line in str_list]
    for start_row, start_col, end_row, end_col in position_list:
        if start_row >= len(str_list) or end_row >= len(str_list):
            continue
        if start_row == end_row:
            for col in range(start_col, min(end_col, len(str_list[start_row]))):
                markers[start_row][col] = False
        else:
            for col in range(start_col, len(str_list[start_row])):
                markers[start_row][col] = False
            
            for row in range(start_row + 1, end_row):
                if row < len(str_list):
                    markers[row] = [False] * len(str_list[row])
            
            for col in range(0, min(end_col, len(str_list[end_row]))):
                markers[end_row][col] = False
    
    result = []
    for i, line in enumerate(str_list):
        if i < len(markers):
            new_line = ''.join([char for j, char in enumerate(line) if j < len(markers[i]) and markers[i][j]])
            result.append(new_line.encode('utf-8'))
        else:
            result.append(line.encode('utf-8'))
    
    return result
   
def delete_block_line(code):
    lines = [line.rstrip() for line in code.splitlines()]
    cleaned = "\n".join(line for line in lines if line.strip() != "")
    return cleaned


def get_cleaned_code(code, language):
    if language == "java":
        return remove_comments_java(code, language)
    elif language == "python":
        return remove_comments_py(code, language)
    else:
        raise ValueError("Unsupported language")
    

def get_asdl_ast(code, language):
    if language == "python":
        asdl_text = open('./asdl/lang/py3/py3_asdl.simplified.txt').read()
        grammar = ASDLGrammar.from_text(asdl_text)
        try:
            code_ast = ast.parse(code)
        except:
            return None

    elif language == "java":
        asdl_text = open('/asdl/lang/java/java_asdl.simplified.txt').read()
        grammar = ASDLGrammar.from_text(asdl_text)
        try:
            code_ast = javalang.parse.parse(code)
        except:
            return None

    # convert the python AST into general-purpose ASDL AST used by tranX

    try:
        if language == "python":
            asdl_ast = python_ast_to_asdl_ast(code_ast.body[0], grammar)
        elif language == "java":
            asdl_ast = java_ast_to_asdl_ast(code_ast, grammar)
        
        return asdl_ast
    
    except Exception as e:
        return None


def asdl_ast_to_python_ast(asdl_ast_node, grammar):
    py_node_type = getattr(sys.modules['ast'], asdl_ast_node.production.constructor.name)
    py_ast_node = py_node_type()

    for field in asdl_ast_node.fields:
        # for composite node
        field_value = None
        if grammar.is_composite_type(field.type):
            if field.value and field.cardinality == 'multiple':
                field_value = []
                for val in field.value:
                    node = asdl_ast_to_python_ast(val, grammar)
                    field_value.append(node)
            elif field.value and field.cardinality in ('single', 'optional'):
                field_value = asdl_ast_to_python_ast(field.value, grammar)
        else:
            # for primitive node, note that primitive field may have `None` value
            if field.value is not None:
                if field.type.name == 'object':
                    if field.value == "True":
                        field_value = True
                    elif field.value == "False":
                        field_value = False
                    elif '.' in field.value or 'e' in field.value:
                        field_value = float(field.value)
                    elif isint(field.value):
                        field_value = int(field.value)
                    else:
                        raise ValueError('cannot convert [%s] to float or int' % field.value)
                elif field.type.name == 'int':
                    field_value = int(field.value)
                else:
                    field_value = field.value

            # FIXME: hack! if int? is missing value in ImportFrom(identifier? module, alias* names, int? level), fill with 0
            elif field.name == 'level':
                field_value = 0

        # must set unused fields to default value...
        if field_value is None and field.cardinality == 'multiple':
            field_value = list()

        setattr(py_ast_node, field.name, field_value)

    return py_ast_node



def isfloat(x):
    try:
        a = float(x)
    except ValueError:
        return False
    else:
        return True


def isint(x):
    try:
        a = float(x)
        b = int(a)
    except ValueError:
        return False
    else:
        return a == b
    

def asdl_ast_to_java_ast(asdl_ast_node, grammar):
    java_node_type = getattr(sys.modules['javalang.tree'],
                             asdl_ast_node.production.constructor.name)
    java_ast_node = java_node_type()

    for field in asdl_ast_node.fields:
        # for composite node
        field_value = None
        #if field.name == 'arguments':
            #print(f'arguments {field.value} {field.cardinality}', file=sys.stderr)
        if grammar.is_composite_type(field.type):
            if (field.value is not None) and (field.cardinality == 'multiple'):
                field_value = []
                for val in field.value:
                    node = asdl_ast_to_java_ast(val, grammar)
                    field_value.append(node)
            elif field.value and field.cardinality in ('single', 'optional'):
                field_value = asdl_ast_to_java_ast(field.value, grammar)
        else:
            # for primitive node, note that primitive field may have `None`
            # value
            if field.value is not None:
                if field.type.name == 'object':
                    if '.' in field.value or 'e' in field.value:
                        field_value = float(field.value)
                    elif isint(field.value):
                        field_value = int(field.value)
                    else:
                        raise ValueError(
                          f'cannot convert [{field.value}] to float or int')
                elif field.type.name == 'int':
                    if type(field.value) == list:
                        field_value = [None] * len(field.value)
                    else:
                        field_value = int(field.value)
                else:
                    field_value = field.value

            # FIXME: hack! if int? is missing value in ImportFrom(identifier?
            # module, alias* names, int? level), fill with 0
            elif field.name == 'level':
                field_value = 0

        # # must set unused fields to default value...
        # if field_value is None and field.cardinality == 'multiple':
        # field_value = list()

        setattr(java_ast_node, field.name, field_value)

    return java_ast_node


def java_ast_to_code(node, indent=0):
    if isinstance(node, javalang.tree.Node):
        fields = {field: getattr(node, field) for field in node.attrs if hasattr(node, field)}
        code = []
        for key, value in fields.items():
            if isinstance(value, list):
                for item in value:
                    code.append(java_ast_to_code(item, indent))
            else:
                code.append(java_ast_to_code(value, indent))
        return "\n".join(code)
    elif isinstance(node, list):
        # 处理列表类型的子节点
        return "\n".join(java_ast_to_code(item, indent) for item in node)
    elif isinstance(node, str):
        return node
    elif node is None:
        return ""
    else:
        return str(node)


def process_dataset(dataset_name, language, checker, top_k, sr, coarse_flag, fine_flag, n, model_name):
    client = load_model(model_name)
    parser = TS_Parser_Load(language).get_parser(language)[1]

    dataset_json = load_dataset(dataset_name, language)

    retrieve_functions = load_json(f"retrieve_results/{dataset_name}_{language}.json")

    results = []
    for i in range(len(dataset_json)):
        prompt = config.relevant_prompt
        data = dataset_json[i]
        retrieved_funcs = retrieve_functions[i]
        req = data["requirement"]
        file_path = data["file_path"]
        for funcs in retrieved_funcs:
            func = funcs["function_code"]
            key_syntactic_structure = extract_key_syntactic_structure(
                client,
                language,
                req,
                func,             
                get_asdl_ast(func, language), 
                coarse_flag,
                fine_flag
            )
            prompt += f"\nRelevant Function:\n{func}\n"
            prompt += f"\nRelevant Function Key Syntactic Structure:\n{key_syntactic_structure}\n"
        prompt += f"\nRequirement:\n{req}\n"

        generated_code = client.generated_code(prompt, n)

        results.append(generated_code)
    
    save_json(f"generation_results/{dataset_name}_{language}_{model_name}_checker_{checker}_topk_{top_k}_sr_{sr}_coarse_{coarse_flag}_fine_{fine_flag}_n_{n}.json", results)


def get_parser():
    parser = ArgumentParser()
    parser.add_argument('--dataset_name', type=str)
    parser.add_argument('--language', type=str)
    parser.add_argument('--checker', type=bool, default=True)
    parser.add_argument('--top_k', type=int, default=5)
    parser.add_argument('--sr', type=bool, default=True)
    parser.add_argument('--coarse_flag', type=bool, default=True)
    parser.add_argument('--fine_flag', type=bool, default=True)
    parser.add_argument('--n', type=int, default=10)
    parser.add_argument('--model_name', type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = get_parser()
    dataset_name = args.dataset_name
    language = args.language
    checker = args.checker
    top_k = args.top_k
    sr = args.sr
    coarse_flag = args.coarse_flag
    fine_flag = args.fine_flag
    n = args.n
    model_name = args.model_name

    process_dataset(dataset_name, language, checker, top_k, sr, coarse_flag, fine_flag, n, model_name)

    