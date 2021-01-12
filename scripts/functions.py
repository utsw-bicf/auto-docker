#!/usr/bin/env python3
"""
Conversion of basic fuctions used in the CI from bash to Python.
"""

import os
import sys
import re
import yaml


def get_deploy_branch():
    deploy_branch = os.environ['DEPLOY_BRANCH']


def get_current_branch_name():
    print(os.system("echo ${GITHUB_REF##*/}"))


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
        range_start = "origin/$DEPLOY_BRANCH"
        range_end = "HEAD"
    print(range_start + " " + range_end)


def build_docker_cmd(command, owner, source, tag, tool, version):
    """
    Given a docker repo owner, image name, and version, produce an appropriate local docker command
    """
    #Ensure the command is lower-case
    command = command.lower()
    # Generate local build command
    if (command == "build"):
        docker_cmd = "docker build -f \"{}/{}/Dockerfile\" -t \"{}/{}:{}\" \"{}/{}".format(tool, version, owner, tool, version, tool, version)
    #Generate a command to return the image ID
    elif (command == "images"):
        docker_cmd = "docker images {}/{}:{} -q".format(owner, tool, tag)
    #Generate pull command
    elif (command == "pull"):
        docker_cmd = "docker pull {}/{}:{}".format(owner, tool, version)
    #Generate push command
    elif (command == "push"):
        docker_cmd = "docker push {}/{}:{}".format(owner, tool, version)
    #Generate tag command
    elif (command == "tag"):
        docker_cmd = "docker tag {}/{}:{} {}/{}:{}".format(owner, tool, source, owner, tool, tag)
    #If command not recognized, error out
    else:
        print("Error, command \"{}\" not recognized, please verify it is one of the following: build, images, pull, push, tag\n.".format(command))
        exit(1)
    print(docker_cmd)