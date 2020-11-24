import sys
import time
import logging
import subprocess
import kraken.kubernetes.client as kubecli
import kraken.invoke.command as runcommand
import kraken.node_actions.common_node_functions as nodeaction
from kraken.node_actions.abstract_node_scenarios import abstract_node_scenarios


class IBMCLOUD:
    def __init__(self):
        self.Wait = 30
       
    # Start the node instance
    def start_instances(self, node):
        action_output = runcommand.invoke("ibmcloud pi instance-start %s" % (node))
        logging.info("IBMCLOUD CLI INFO: %s" % (action_output))
        return action_output
        
    # Stop the node instance
    def stop_instances(self, node):
        action_output = runcommand.invoke("ibmcloud pi instance-stop %s" % (node))
        logging.info("IBMCLOUD CLI INFO: %s" % (action_output))
        return action_output
        
    # Terminate the node instance
    def terminate_instances(self, node):
        action_output = runcommand.invoke("ibmcloud pi instance-stop %s" % (node))  
        logging.info("IBMCLOUD CLI INFO: %s" % (action_output))       
        return action_output
        
    # Reboot the node instance
    def reboot_instances(self, node):
        action_output = runcommand.invoke("ibmcloud pi instance-soft-reboot %s" % (node))
        logging.info("IBMCLOUD CLI INFO: %s" % (action_output))                
            
    # Wait until the node instance is running
    def wait_until_running(self, node):
        self.get_instance_status(node, "ACTIVE", self.Wait)
        
    # Wait until the node instance is stopped
    def wait_until_stopped(self, node):
        self.get_instance_status(node, "SHUTOFF", self.Wait)

    # Wait until the node instance is terminated
    def wait_until_terminated(self, node):
        self.get_instance_status(node, "SHUTOFF", self.Wait)
                
    # Get instance status
    def get_instance_status(self, node, expected_status, timeout):
        i = 0
        sleeper = 1
        while i <= timeout:
            instStatus = runcommand.invoke("ibmcloud pi instance %s  | grep ^Status | awk  '{print $2}'" % (node))
            logging.info("instance status is %s" % (instStatus))
            logging.info("expected status is %s" % (expected_status))
            if (instStatus.strip() == expected_status):
                logging.info("instance status has reached desired status %s" % (instStatus))
                return True
            time.sleep(sleeper)
            i += sleeper
            
    def get_instance_ip(self, node):
        action_output = runcommand.invoke("ibmcloud pi instance %s | grep 'External Address' | awk '{print $7}' | sed 's/.$//'" % (node))
        logging.info("IBMCLOUD CLI INFO: IP Address is %s" % (action_output))
        return action_output        
        
class ibmcloud_node_scenarios(abstract_node_scenarios):
    def __init__(self):
        self.ibmcloud = IBMCLOUD()

    # Node scenario to start the node
    def node_start_scenario(self, instance_kill_count, node, timeout):
        for _ in range(instance_kill_count):
            try:
                logging.info("Starting node_start_scenario injection")
                logging.info("Starting the node %s" % (node))
                node_with_prefix = nodeaction.get_cluster_name() + "-" + node
                self.ibmcloud.start_instances(node_with_prefix)
                self.ibmcloud.wait_until_running(node_with_prefix)
                if "bastion" not in node:
                    nodeaction.wait_for_ready_status(node, timeout)
                logging.info("Node with instance ID: %s is in running state" % (node))
                logging.info("node_start_scenario has been successfully injected!")
            except Exception as e:
                logging.error("Failed to start node instance. Encountered following "
                              "exception: %s. Test Failed" % (e))
                logging.error("node_start_scenario injection failed!")
                sys.exit(1)

    # Node scenario to stop the node
    def node_stop_scenario(self, instance_kill_count, node, timeout):
        for _ in range(instance_kill_count):
            try:
                logging.info("Starting node_stop_scenario injection")
                logging.info("Stopping the node %s " % (node))
                node_with_prefix = nodeaction.get_cluster_name() + "-" + node
                self.ibmcloud.stop_instances(node_with_prefix)
                self.ibmcloud.wait_until_stopped(node_with_prefix)
                logging.info("Node with instance name: %s is in stopped state" % (node_with_prefix))
                if "bastion" not in node:
                    nodeaction.wait_for_unknown_status(node, timeout)
            except Exception as e:
                logging.error("Failed to stop node instance. Encountered following exception: %s. "
                              "Test Failed" % (e))
                logging.error("node_stop_scenario injection failed!")
                sys.exit(1)

    # Node scenario to terminate the node
    def node_termination_scenario(self, instance_kill_count, node, timeout):
        for _ in range(instance_kill_count):
            try:
                logging.info("Starting node_termination_scenario injection")
                logging.info("Terminating the node %s" % (node))
                node_with_prefix = nodeaction.get_cluster_name() + "-" + node
                self.ibmcloud.terminate_instances(node_with_prefix)
                self.ibmcloud.wait_until_terminated(node_with_prefix)
                for _ in range(timeout):
                    if node not in kubecli.list_nodes():
                        break
                    time.sleep(1)
                if node in kubecli.list_nodes():
                    raise Exception("Node could not be terminated")
                logging.info("Node with instance name: %s has been terminated" % (node))
                logging.info("node_termination_scenario has been successfuly injected!")
            except Exception as e:
                logging.error("Failed to terminate node instance. Encountered following exception:"
                              " %s. Test Failed" % (e))
                logging.error("node_termination_scenario injection failed!")
                sys.exit(1)

    # Node scenario to reboot the node
    def node_reboot_scenario(self, instance_kill_count, node, timeout):
        for _ in range(instance_kill_count):
            try:
                logging.info("Starting node_reboot_scenario injection")
                logging.info("Rebooting the node %s" % (node))
                node_with_prefix = nodeaction.get_cluster_name() + "-" + node
                self.ibmcloud.reboot_instances(node_with_prefix)
                nodeaction.wait_for_unknown_status(node, timeout)
                nodeaction.wait_for_ready_status(node, timeout)
                logging.info("Node with instance name: %s has been rebooted" % (node))
                logging.info("node_reboot_scenario has been successfuly injected!")
            except Exception as e:
                logging.error("Failed to reboot node instance. Encountered following exception:"
                              " %s. Test Failed" % (e))
                logging.error("node_reboot_scenario injection failed!")
                sys.exit(1)

    def node_service_status(self, node, service, timeout):
        try:
            logging.info("Checking service status on the bastion nodes")
            node_with_prefix = nodeaction.get_cluster_name() + "-" + node
            ip = self.ibmcloud.get_instance_ip(node_with_prefix)
            for service_name in service:
                nodeaction.check_service_status(ip.strip(), service_name.strip(), timeout)
                logging.info("Service status checked on %s" % (node))
                logging.info("check service status is successfuly injected!")
        except Exception as e:
            logging.error("Failed to check service status. Encountered following exception:"
                          " %s. Test Failed" % (e))
            logging.error("stop_start_bastion_scenario injection failed!")
            sys.exit(1)
 
