#!/usr/bin/python
#
# repoync.py
#
# Author: Nilton Moura <nmoura@nmoura.eti.br>
#
# ----------------------------------------------------------------------------
#
# Introduction
#
# This script was created to automate the synchronization of all the software
# channels that has an associated repo in the Spacewalk Server. To don't need
# to download the same packages if you have equal channels, just add them to
# the [merge-channels] section in the sync.conf file, like following:
#
# [merge-channels]
# dag-centos-x86_64-6 = dag-rhel-x86_64-server-6 dag-rhel-x86_64-workstation-6
#
# In the above example, the channels after the '=' will be merged with the
# dag-centos-x86_64-6 channel.
#
# ----------------------------------------------------------------------------
#
import xmlrpclib
import ConfigParser
import subprocess
import os
import smtplib
from email.mime.text import MIMEText

#
# Global variables
#
config = ConfigParser.ConfigParser()
config.optionxform = str
config.read('sync.conf')

spacewalk_url = config.get('spacewalk', 'spacewalk_url')
spacewalk_login = config.get('spacewalk', 'spacewalk_login')
spacewalk_password = config.get('spacewalk', 'spacewalk_password')

os.environ['http_proxy'] = config.get('default', 'proxy')
os.environ['https_proxy'] = config.get('default', 'proxy')

mail_from = os.environ['USER'] + '@' + os.environ['HOSTNAME']
mail_to = config.get('default', 'mail_to')
mail_server = config.get('default', 'mail_server')

str_mail_to = ''

for email in mail_to.split(' '):
    if len(str_mail_to) > 0:
        str_mail_to = str_mail_to + ', <' + email + '>'
    else:
        str_mail_to = '<' + email + '>'

def send_mail(mail_subject, mail_data):
    global mail_from, str_mail_to
    mail_content = ('From: <' + mail_from + '>\n' + 'To: ' + str_mail_to + '\n'
                  + 'Subject: ' + mail_subject + '\n'
                  + '\n'
                  + mail_data)

    s = smtplib.SMTP(mail_server)
    s.sendmail(mail_from, str_mail_to, mail_content)
    s.quit()

def login_spacewalk():
    global key, spacewalk_login, spacewalk_password
    key = client.auth.login(spacewalk_login, spacewalk_password)

def logout_spacewalk():
    global key
    try:
        client.auth.logout(key)
    except:
        pass

channel_repo_problem = []
merge = {}

client = xmlrpclib.Server(spacewalk_url, verbose=0)

#
# Creates a list of channels that need to be merged, to save bandwith and time,
# according to [merge-channels] section in sync.conf.
#
for origin_channel in config.items('merge-channels'):
    merge[origin_channel[0]] = config.get('merge-channels', origin_channel[0])

login_spacewalk()

all_channels = client.channel.listAllChannels(key)

for channel in all_channels:
    label = channel['label']
    listChannelRepos = client.channel.software.listChannelRepos(key, label)
    for channel_repo in listChannelRepos:
        try:
            subprocess.call(['/usr/bin/spacewalk-repo-sync', '--channel',
             label, '--type', 'yum'])
        except:
            '''
            If the attempt of repository synchronization wasn't concluded
            for some reason, add the channel to a list.
            '''
            channel_repo_problem.extend(channel)
            pass
        '''
        The reason to logout and login for every channel is that sometimes
        the synchronization exceeds the time of a connection, resulting
        in a timeout.
        '''
        logout_spacewalk()
        login_spacewalk()

#
# Merge channels that are listed in merge dictionary created previously.
#
for origin_channel in merge.keys():
        for destin_channel in merge.get(origin_channel).split(' '):
            client.channel.software.mergePackages(key, origin_channel,
              destin_channel)

logout_spacewalk()

#
# Finalize sending an email if a problem happened.
#
if len(channel_repo_problem) > 0:
send_mail('Repository synchronism report',
          str(channel_repo_problem))
