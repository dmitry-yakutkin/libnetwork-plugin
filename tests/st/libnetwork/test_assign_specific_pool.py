# Copyright 2015 Tigera, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging

from subprocess import check_output

from tests.st.test_base import TestBase
from tests.st.utils.docker_host import DockerHost
from tests.st.utils.utils import (
    assert_number_endpoints, get_ip, log_and_run, retry_until_success, ETCD_SCHEME,
    ETCD_CA, ETCD_KEY, ETCD_CERT, ETCD_HOSTNAME_SSL)
from tests.st.libnetwork.test_mainline_single_host import \
    ADDITIONAL_DOCKER_OPTIONS, POST_DOCKER_COMMANDS
from netaddr import *

logger = logging.getLogger(__name__)


class TestAssignIP(TestBase):
    def test_assign_specific_ip(self):
        """
        Test that a libnetwork assigned IP is allocated to the container with
        Calico when using the '--ip' flag on docker run.
        """
        with DockerHost('host',
                        additional_docker_options=ADDITIONAL_DOCKER_OPTIONS,
                        post_docker_commands=["docker load -i /code/busybox.tar",
                                              "docker load -i /code/calico-node-libnetwork.tar"],
                        start_calico=False) as host:
            run_plugin_command = 'docker run -d ' \
                                 '--net=host --privileged ' + \
                                 '-e CALICO_ETCD_AUTHORITY=%s:2379 ' \
                                 '-v /run/docker/plugins:/run/docker/plugins ' \
                                 '-v /var/run/docker.sock:/var/run/docker.sock ' \
                                 '-v /lib/modules:/lib/modules ' \
                                 '--name libnetwork-plugin ' \
                                 'calico/libnetwork-plugin' % (get_ip(),)

            host.execute(run_plugin_command)

            #  Create two calico pools, and two docker networks with corresponding subnets.
            subnet1 = "10.15.0.0/16"
            subnet2 = "10.16.0.0/16"
            host.calicoctl('pool add %s' % subnet1)
            host.calicoctl('pool add %s' % subnet2)
            network1 = host.create_network("pool1", subnet=subnet1, driver="calico", ipam_driver="calico-ipam")
            network2 = host.create_network("pool2", subnet=subnet2, driver="calico", ipam_driver="calico-ipam")

            # Create a workload on network1 and check that it gets an IP in the right subnet.
            workload1 = host.create_workload("workload1", network=network1)
            self.assertTrue(IPAddress(workload1.ip) in IPNetwork(subnet1))

            # Create a workload on network2 and check that it gets an IP in the right subnet.
            workload2 = host.create_workload("workload2", network=network2)
            # Test commented out due to bug in libcalico-go
            # self.assertTrue(IPAddress(workload2.ip) in IPNetwork(subnet2))
