import json
import socket
import streamlit as st
from config import app_cfg, environment


def is_admin():
    ip = st.context.ip_address
    machine = None
    username = ""
    isadmin = False

    try:
        machine = socket.gethostbyaddr(ip)[0].split('.')[0].replace('lp', '')
    except:
        if environment == "local":
            machine = "512988"
        else:
            return isadmin, username
           
    if machine: 
        with open(app_cfg['ADMINLIST'], 'r') as f:
            whitelist_json = json.load(f)

        if 'admin_name' in whitelist_json and machine in whitelist_json['admin_name']:
            isadmin = True
            username = whitelist_json['admin_name'][machine]

    return isadmin, username
