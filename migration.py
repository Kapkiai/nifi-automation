import nipyapi
from collections import namedtuple
from nipyapi import versioning
import urllib3
import json
import time
import sys

nipyapi.config.default_profiles_file = './profiles.yml'

nipyapi.profiles.switch('dev-nifi')

# define the list of Process Groups
process_groups = ["default"]

if (len(sys.argv) > 1):
    pg = sys.argv[1]
    process_groups = pg.split(',')


print(process_groups)

# store exported flows
exported_flows = {}
ExportedFlow = namedtuple("ExportedFlow", ["name", "bucket_name", "definition"])

def sanitize_pg(pg_def):
    """
    sanitize the processGroup section from parameterContext references, does a
      recursive cleanup of the processGroups if multiple levels are found.
    """

    if "parameterContextName" in pg_def:
        pg_def.pop("parameterContextName")

    if "processGroups" not in pg_def or len(pg_def["processGroups"]) == 0:
        return pg_def

    for pg in pg_def["processGroups"]:
        sanitize_pg(pg)

for pgn in process_groups:
    # make sure there's a Process Group on the Canvas
    pg = nipyapi.canvas.get_process_group(pgn, greedy=False)

    if pg is None:
        print(F"process group {pgn} was not found in the Nifi Canvas")
        exit(1)

    # make sure the process group is in the Registry
    if pg.component.version_control_information is None:
        print(F"process group {pgn} is not added to version control")
        exit(1)

    # make sure there are no uncommitted changes on the Canvas
    diff = nipyapi.nifi.apis.process_groups_api.ProcessGroupsApi().get_local_modifications(pg.id)
    diffn = len(diff.component_differences)
    if diffn > 0:
        print(F"there are uncommitted changes in the process group {pgn}")
        exit(1)

    # since we are here, we found no issue with this Process Group
    # let's export it

    bucket_id = pg.component.version_control_information.bucket_id
    bucket_name = pg.component.version_control_information.bucket_name
    flow_id = pg.component.version_control_information.flow_id

    # export the latest version from the Registry
    flow_json = versioning.export_flow_version(bucket_id, flow_id, version=None)
    exported_flows[pgn] = ExportedFlow(pgn, bucket_name, flow_json)

# connect to Nifi
nipyapi.profiles.switch('uat-nifi')

for flow_name, exported_flow in exported_flows.items():
    flow_name = flow_name
    bucket = versioning.get_registry_bucket(exported_flow.bucket_name)
    print(bucket)
    if bucket is None:
        bucket = versioning.create_registry_bucket(exported_flow.bucket_name)
        pg = nipyapi.canvas.get_process_group(flow_name, greedy=False)
        if pg is not None:
            print(F"process group exists on Canvas, but not in Registry: {flow_name}")
            exit(1)

    else:
        bflow = versioning.get_flow_in_bucket(bucket.identifier, flow_name)
        pg = nipyapi.canvas.get_process_group(flow_name, greedy=False)
        if bflow is None and pg is not None:
            print(F"process group exists on Canvas, but not in Registry: {flow_name}")
            exit(1)

        if pg is not None:
            diff = nipyapi.nifi.apis.process_groups_api.ProcessGroupsApi().get_local_modifications(pg.id)
            diffn = len(diff.component_differences)
            if bflow is not None and pg is not None and diffn > 0:
                print(F"there are uncommitted changes in the process group {pgn}")
                exit(1)

# get the registry client for the test environment, we need this to import
# process groups
reg_clients = versioning.list_registry_clients()
test_reg_client = None

# just getting the first registry client we find, assuming we only have one
for reg_client in reg_clients.registries:
    test_reg_client = reg_client.component
    break

# read the Canvas root element ID to attach Process Groups
root_pg = nipyapi.canvas.get_root_pg_id()

for flow_name, exported_flow in exported_flows.items():
    # flow_name = flow_name + '_PROD'
    flow = json.loads(exported_flow.definition)

    # get the bucket details
    bucket = versioning.get_registry_bucket(exported_flow.bucket_name)

    # remove from top level Process Group
    if "parameterContexts" in flow:
        param_ctx = flow["parameterContexts"]
        flow["parameterContexts"] = {}
        if "parameterContextName" in flow["flowContents"]:
            flow["flowContents"].pop("parameterContextName")

    # additionally, sanitize inner Process Groups
    for pg in flow["flowContents"]["processGroups"]:
        sanitize_pg(pg)

    sanitized_flow_def = json.dumps(flow)

    # check if the process group exists in the bucket
    existing_flow = versioning.get_flow_in_bucket(bucket.identifier, flow_name)
    if existing_flow is None:
        # import anew into the Registry
        vflow = versioning.import_flow_version(
                              bucket.identifier,
                              encoded_flow=sanitized_flow_def,
                              flow_name=flow_name)
        time.sleep(5)

        # deploy anew into the Canvas
        versioning.deploy_flow_version(
              parent_id=root_pg,
              location=(0, 0),
              bucket_id=bucket.identifier,
              flow_id=vflow.flow.identifier,
              reg_client_id=test_reg_client.id,
              )
    else:
        # update Flow in Registry in place
        vflow = versioning.import_flow_version(
                bucket_id=bucket.identifier,
                encoded_flow=sanitized_flow_def,
                flow_id=existing_flow.identifier)
        time.sleep(5)

        # check if the Canvas already has the Process Group
        pg = nipyapi.canvas.get_process_group(flow_name, greedy=False)
        if pg is None:
            # deploy anew into the Canvas
            versioning.deploy_flow_version(
                    parent_id=root_pg,
                    location=(0, 0),
                    bucket_id=bucket.identifier,
                    flow_id=vflow.flow.identifier,
                    reg_client_id=test_reg_client.id,
                    )
        else:
            # update Canvas in place
            versioning.update_flow_ver(process_group=pg)
