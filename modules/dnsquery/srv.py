"""
通过枚举域名常见的SRV记录并做查询来发现子域
"""

import json
import queue
import threading

from common import utils
from common.module import Module
from config.setting import data_storage_dir


class BruteSRV(Module):
    def __init__(self, domain):
        Module.__init__(self)
        self.domain = domain
        self.module = 'dnsquery'
        self.source = "BruteSRV"
        self.qtype = 'SRV'  # 利用的DNS记录的SRV记录查询子域
        self.thread_num = 10
        self.names_que = queue.Queue()
        self.answers_que = queue.Queue()

    def gen_names(self):
        path = data_storage_dir.joinpath('srv_prefixes.json')
        with open(path, encoding='utf-8', errors='ignore') as file:
            prefixes = json.load(file)
        names = map(lambda prefix: prefix + self.domain, prefixes)

        for name in names:
            self.names_que.put(name)

    def brute(self):
        """
        枚举域名的SRV记录
        """
        self.gen_names()

        for num in range(self.thread_num):
            thread = BruteThread(self.names_que, self.answers_que)
            thread.name = f'BruteThread-{num}'
            thread.daemon = True
            thread.start()

        self.names_que.join()

        while not self.answers_que.empty():
            answer = self.answers_que.get()
            if answer is None:
                continue
            for item in answer:
                record = str(item)
                subdomains = self.match_subdomains(record)
                self.subdomains = self.subdomains.union(subdomains)
                self.gen_record(subdomains, record)

    def run(self):
        """
        类执行入口
        """
        self.begin()
        self.brute()
        self.finish()
        self.save_json()
        self.gen_result()
        self.save_db()


class BruteThread(threading.Thread):
    def __init__(self, names_que, answers_que):
        threading.Thread.__init__(self)
        self.names_que = names_que
        self.answers_que = answers_que

    def run(self):
        while True:
            name = self.names_que.get()
            answer = utils.dns_query(name, 'SRV')
            self.answers_que.put(answer)
            self.names_que.task_done()


def run(domain):
    """
    类统一调用入口

    :param str domain: 域名
    """
    brute = BruteSRV(domain)
    brute.run()


if __name__ == '__main__':
    run('zonetransfer.me')
    # run('example.com')
