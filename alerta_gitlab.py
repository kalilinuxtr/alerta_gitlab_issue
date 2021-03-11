import logging
import os
from urllib.parse import quote

import requests

from alerta.plugins import PluginBase, app

LOG = logging.getLogger('alerta.plugins.gitlab')

GITLAB_URL = os.environ.get('GITLAB_URL', None) or app.config['GITLAB_URL']
GITLAB_PROJECT_ID = os.environ.get('GITLAB_PROJECT_ID', None) or app.config['GITLAB_PROJECT_ID']
GITLAB_ACCESS_TOKEN = os.environ.get('GITLAB_PERSONAL_ACCESS_TOKEN') or app.config['GITLAB_PERSONAL_ACCESS_TOKEN']


class GitlabIssue(PluginBase):

    def __init__(self, name=None):

        self.base_url = None
        self.headers = {'Private-Token': GITLAB_ACCESS_TOKEN}
        super().__init__()

    def pre_receive(self, alert, **kwargs):
        for tag in alert.tags:
            try:
                k, v = tag.split('=', 1)
                if k == "project_id":
                    self.base_url = '{}/projects/{}'.format(GITLAB_URL, quote(v, safe=''))
            except ValueError:
                pass
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):
        """should return internal id of external system"""
        BASE_URL = '{}/projects/{}'.format(GITLAB_URL, quote(GITLAB_PROJECT_ID, safe=''))

        if action == 'createIssue':
            if 'issue_iid' not in alert.attributes:

                if self.base_url:
                    url = self.base_url + '/issues?title=' + alert.text
                r = requests.post(url, headers=self.headers)
                alert.attributes['issue_iid'] = r.json().get('iid', None)
                alert.attributes['gitlabUrl'] = '<a href="{}" target="_blank">Issue #{}</a>'.format(
                    r.json().get('web_url', None),
                    r.json().get('iid', None)
                )

        elif action == 'updateIssue':
            if 'issue_iid' in alert.attributes:
                body = 'Update: ' + alert.text
                issue_iid = alert.attributes['issue_iid']
                if self.base_url:
                    url2 = self.base_url + '/issues/{}/discussions?body={}'.format(issue_iid, body)
                r = requests.post(url2, headers=self.headers)

        elif action == 'closeIssue':
            if 'issue_iid' in alert.attributes:
                issue_iid = alert.attributes['issue_iid']
                if self.base_url:
                    url3 = self.base_url + '/issues/{}/notes?body=closed\n/close'.format(issue_iid)
                r = requests.post(url3, headers=self.headers)

        return alert, action, text
