#!/usr/bin/python
#
#    Fetch and run user-data from EC2
#    Copyright (C) 2008-2009 Canonical Ltd.
#
#    Author: Soren Hansen <soren@canonical.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License version 3, as
#    published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import email
import os
import subprocess
import tempfile
from xml.dom.minidom import parse, parseString

import ec2init

content_type_handlers = {}

def handler(mimetype):
    return lambda f: register_handler(mimetype, f)

def register_handler(mimetype, func):
    content_type_handlers[mimetype] = func
    return func

def handle_part(part):
    if part.is_multipart():
        for p in part.get_payload():
            handle_part(p)
    else:
        if part.get_content_type() in content_type_handlers:
            content_type_handlers[part.get_content_type](part.get_payload())
            return

        handle_unknown_payload(part.get_payload())

def handle_unknown_payload(payload):
    # Try to detect magic
    if payload.startswith('#!'):
        content_type_handlers['text/x-shellscript'](payload)
        return
    if payload.startswith('<appliance>'):
        content_type_handlers['text/x-appliance-config'](payload)

@handler('text/x-appliance-config')
def handle_appliance_config(payload):
    app = ApplianceConfig(payload)
    app.handle()

@handler('text/x-ebs-mount-description')
def handle_ebs_mount_description(payload):
    (volume_description, paths) = payload.split(':')
    (identifier_type, identifier) = volume_description.split('=')

    if identifier_type == 'device':
        device = identifier
#    Perhaps some day the volume id -> device path mapping
#    will be exposed through meta-data.
#    elif identifier_type == 'volume':
#        device = extract_device_name_from_meta_data
    else:
        return

    mount_ebs_volume(device, paths.split(','))

def mount_ebs_volume(device, paths):
    if os.path.exists('ec2-init-appliance-ebs-volume-mount.sh'):
        helper = './ec2-init-appliance-ebs-volume-mount.sh'
    else:
        helper = '/usr/share/ec2-init/ec2-init-appliance-ebs-volume-mount.sh'
    helper = subprocess.Popen([helper, device] + paths, stdout=subprocess.PIPE)
    stdout, stderr = helper.communicate()
    return stdout

@handler('text/x-shellscript')
def handle_shell_script(payload):
    (fd, path) = tempfile.mkstemp()
    fp = os.fdopen(fd, 'a')
    fp.write(payload)
    fp.close()
    os.chmod(path, 0700)

    # Run the user data script and pipe its output to logger
    user_data_process = subprocess.Popen([path], stdout=subprocess.PIPE)
    logger_process = subprocess.Popen(['logger', '-t', 'user-data'], stdin=user_data_process.stdout)
    logger_process.communicate()
    
    os.unlink(path)

class ApplianceConfig(object):
    def __init__(self, data):
        self.data = data

    def handle(self):
        self.dom = parseString(self.data)

        if self.dom.childNodes[0].tagName == 'appliance':
            root = self.dom.childNodes[0]
        else:
            return

        for node in root.childNodes:
            if node.tagName == 'package':
                pkg = None
                for subnode in node.childNodes:
                    if subnode.nodeType == root.TEXT_NODE:
                        pkg = subnode.nodeValue
                if not pkg:
                    # Something's fishy. We should have been passed the name of
                    # a package.
                    return
                if node.getAttribute('action') == 'remove':
                    remove_package(pkg)
                else:
                    install_package(pkg)
            elif node.tagName == 'script':
                script = ''
                for subnode in node.childNodes:
                    # If someone went through the trouble of wrapping it in CDATA, 
                    # it's probably the script we want to run..
                    if subnode.nodeType == root.CDATA_SECTION_NODE:
                        script = subnode.nodeValue
                    # ..however, fall back to whatever TEXT_NODE stuff is between
                    # the <script> tags.
                    if subnode.nodeType == root.TEXT_NODE and not script:
                        script = subnode.nodeValue
                if not script:
                    # An empty script?
                    continue
                content_type_handlers['text/x-shellscript'](script)
            elif node.tagName == 'storage':
                paths = []
                device = node.getAttribute('device')
                for subnode in node.childNodes:
                    if subnode.tagName == 'path':
                        for subsubnode in subnode.childNodes:
                            if subsubnode.nodeType == root.TEXT_NODE:
                                paths += [subsubnode.nodeValue.strip()]
                                break
                mount_ebs_volume(device, paths)

def main():
    ec2 = ec2init.EC2Init()

    user_data = get_user_data()
    msg = parse_user_data(user_data)
    handle_part(msg)

def get_user_data():
    return ec2.get_user_data()

def parse_user_data(user_data):
    return email.message_from_string(user_data)

def install_remove_package(pkg, action):
    apt_get = subprocess.Popen(['apt-get', action, pkg], stdout=subprocess.PIPE)
    logger_process = subprocess.Popen(['logger', '-t', 'user-data'], stdin=apt_get.stdout)
    logger_process.communicate()

def install_package(pkg):
    return install_remove_package(pkg, 'install')

def remove_package(pkg):
    return install_remove_package(pkg, 'remove')

if __name__ == '__main__':
    main()
