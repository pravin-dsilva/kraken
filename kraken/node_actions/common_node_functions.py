import time
import random
import logging
import paramiko
import kraken.kubernetes.client as kubecli
import kraken.invoke.command as runcommand


# Pick a random node with specified label selector
def get_node(node_name, label_selector):
    if node_name in kubecli.list_killable_nodes():
        return node_name
    else:
        logging.info("Node with provided node_name does not exist or the node might "
                     "be in NotReady state.")
    nodes = kubecli.list_killable_nodes(label_selector)
    if not nodes:
        raise Exception("Ready nodes with the provided label selector do not exist")
    logging.info("Ready nodes with the label selector %s: %s" % (label_selector, nodes))
    number_of_nodes = len(nodes)
    node = nodes[random.randint(0, number_of_nodes - 1)]
    return node


# Wait till node status becomes Ready
def wait_for_ready_status(node, timeout):
    runcommand.invoke("kubectl wait --for=condition=Ready "
                      "node/" + node + " --timeout=" + str(timeout) + "s")


# Wait till node status becomes NotReady
def wait_for_unknown_status(node, timeout):
    for _ in range(timeout):
        if kubecli.get_node_status(node) == "Unknown":
            break
        time.sleep(1)
    if kubecli.get_node_status(node) != "Unknown":
        raise Exception("Node condition status isn't Unknown")
     
def get_cluster_name():
    return runcommand.invoke("kubectl config view -o jsonpath='{.contexts[].context.cluster}'")
    
def check_service_status(node, service, timeout):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    i = 0
    sleeper = 1
    while i <= timeout:
        try:
            time.sleep(sleeper)
            i += sleeper            
            logging.info("Trying to ssh to instance: %s" % (node))
            conn = ssh.connect(node, username='root', key_filename='/root/.ssh/id_rsa', timeout=800, banner_timeout=400)
            if conn is None:
                break
        except:
            pass
    logging.info("Checking status of Service: %s" % (service))
    stdin, stdout, stderr = ssh.exec_command("systemctl status %s  | grep '^   Active' |  awk '{print $2}'" % (service))
    service_status =  stdout.readlines()[0]
    logging.info("Status of service %s is %s \n" % (service, service_status.strip()))
    ssh.close()
