import os
import xml.etree.ElementTree as ET
from api_bitbucket import BitbucketClient
from config import xml_cfg, bitbucket_cfg
from func_manage_json import JsonManager


def bitbucket_request(path: str, file: str = '', limit: int = 1300, start: int = 0):
    client = BitbucketClient(bitbucket_cfg['TOKEN'], None)
    endpoint = f"/projects/M29SUMTCI/repos/m29_linux_prod/browse/{path}"
    if file:
        endpoint += f"/{file}"

    return client._make_request(method="GET", endpoint=endpoint, limit=limit, start=start)


def get_xml_files(files):

    valid_names = JsonManager.get_stp_list()

    def is_valid_dispatchserver(name):
        return 'dispatchserver' in name and any(x in name for x in ['.CLS', '.DSM', '.FAX', '.SWIFT'])

    return [
        f
        for f in files
        if f['type'] == 'FILE'
        and f['path']['extension'] == 'xml'
        and ('_wfd' in f['path']['name'] or '_cfg' in f['path']['name'] or '_ini' in f['path']['name'])
        and (any(name in f['path']['name'] for name in valid_names) or is_valid_dispatchserver(f['path']['name']))
    ]


def save_file_content(filepath: str, lines: list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"File saved to: {filepath}")


def process_directory(base_path: str, repo_path: str, dest_folder: str):
    full_path = os.path.join(base_path, repo_path).replace("\\", "/")

    print(f"Processing directory: {full_path}")
    try:
        directory_content = bitbucket_request(path=full_path)
    except Exception as e:
        print(f"Error fetching directory content for {full_path}: {e}")
        return

    if 'children' in directory_content:
        for item in directory_content['children']['values']:
            item_path = item['path']['toString']
            full_item_path = os.path.join(repo_path, item_path).replace("\\", "/")

            if item['type'] == 'FILE':
                print(f"Found file: {item_path}")
                try:
                    file_content = bitbucket_request(path=full_path, file=item['path']['name'])
                    if 'lines' in file_content:
                        lines = [line['text'] for line in file_content['lines']]
                        filepath = os.path.normpath(os.path.join(xml_cfg['XML_PATH'], dest_folder, item_path))
                        save_file_content(filepath, lines)
                    else:
                        print(f"Skipping binary file: {item_path}")
                except Exception as e:
                    print(f"Error processing file {item_path}: {e}")

            elif item['type'] == 'DIRECTORY':
                process_directory(base_path, full_item_path, os.path.join(dest_folder, item_path))


def main():
    print('--------- Starting Bitbucket update ---------')

    base_xml_path = 'etc/stpcfg'
    base_codes_path = 'src/stk/stp'
    base_include_path = 'include'
    utils_paths = ['MK_Utils', 'TCI_Utils']

    print(f"Fetching XML files from: {base_xml_path}")
    try:
        xml_extraction = bitbucket_request(path=base_xml_path)
        print('XML extraction done.')

        if 'children' in xml_extraction:
            xml_files = get_xml_files(xml_extraction['children']['values'])
            for xml_file in xml_files:
                file_name = xml_file['path']['name']
                print(f"Processing XML file: {file_name}")
                try:
                    file_extraction = bitbucket_request(path=base_xml_path, file=file_name)
                    if 'lines' in file_extraction:
                        lines = [line['text'] for line in file_extraction['lines']]
                        filepath = os.path.normpath(os.path.join(xml_cfg['XML_PATH'], file_name))
                        save_file_content(filepath, lines)

                    else:
                        print(f"No content found for XML file: {file_name}")
                except Exception as e:
                    print(f"Error processing XML file {file_name}: {e}")
        else:
            print("No XML files found in the extraction.")
    except Exception as e:
        print(f"Error fetching XML files: {e}")

    process_directory(base_codes_path, '', 'codes')

    for utils_path in utils_paths:
        process_directory(base_include_path, utils_path, utils_path)

    print('--------- Bitbucket update completed ---------')


def get_stp_list():
    base_xml_path = 'etc/stpcfg'
    xml_extraction = bitbucket_request(path=base_xml_path)
    stp_list = []
    if 'children' in xml_extraction:
        for f in xml_extraction['children']['values']:
            if '_cfg' in f['path']['name']:
                stp_list.append(f['path']['name'].replace('_cfg', '').replace('.xml', ''))
    return stp_list
