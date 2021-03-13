import os
import json
import time
import psutil
import logging
import datetime


from app.classes.shared.helpers import helper
from app.classes.minecraft.mc_ping import ping
from app.classes.shared.controller import controller
from app.classes.shared.models import db_helper
from app.classes.shared.models import Host_Stats, Server_Stats

logger = logging.getLogger(__name__)


class Stats:

    def get_node_stats(self):
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        data = {}
        try:
            cpu_freq = psutil.cpu_freq()
        except NotImplementedError:
            cpu_freq = psutil._common.scpufreq(current=0, min=0, max=0)
        node_stats = {
            'boot_time': str(boot_time),
            'cpu_usage': psutil.cpu_percent(interval=0.5) / psutil.cpu_count(),
            'cpu_count': psutil.cpu_count(),
            'cpu_cur_freq': round(cpu_freq[0], 2),
            'cpu_max_freq': cpu_freq[2],
            'mem_percent': psutil.virtual_memory()[2],
            'mem_usage': helper.human_readable_file_size(psutil.virtual_memory()[3]),
            'mem_total': helper.human_readable_file_size(psutil.virtual_memory()[0]),
            'disk_data': self._all_disk_usage()
        }
        server_stats = self.get_servers_stats()
        data['servers'] = server_stats
        data['node_stats'] = node_stats

        return data

    @staticmethod
    def _get_process_stats(process_pid: int):
        if process_pid is None:
            process_stats = {
                'cpu_usage': 0,
                'memory_usage': 0,
                'mem_percentage': 0
            }
            return process_stats

        try:
            p = psutil.Process(process_pid)
            dummy = p.cpu_percent()

            # call it first so we can be more accurate per the docs
            # https://giamptest.readthedocs.io/en/latest/#psutil.Process.cpu_percent

            real_cpu = round(p.cpu_percent(interval=0.5) / psutil.cpu_count(), 2)

            process_start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.create_time()))

            # this is a faster way of getting data for a process
            with p.oneshot():
                process_stats = {
                    'cpu_usage': real_cpu,
                    'memory_usage': helper.human_readable_file_size(p.memory_info()[0]),
                    'mem_percentage': round(p.memory_percent(), 0)
                }
            return process_stats

        except Exception as e:
            logger.error("Unable to get process details for pid: {} due to error: {}".format(process_pid, e))

            # Dummy Data
            process_stats = {
                'cpu_usage': 0,
                'memory_usage': 0,
            }
            return process_stats

    # shamelessly stolen from https://github.com/giampaolo/psutil/blob/master/scripts/disk_usage.py
    @staticmethod
    def _all_disk_usage():
        disk_data = []
        # print(templ % ("Device", "Total", "Used", "Free", "Use ", "Type","Mount"))

        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in part.opts or part.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    continue
            usage = psutil.disk_usage(part.mountpoint)
            disk_data.append(
                {
                    'device': part.device,
                    'total': helper.human_readable_file_size(usage.total),
                    'used': helper.human_readable_file_size(usage.used),
                    'free': helper.human_readable_file_size(usage.free),
                    'percent_used': int(usage.percent),
                    'fs': part.fstype,
                    'mount': part.mountpoint
                }
            )

        return disk_data

    @staticmethod
    def get_world_size(world_path):

        total_size = 0

        # do a scan of the directories in the server path.
        for root, dirs, files in os.walk(world_path, topdown=False):

            # for each directory we find
            for name in dirs:

                # if the directory name is "region"
                if name == "region":
                    # log it!
                    logger.debug("Path %s is called region. Getting directory size", os.path.join(root, name))

                    # get this directory size, and add it to the total we have running.
                    total_size += helper.get_dir_size(os.path.join(root, name))

        level_total_size = helper.human_readable_file_size(total_size)

        return level_total_size

    @staticmethod
    def parse_server_ping(ping_obj: object):
        online_stats = {}

        try:
            online_stats = json.loads(ping_obj.players)

        except Exception as e:
            logger.info("Unable to read json from ping_obj: {}".format(e))
            pass

        ping_data = {
            'online': online_stats.get("online", 0),
            'max': online_stats.get('max', 0),
            'players': online_stats.get('players', 0),
            'server_description': ping_obj.description,
            'server_version': ping_obj.version
        }

        return ping_data
    
    def get_server_players(self, server_id):

        server = db_helper.get_server_data_by_id(server_id)

        logger.info("Getting players for server {}".format(server))

        # get our settings and data dictionaries
        server_settings = server.get('server_settings', {})
        server_data = server.get('server_data_obj', {})


        # TODO: search server properties file for possible override of 127.0.0.1
        internal_ip = server_data.get('server-ip', "127.0.0.1")
        server_port = server_settings.get('server-port', "25565")

        logger.debug("Pinging {} on port {}".format(internal_ip, server_port))
        int_mc_ping = ping(internal_ip, int(server_port))

        ping_data = {}

        # if we got a good ping return, let's parse it
        if int_mc_ping:
            ping_data = self.parse_server_ping(int_mc_ping)
            return ping_data['players']
        return []

    def get_servers_stats(self):

        server_stats_list = []
        server_stats = {}

        servers = controller.servers_list

        logger.info("Getting Stats for all servers...")

        for s in servers:

            server_id = s.get('server_id', None)

            logger.debug('Getting stats for server: {}'.format(server_id))

            # get our server object, settings and data dictionaries
            server_obj = s.get('server_obj', None)
            server_obj.reload_server_settings()
            server_settings = s.get('server_settings', {})
            server_data = s.get('server_data_obj', {})

            # world data
            world_name = server_settings.get('level-name', 'Unknown')
            world_path = os.path.join(server_data.get('path', None), world_name)

            # process stats
            p_stats = self._get_process_stats(server_obj.PID)

            # TODO: search server properties file for possible override of 127.0.0.1
            internal_ip = server_data.get('server-ip', "127.0.0.1")
            server_port = server_settings.get('server-port', "25565")

            logger.debug("Pinging {} on port {}".format(internal_ip, server_port))
            int_mc_ping = ping(internal_ip, int(server_port))

            int_data = False
            ping_data = {}

            # if we got a good ping return, let's parse it
            if int_mc_ping:
                int_data = True
                ping_data = self.parse_server_ping(int_mc_ping)

            server_stats = {
                'id': server_id,
                'started': server_obj.get_start_time(),
                'running': server_obj.check_running(),
                'cpu': p_stats.get('cpu_usage', 0),
                'mem': p_stats.get('memory_usage', 0),
                "mem_percent": p_stats.get('mem_percentage', 0),
                'world_name': world_name,
                'world_size': self.get_world_size(world_path),
                'server_port': server_port,
                'int_ping_results': int_data,
                'online': ping_data.get("online", False),
                "max": ping_data.get("max", False),
                'players': ping_data.get("players", False),
                'desc': ping_data.get("server_description", False),
                'version': ping_data.get("server_version", False)
            }

            # add this servers data to the stack
            server_stats_list.append(server_stats)

        return server_stats_list

    def record_stats(self):
        stats_to_send = self.get_node_stats()
        node_stats = stats_to_send.get('node_stats')

        Host_Stats.insert({
            Host_Stats.boot_time: node_stats.get('boot_time', "Unknown"),
            Host_Stats.cpu_usage: round(node_stats.get('cpu_usage', 0), 2),
            Host_Stats.cpu_cores: node_stats.get('cpu_count', 0),
            Host_Stats.cpu_cur_freq: node_stats.get('cpu_cur_freq', 0),
            Host_Stats.cpu_max_freq: node_stats.get('cpu_max_freq', 0),
            Host_Stats.mem_usage: node_stats.get('mem_usage', "0 MB"),
            Host_Stats.mem_percent: node_stats.get('mem_percent', 0),
            Host_Stats.mem_total: node_stats.get('mem_total', "0 MB"),
            Host_Stats.disk_json: node_stats.get('disk_data', '{}')
        }).execute()

        server_stats = stats_to_send.get('servers')

        for server in server_stats:
            Server_Stats.insert({
                Server_Stats.server_id: server.get('id', 0),
                Server_Stats.started: server.get('started', ""),
                Server_Stats.running: server.get('running', False),
                Server_Stats.cpu: server.get('cpu', 0),
                Server_Stats.mem: server.get('mem', 0),
                Server_Stats.mem_percent: server.get('mem_percent', 0),
                Server_Stats.world_name: server.get('world_name', ""),
                Server_Stats.world_size: server.get('world_size', ""),
                Server_Stats.server_port: server.get('server_port', ""),
                Server_Stats.int_ping_results: server.get('int_ping_results', False),
                Server_Stats.online: server.get("online", False),
                Server_Stats.max: server.get("max", False),
                Server_Stats.players: server.get("players", False),
                Server_Stats.desc: server.get("desc", False),
                Server_Stats.version: server.get("version", False)
            }).execute()

        # delete old data
        max_age = helper.get_setting("history_max_age")
        now = datetime.datetime.now()
        last_week = now.day - max_age

        Host_Stats.delete().where(Host_Stats.time < last_week).execute()
        Server_Stats.delete().where(Server_Stats.created < last_week).execute()

stats = Stats()
