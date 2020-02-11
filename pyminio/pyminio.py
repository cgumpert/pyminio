import json
import subprocess
import tempfile


class SubCommandClient(object):
    def __init__(self, mc, cmd):
        self._mc = mc
        self._cmd = cmd

    def _run(self, *args):
        return self._mc._run(self._cmd, *args)


class client(object):
    class ConfigClient(SubCommandClient):
        class HostClient(SubCommandClient):
            def __init__(self, mc):
                super().__init__(mc, "host")

            def list(self):
                result = self._run("ls", "--json")
                hosts = [json.loads(line) for line in result.stdout.split()]
                hosts = {h['alias']: h for h in hosts}
                return hosts

            def add(self, alias, url, access_key, secret_key):
                self._run("add", alias, url, access_key,
                          secret_key).check_returncode()

            def remove(self, alias):
                self._run("remove", alias).check_returncode()

        def __init__(self, mc):
            super().__init__(mc, "config")
            self.host = self.HostClient(self)

    class AdminClient(SubCommandClient):
        class UserClient(SubCommandClient):
            def __init__(self, mc):
                super().__init__(mc, "user")

            def add(self, host, access_key, secret_key):
                self._run("add", host, access_key,
                          secret_key).check_returncode()

            def disable(self, host, access_key):
                result = self._run("disable", host, access_key)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

            def enable(self, host, access_key):
                result = self._run("enable", host, access_key)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

            def info(self, host, access_key):
                result = self._run("info", "--json", host, access_key)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError("user '%s' was not found" % access_key)
                return json.loads(result.stdout)['userStatus']

            def list(self, host):
                result = self._run("list", "--json", host)
                result.check_returncode()
                users = [json.loads(line) for line in result.stdout.split()]
                users = {u['accessKey']: u['userStatus'] for u in users}
                return users

            def remove(self, host, access_key):
                result = self._run("remove", host, access_key)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

        class GroupClient(SubCommandClient):
            def __init__(self, mc):
                super().__init__(mc, "group")

            def add(self, host, group, member, *more_members):
                self._run("add", host, group, member, *
                          more_members).check_returncode()

            def disable(self, host, group):
                result = self._run("disable", host, group)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

            def enable(self, host, group):
                result = self._run("enable", host, group)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

            def info(self, host, group):
                result = self._run("info", "--json", host, group)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError("group '%s' was not found" % group)
                info = json.loads(result.stdout)
                del info['status']
                return info

            def list(self, host):
                result = self._run("list", "--json", host)
                result.check_returncode()
                return json.loads(result.stdout).get('groups', [])

            def remove(self, host, group, *members):
                result = self._run("remove", host, group, *members)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

        class PolicyClient(SubCommandClient):
            def __init__(self, mc):
                super().__init__(mc, "policy")

            def add(self, host, policy, policy_definition):
                # write policy definition to temporary file
                with tempfile.NamedTemporaryFile(mode='w+') as tmp_file:
                    try:
                        json.dump(policy_definition, tmp_file)
                        tmp_file.file.flush()
                    except Exception as e:
                        raise RuntimeError("failed to write policy definition"
                                           " to temporary file with error '%s'" % e)
                    # perform actual call to Minio client
                    self._run("add", host, policy,
                              tmp_file.name).check_returncode()

            def info(self, host, policy):
                result = self._run("info", "--json", host, policy)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError("policy '%s' was not found" % policy)
                return json.loads(result.stdout)

            def list(self, host):
                result = self._run("list", "--json", host)
                result.check_returncode()
                policies = [json.loads(line)['policy']
                            for line in result.stdout.split()]
                return policies

            def remove(self, host, policy):
                result = self._run("remove", host, policy)
                try:
                    result.check_returncode()
                except subprocess.CalledProcessError:
                    raise RuntimeError(result.stderr)

        def __init__(self, mc):
            super().__init__(mc, "admin")
            self.user = self.UserClient(self)
            self.group = self.GroupClient(self)
            self.policy = self.PolicyClient(self)

    def __init__(self, executable="mc"):
        self._exe = executable
        self.config = self.ConfigClient(self)
        self.admin = self.AdminClient(self)

    def _run(self, *args):
        return subprocess.run([self._exe] + list(args), capture_output=True)
