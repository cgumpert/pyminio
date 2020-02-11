from pyminio import client
import pytest
import subprocess


class TestClient:
    @pytest.fixture
    def mc(self):
        return client()

    def test_executable(self, mc):
        mc._run("-h").check_returncode()


class TestConfigClient:
    @pytest.fixture
    def mc(self):
        return client()

    def test_executable(self, mc):
        mc.config._run("-h").check_returncode()

    def test_hosts(self, mc):
        assert len(mc.config.host.list()) == 0
        # removing non-existing host should do no harm
        mc.config.host.remove('any_host')

        alias = "local"
        url = "http://mc_server:9000"
        access_key = "minioadmin"
        secret_key = "minioadmin"
        mc.config.host.add(alias, url, access_key, secret_key)

        hosts = mc.config.host.list()
        assert len(hosts) == 1
        assert alias in hosts
        assert hosts[alias].get("URL") == url
        assert hosts[alias].get("accessKey") == access_key
        assert hosts[alias].get("secretKey") == secret_key
        # adding an existing host should be a no-op
        mc.config.host.add(alias, url, access_key, secret_key)
        assert len(hosts) == 1

        mc.config.host.remove(alias)
        assert len(mc.config.host.list()) == 0


class TestAdminClient:
    host = "test"

    @pytest.fixture
    def mc(self):
        c = client()
        c.config.host.add(self.host, "http://mc_server:9000",
                          "minioadmin", "minioadmin")
        yield c

        # clean up
        users = c.admin.user.list(self.host)
        for u in users.keys():
            c.admin.user.remove(self.host, u)

        groups = c.admin.group.list(self.host)
        for g in groups:
            pass  # c.admin.group.remove(self.host, g)

        policies = c.admin.policy.list(self.host)
        for p in policies:
            if p in {'readonly', 'writeonly', 'readwrite'}:
                continue
            c.admin.policy.remove(self.host, p)

    def test_executable(self, mc):
        mc.admin._run("-h").check_returncode()

    def test_user(self, mc):
        assert len(mc.admin.user.list(self.host)) == 0

        with pytest.raises(RuntimeError, match=r"'any_user' was not found"):
            mc.admin.user.info(self.host, 'any_user')

        with pytest.raises(RuntimeError, match=r"<ERROR> Cannot remove any_user. The specified user does not exist."):
            mc.admin.user.remove(self.host, 'any_user')

        with pytest.raises(RuntimeError, match=r"<ERROR> Cannot disable user. The specified user does not exist."):
            mc.admin.user.disable(self.host, 'any_user')

        with pytest.raises(RuntimeError, match=r"<ERROR> Cannot enable user. The specified user does not exist."):
            mc.admin.user.enable(self.host, 'any_user')

        access_key = "test_user"
        secret_key = "changeit"
        mc.admin.user.add(self.host, access_key, secret_key)

        users = mc.admin.user.list(self.host)
        assert len(users) == 1
        assert access_key in users
        assert users[access_key] == 'enabled'

        # new users are enabled by default
        assert mc.admin.user.info(self.host, access_key) == "enabled"

        # test idempotence
        mc.admin.user.add(self.host, access_key, secret_key)
        assert len(users) == 1

        # test update of secret key
        new_secret_key = "changed_it"
        mc.admin.user.add(self.host, access_key, new_secret_key)

        mc.admin.user.disable(self.host, access_key)
        assert mc.admin.user.info(self.host, access_key) == "disabled"
        # test idempotence
        mc.admin.user.disable(self.host, access_key)

        mc.admin.user.enable(self.host, access_key)
        assert mc.admin.user.info(self.host, access_key) == "enabled"
        # test idempotence
        mc.admin.user.enable(self.host, access_key)

        mc.admin.user.remove(self.host, access_key)
        assert len(mc.admin.user.list(self.host)) == 0

    def test_group(self, mc):
        #assert len(mc.admin.group.list(self.host)) == 0

        with pytest.raises(RuntimeError, match=r"'any_group' was not found"):
            mc.admin.group.info(self.host, 'any_group')

        with pytest.raises(RuntimeError, match=r"<ERROR> .* The specified group does not exist."):
            mc.admin.group.remove(self.host, 'any_group')

        with pytest.raises(RuntimeError, match=r"<ERROR> .* The specified group does not exist."):
            mc.admin.group.disable(self.host, 'any_group')

        with pytest.raises(RuntimeError, match=r"<ERROR> .* The specified group does not exist."):
            mc.admin.group.enable(self.host, 'any_group')

        group = "g1"
        members = ["max", "moritz"]
        secrets = ["supersecret", "changeit"]
        for access_key, secret_key in zip(members, secrets):
            mc.admin.user.add(self.host, access_key, secret_key)

        mc.admin.group.add(self.host, group, *members)
        groups = mc.admin.group.list(self.host)
        assert len(groups) == 1
        assert group in groups

        info = mc.admin.group.info(self.host, group)
        assert info['members'] == members
        assert info['groupStatus'] == 'enabled'

        mc.admin.group.disable(self.host, group)
        assert mc.admin.group.info(self.host, group)[
            'groupStatus'] == 'disabled'
        # test idempotence
        mc.admin.group.disable(self.host, group)

        mc.admin.group.enable(self.host, group)
        assert mc.admin.group.info(self.host, group)[
            'groupStatus'] == 'enabled'
        # test idempotence
        mc.admin.group.enable(self.host, group)

        mc.admin.group.remove(self.host, group, members[0])
        assert mc.admin.group.info(self.host, group)['members'] == members[1:]
        # test idempotence
        mc.admin.group.remove(self.host, group, members[0])

        with pytest.raises(RuntimeError, match=r"The specified group is not empty"):
            mc.admin.group.remove(self.host, group)

        mc.admin.group.remove(self.host, group, *members)
        #mc.admin.group.remove(self.host, group)

        #assert len(mc.admin.group.list(self.host)) == 0

    def test_policy(self, mc):
        # by default, we have readonly, readwrite and writeonly policies pre-defined
        assert set(mc.admin.policy.list(self.host)) == {
            'readonly', 'writeonly', 'readwrite'}

        with pytest.raises(RuntimeError, match=r"'any_policy' was not found"):
            mc.admin.policy.info(self.host, 'any_policy')

        with pytest.raises(RuntimeError, match=r"<ERROR> Cannot remove policy. The canned policy does not exist."):
            mc.admin.policy.remove(self.host, 'any_policy')

        policy_name = 'my_policy'
        policy_definition = {
            "Version": "2012-10-17",
            "ID": "MyPolicy",
            "Statement": [
                {
                    "Sid": "ExampleStatement01",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::Account-ID:user/Dave"
                    },
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket",
                        "s3:GetBucketLocation"
                    ],
                    "Resource": [
                        "arn:aws:s3:::examplebucket/*",
                        "arn:aws:s3:::examplebucket"
                    ]
                }
            ]
        }
        mc.admin.policy.add(self.host, policy_name, policy_definition)
        assert len(mc.admin.policy.list(self.host)) == 4
        assert policy_name in mc.admin.policy.list(self.host)
        policy_json = mc.admin.policy.info(
            self.host, policy_name)['policyJSON']

        policy = mc.admin.policy.info(self.host, policy_name)
        assert policy['policy'] == policy_name

        # test idempotence
        mc.admin.policy.add(self.host, policy_name, policy_definition)
        assert len(mc.admin.policy.list(self.host)) == 4

        # test policy update
        policy_definition['Id'] = "MyUpdatedPolicy"
        mc.admin.policy.add(self.host, policy_name, policy_definition)
        assert len(mc.admin.policy.list(self.host)) == 4
        new_policy_json = mc.admin.policy.info(
            self.host, policy_name)['policyJSON']
        assert policy_json != new_policy_json

        mc.admin.policy.remove(self.host, policy_name)
        assert len(mc.admin.policy.list(self.host)) == 3
        assert policy_name not in mc.admin.policy.list(self.host)
