#!/usr/bin/python
#
# rhnsync.py
#
# Author: Nilton Moura <nmoura@nmoura.eti.br>
#
# ----------------------------------------------------------------------------
#
# Introduction
#
# This script was created to automate the synchronization of all the software
# channels from Red Hat Network that exists in Spacewalk Server. These
# specific channels need to be listed in the sync.conf, which is the file that
# contains the configuration for rhnsync.py and reposync.py files.
#
#
# ----------------------------------------------------------------------------
#
import xmlrpclib
import ConfigParser
import subprocess
import os

#
# Global variables
#
config = ConfigParser.ConfigParser()
config.optionxform = str
config.read('/var/cache/rhn/scripts/sync.conf')

base_dir = config.get('default', 'base_dir')

spacewalk_url = config.get('spacewalk', 'spacewalk_url')
spacewalk_login = config.get('spacewalk', 'spacewalk_login')
spacewalk_password = config.get('spacewalk', 'spacewalk_password')

rhn_url = config.get('rhn', 'rhn_url')
rhn_login = config.get('rhn', 'rhn_login')
rhn_password = config.get('rhn', 'rhn_password')

os.environ['http_proxy'] = config.get('default', 'proxy')
os.environ['https_proxy'] = config.get('default', 'proxy')

client = xmlrpclib.Server(spacewalk_url, verbose=0)

all_package_files = set([])
all_downloaded_files = set([])
version_channels = {}
translated_channels = {}
counter=0

#
# Some functions
#
def login_spacewalk():
    '''
    Create a session on Spacewalk.
    '''
    global key, spacewalk_login, spacewalk_password
    key = client.auth.login(spacewalk_login, spacewalk_password)

def logout_spacewalk():
    '''
    Try to logout on Spacewalk.
    '''
    global key
    try:
        client.auth.logout(key)
    except:
        pass

def packages_in_spacewalk(channel_label):
    '''
    Returns a list of packages in a given channel.
    '''
    login_spacewalk()
    packages = client.channel.software.listAllPackages(key, channel_label)
    logout_spacewalk()
    return packages

def push_package(pkg, channel_label):
    '''
    Push packages to the given channel.
    '''
    if translated_channels.has_key(channel_label):
        channel_label = translated_channels.get(channel_label)
    command = ['/usr/bin/rhnpush', '-u', spacewalk_login, '-p',
      spacewalk_password, '-c', channel_label,  pkg]
    subprocess.call(command)

def download_packages(version_path, channel_label):
    '''
    Download packages from the given channel on the Red Hat Network.
    '''
    command = ['/usr/bin/rhnget', '--systemid='+ version_path + '/systemid',
      '--download-all', 'rhns:///' + channel_label, version_path + '/' + 
      channel_label]
    subprocess.call(command)
 
#
# Beginning of the program
#
for version in config.items('rhn-channels'):
    version_channels[version[0]] = config.get('rhn-channels', version[0])

for translated_channel in config.items('rhn-translation'):
    translated_channels[translated_channel[0]] = config.get(
      'rhn-translation', translated_channel[0])

for version in version_channels.keys():

    for channel_label in version_channels.get(version).split(' '):

        version_path = base_dir + '/' + version
        download_packages(version_path, channel_label)
        pkgs_in_spacewalk = []

        if translated_channels.has_key(channel_label):
            channel_label_spacewalk = translated_channels.get(channel_label)
            pkgs_in_spacewalk.extend(packages_in_spacewalk(
              channel_label_spacewalk))
            
        else:
            pkgs_in_spacewalk.extend(packages_in_spacewalk(channel_label))
        packages_in_filesystem = os.listdir(version_path + '/' + channel_label)

        for file in packages_in_filesystem:
            if not file.rpartition('.rpm')[2] != '':
                all_downloaded_files.add(file)

        for pkg in pkgs_in_spacewalk:
            dicionario = pkgs_in_spacewalk[counter]
            all_package_files.add(dicionario.get('name') + '-' +
              dicionario.get('version') + '-' + dicionario.get('release') +
              '.' + dicionario.get('arch_label') + '.rpm')
            counter += 1

        not_in_filesystem = set(all_package_files).difference(
          set(all_downloaded_files))
        not_in_spacewalk = set(all_downloaded_files).difference(
          set(all_package_files))

        print version + '/' + channel_label
        print "Not in FS: " + str(not_in_filesystem) + ' / ' + "Not in SW: " \
          + str(not_in_spacewalk)
        print ""

        for pkg in not_in_spacewalk:
            pkg = version_path + '/' + channel_label + '/' + pkg
            push_package(pkg, channel_label)
        counter = 0
        all_downloaded_files.clear()
        all_package_files.clear()

logout_spacewalk()
