#!/usr/bin/env python3
"""
Conversion of basic fuctions used in the CI from bash to Python.
"""

import os
import re
import sys
import subprocess
import yaml


def get_deploy_branch():
    if 'DEPLOY_BRANCH' in os.environ:
        print("Deploy branch set to {}...".format(
            os.environ.get('DEPLOY_BRANCH')))
    else:
        print("Error: DEPLOY_BRANCH is empty\nPlease ensure DEPLOY_BRANCH is set to the name of the default branch used for deployment (i.e. 'develop').\n")
        exit(1)
    return os.environ.get('DEPLOY_BRANCH')


def get_current_branch_name():
    return os.system("echo ${GITHUB_REF##*/}")


def fetch_develop():
    """
    Keep track of which branch we are on.
    We are on a detached head, and we need to be able to go back to it.
    """
    build_head = os.system("git rev-parse HEAD")
    current_branch = get_current_branch_name
    deploy_branch = get_deploy_branch
    if (current_branch != deploy_branch):
        # If branch is not deploy branch (e.g. develop)
        # fetch the current develop branch
        os.system(
            "git config --replace-all remote.origin.fetch +refs/heads/*:refs/remotes/origin/*;")
        os.system("git fetch origin $DEPLOY_BRANCH")
        # create the tracking branch
        os.system("git checkout -qf $DEPLOY_BRANCH")
        # finally, go back to where we were at the beginning
        os.system("git checkout " + build_head)


def get_compare_range():
    """
    If the current branch is the deploy branch, return a range representing the two parents of the HEAD's merge commit. If not, return a range
    comparing the current HEAD with the deploy_branch
    """
    current_branch = get_current_branch_name
    deploy_branch = get_deploy_branch
    if (current_branch == deploy_branch):
        # On the deploy branch (e.g. develop)
        range_start = "HEAD^1"  # alias for first parent
        range_end = "HEAD^2"   # alias for second parent
    else:
        # Not on the deploy branch (e.g. develop)
        # When not on the deploy branch, always compare with the deploy branch
        range_start = "origin/" + get_deploy_branch()
        range_end = "HEAD"
    return (range_start + " " + range_end)


def changed_paths_in_range(compare_range):
    cmd = "git diff --name-only --diff-filter=d {}".format(
        compare_range).split()
    paths_run = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, universal_newlines=True)
    return paths_run.communicate()[0].split("\n")[:-1]


def build_docker_cmd(command, owner, tool, version, source="NA"):
    """
    Given a docker repo owner, image name, and version, produce an appropriate local docker command
    """
    # Ensure the command is lower-case
    command = command.lower()
    # Generate local build command
    if (command == "build"):
        return "docker build -f \"{}/{}/Dockerfile\" -t \"{}/{}:{}\" \"{}/{}/\"".format(
            tool, version, owner, tool, version, tool, version)
    # Generate a command to return the image ID
    elif (command == "images"):
        return "docker images {}/{}:{} -q".format(owner, tool, version)
    # Generate pull command
    elif (command == "pull"):
        return "docker pull {}/{}:{}".format(owner, tool, version)
    # Generate push command
    elif (command == "push"):
        return "docker push {}/{}:{}".format(owner, tool, version)
    # Generate tag command
    elif (command == "tag"):
        return "docker tag {}/{}:{} {}/{}:{}".format(
            owner, tool, source, owner, tool, version)
    # If command not recognized, error out
    else:
        print("Error, command \"{}\" not recognized, please verify it is one of the following: build, images, pull, push, tag\n.".format(command))
        exit(1)


def ensure_local_image(owner, tool, version):
    """
    Given a docker repo owner, image name, and version, check if it exists locally and pull if necessary
    """
    if (os.system(build_docker_cmd("images", owner, tool, version)) == ''):
        print("Image {}/{}:{} does not exist locally for tagging, pulling...\n".format(owner, tool, version))
        os.system(build_docker_cmd("build", owner, tool, version))


def build_images(owner, changed_paths):
    """
    Given
    1. a Docker repo owner (e.g. "medforomics") and
    2. a list of relative changed_paths to Dockerfiles (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile", issue a docker build command and tag any versions with a latest symlink
    """
    print("Building changed Dockerfiles...\n")
    # Check for Dockerfile changes first
    for changed_path in changed_paths:
        print(changed_path)
        tool = changed_path.split("/")[0]
        print(tool)
        version = changed_path.split("/")[1]
        print(version)
        filename = changed_path.split("/")[2]
        if (filename.lower() == "dockerfile" and version != "latest"):
            attempted_build = 1
            print("Building {}/{}:{}...".format(owner, tool, version))
            os.system(build_docker_cmd("build", owner, tool, version))
        # Check if there is a symlink in the latest directory pointing to this version
        if (os.path.abspath(tool + "/latest/Dockerfile") == os.path.abspath(os.readlink(changed_path))):
            print("Tagging {}/{}:{} as {}/{}:latest\n".format(owner,
                                                              tool, version, owner, tool))
            os.system(build_docker_cmd("tag", owner, tool, version, "latest"))
    # After building all Dockerfiles, check for any changes to latest
    print("Updating latest tags...\n")
    for changed_path in changed_paths:
        tool = changed_path.split('/')[0]
        version = changed_path.split('/')[1]
        filename = changed_path.split('/')[2]
        if (os.path.islink(changed_path) and filename.lower() == "" and version == "latest"):
            # The changed file is a symlink called latest, e.g. "fastqc/latest"
            # Determine the version it's pointing to
            dest_version = os.path.abspath(
                os.readlink(changed_path)).split('/')[-1]
            # In order to tag to version, it must exist locally. If it wasn't built in previous loop, need to pull it
            ensure_local_image(owner, tool, dest_version)
            print("Tagging {}/{}:{} as {}/{}:latest...\n".format(owner,
                                                                 tool, dest_version, owner, tool))
            os.system(build_docker_cmd("tag", owner, tool, version, "latest"))
    if (attempted_build == ""):
        print("No changes to Dockerfiles or latest symlinks detected, nothing to build.\n")


def push_images(owner, changed_paths):
    """
    Given
    1. a Docker repo owner (e.g. "medforomics") and
    2. a list of relative path to Dockerfiles (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile",
    issue a docker push command for the images built by build_images
    """
    for changed_path in changed_paths:
        tool = changed_path.split('/')[0]
        version = changed_path.split('/')[1]
        filename = changed_path.split('/')[2]
        if (filename.lower() == "dockerfile" and version != "latest"):
            attempted_push = "1"
            print("Pushing {}/{}:{}...".format(owner, tool, version))
            os.system(build_docker_cmd("build", owner, tool, version))
            # Check if there's a symlink {}/latest pointing to THIS version
            if (os.readlink(tool + "/latest/Dockerfile") == os.readlink(tool + "/" + version + "/Dockerfile")):
                print("Pushing {}/{}:latest...".format(owner, tool))
                os.system(build_docker_cmd("push", owner, tool, "latest"))
    # After pushing all Dockerfiles, check for any changes to latest and push those
    print("Pushing latest tags...\n")
    for changed_path in changed_paths:
        tool = changed_path.split('/')[0]
        version = changed_path.split('/')[1]
        filename = changed_path.split('/')[2]
        if (os.path.islink(changed_path) and filename.lower() == "" and version == "latest"):
            attempted_push = "1"
            # The changed file is a symlink called latest, e.g. "fastqc/latest"
            # Determine the version it's pointing to
            print("Pushing {}/{}:latest...".format(owner, tool))
            os.system(build_docker_cmd("build", owner, tool, "latest"))
    if (attempted_push == ""):
        print("No changes to Dockerfiles or latest symlinks detected, nothing to push")


def print_changed(range, changed_paths):
    print("Changed files between {}:".format(range))
    for changed_path in changed_paths:
        print(changed_path)


def check_org():
    if 'DOCKERHUB_ORG' in os.environ:
        print("Using Docker Hub org as {}...".format(
            os.environ.get('DOCKERHUB_ORG')))
    else:
        print("Error: DOCKERHUB_ORG is empty\nPlease ensure DOCKERHUB_ORG is set to the name of the Docker Hub organization.\n")
        exit(1)
    return os.environ.get('DOCKERHUB_ORG')
