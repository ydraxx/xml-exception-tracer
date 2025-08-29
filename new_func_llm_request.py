import chardet
import os
import re
import api_maia
from config import xml_cfg, environment


true_STP_name = {
    "IncmessageServer": "ImsgServer",
    "SendPayServerTCI": "SendPayServer",
    "SettlementServer": "SettleServer",
    "SettleflowServer": "SettleServer"
}


def find_directory(service_part):
    if service_part.endswith('TCI'):
        code_directory = service_part.split('TCI')[0]
        directory = 'tci'
    elif service_part.endswith('VANILLE'):
        code_directory = service_part.split('VANILLE')[0]
        directory = 'vanille'
    elif service_part.endswith('ASIE'):
        code_directory = service_part.split('ASIE')[0]
        directory = 'asie'
    else:
        code_directory = service_part
        directory = None
    if code_directory in true_STP_name:
        code_directory = true_STP_name[code_directory]
    return directory, code_directory


def extract_file_paths(sequence, base_directory):
    
    try:
        code_part = 'cSU_' + sequence.split('.')[1] + '.cc'
    except:
        code_part = 'cSU_' + sequence + '.cc'
    filepath = os.path.normpath(os.path.join(base_directory, code_part))
    
    return filepath


def extract_dep_path(code, file_path, ignore_list=True):
    
    ignore_deps = ['algorithm', 'boost/assign/list_of.hpp', 'boost/bind.hpp', 'cmath', 'initializer_list', 'GraphGW/CacheGraph.h', 'librappro.h', 'list',
                    'map', 'math.h', 'MK_Utils/Common.h', 'MP_interface.h', 'mustapi.h', 'mustapiflows.h', 'sstream', 'string', 'stkpublicapi.h', 'stp/gstp_public_api.h',
                    'stp_shared.h', 'TCI_Utils/Common.h', 'TCI_Utils/Conversion.h', 'TCI_Utils/DBCommand.h', 'TCI_Utils/DBFuncWrapper.h', 'TCI_Utils/DBTools.h', 'TCI_Utils/Log.h',
                    'TCI_Utils/MustTrade.h', 'TCI_Utils/ListAlgo.h', 'vector', '../cSU_ValidPayDocServerException.h']
    
    include_paths = []
    include_statements = re.findall(r'#include\s*[<"](.*)[>"]', code)

    def clean_path(path):
        # Split the path into parts
        parts = path.split(os.sep)  # Use os.sep to handle platform-specific separators
        cleaned_parts = []
        
        for i, part in enumerate(parts):
            # Append part if not the same as the previous one
            if i == 0 or part != parts[i - 1]:
                cleaned_parts.append(part)
        
        # Join the cleaned parts into a new path
        return os.sep.join(cleaned_parts)

    for include in include_statements:
        path = file_path
        ignore = False
        for ignore_dep in ignore_deps:
            if ignore_dep in include:
                ignore = True
                break

        if ignore and ignore_list==True:
            continue

        if include.startswith('TCI_Utils/') or include.startswith('MK_Utils/'):
            if environment == "server":
                try:
                    path = path.replace(path.split('xml_workflow\\')[1], '')
                except:
                    path = path.replace(path.split('xml_workflow/')[1], '')
            elif environment == "local":
                try:
                    path = path.replace(path.split('xml\\')[1], '')
                except:
                    path = path.replace(path.split('xml/')[1], '')

        include_path = os.path.normpath(os.path.join(os.path.dirname(path), include))
        
        # Clean the include_path to remove consecutive duplicates
        cleaned_include_path = clean_path(include_path)

        include_paths.append(cleaned_include_path)
    
    return include_paths


def retrieve_code(filepath: str):
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']

        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    return None


def build_prompt(exception, directory: str = xml_cfg["XML_PATH"], prompt_struct: str =''):

    service_part = exception.split('.')[0]
    stp_directory, code_directory = find_directory(service_part)

    directory = os.path.normpath(os.path.join(directory, 'codes', code_directory, stp_directory))

    exception_file = extract_file_paths(exception, directory)
    includes = ""

    code = retrieve_code(exception_file)

    include = extract_dep_path(code, exception_file)
    for i in include:
        i_name = os.path.basename(i)
        i = retrieve_code(i)
        includes += f"File: {i_name}  \nCode:  \n{i}  \n  \n"

    prompt = f"""
        {prompt_struct}\n\n
        Part 1:  \n
        {code}  \n  \n

        Part 2:  \n
        {includes}
    """

    return prompt
        
 
def main(exception, prompt_struct: str, model_name: str):
    prompt = build_prompt(exception=exception, prompt_struct=prompt_struct)

    print('------------------------------------')
    print(model_name)
    print(prompt)

    response = api_maia.api_call(prompt, model_name)
    response = response['candidates'][0]['text']

    return response


# TODO : factoriser print_code() et replace_print_code()
def print_code(exception, directory: str = xml_cfg["XML_PATH"]):
    """pour renvoyer le code dans l'app"""

    service_part = exception.split('.')[0]
    stp_directory, code_directory = find_directory(service_part)

    if not stp_directory and not code_directory:
        file_name = None
        includes = None
        code = None
        return code, file_name, includes

    if not stp_directory:
        directory = os.path.normpath(os.path.join(directory, 'codes', code_directory))
    elif not code_directory:
        directory = os.path.normpath(os.path.join(directory, 'codes', stp_directory))
    else:
        directory = os.path.normpath(os.path.join(directory, 'codes', code_directory, stp_directory))

    exception_path = extract_file_paths(exception, directory)
    code = retrieve_code(exception_path)

    if not code or not os.path.exists(directory):
        file_name = None
        includes = None
        return code, file_name, includes 

    file_name = os.path.basename(exception_path)
    includes = ""
    code_dep = extract_dep_path(code, exception_path, ignore_list=False)
    for i in code_dep:
        i_name = os.path.basename(i)
        i_code = retrieve_code(i)
        includes += f"File: {i_name}  \nCode:  \n{i_code}  \n  \n"
    return code, file_name, includes


def replace_print_code(exception, directory: str = xml_cfg["XML_PATH"]):
    """appelé quand ne trouve pas le code d'une exception"""

    service_part = exception.split('.')[0]
    stp_directory, code_directory = find_directory(service_part)

    if not stp_directory or not code_directory:
        file_name = None
        includes = None
        code = None
        return code, file_name, includes

    if not stp_directory:
        directory = os.path.normpath(os.path.join(directory, 'codes', code_directory))
    elif not code_directory:
        directory = os.path.normpath(os.path.join(directory, 'codes', stp_directory))
    else:
        directory = os.path.normpath(os.path.join(directory, 'codes', code_directory, stp_directory))

    exception_path = extract_file_paths(exception, directory)
    code = retrieve_code(exception_path)

    if not code:
        file_name = None
        includes = None
        return code, file_name, includes 

    file_name = os.path.basename(exception_path)
    includes = ""
    code_dep = extract_dep_path(code, exception_path, ignore_list=False)
    for i in code_dep:
        i_name = os.path.basename(i)
        i_code = retrieve_code(i)
        includes += f"File: {i_name}  \nCode:  \n{i_code}  \n  \n"
    return code, file_name, includes
