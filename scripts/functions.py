#!/usr/bin/env python3
"""
Conversion of basic fuctions used in the CI from bash to Python.
"""

import os
import re
import sys
import subprocess
import yaml
import check_pre_exist


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
    Given a docker repo owner, image name, and version, produce an
    appropriate local docker command
    """
    # Ensure the command is lower-case
    command = command.lower()
    # Generate local build command
    if (command == "build"):
        cmd = "docker build -q -f \"{}/{}/Dockerfile\" -t \"{}/{}:{}\" \"{}/{}/\"".format(
            tool, version, owner, tool, version, tool, version)
        return cmd
    # Generate a command to return the image ID
    elif (command == "images"):
        cmd = "docker images {}/{}:{} -q".format(owner, tool, version)
        return cmd
    # Generate pull command
    elif (command == "pull"):
        cmd = "docker pull {}/{}:{}".format(owner, tool, version)
        return cmd
    # Generate push command
    elif (command == "push"):
        cmd = "docker push {}/{}:{}".format(owner, tool, version)
        return cmd
    # Generate tag command
    elif (command == "tag"):
        cmd = "docker tag {}/{}:{} {}/{}:{}".format(
            owner, tool, version, owner, tool, source)
        return cmd
    # If command not recognized, error out
    else:
        print("Error, command \"{}\" not recognized, please verify it is one of the following: build, images, pull, push, tag\n.".format(command))
        exit(1)


def ensure_local_image(owner, tool, version):
    """
    Given a docker repo owner, image name, and version, check if it exists
    locally and pull if necessary
    """
    if (os.system(build_docker_cmd("images", owner, tool, version)) == ''):
        print("Image {}/{}:{} does not exist locally for tagging, pulling...\n".format(owner, tool, version))
        os.system(build_docker_cmd("build", owner, tool, version))


def build_images(owner, changed_paths):
    """
    Given
    1. a Docker repo owner (e.g. "medforomics") and
    2. a list of relative changed_paths to Dockerfiles
    (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile",
    issue a docker build command and tag any versions with a latest symlink
    """
    print("Building changed Dockerfiles...\n")
    attempted_build = 0
    # Check for Dockerfile changes first
    for changed_path in changed_paths:
        if changed_path.count('/') == 2:
            tool, version, filename = changed_path.split('/')
            if (filename.lower() == "dockerfile" and version != "latest"):
                attempted_build = 1
                print("Building {}/{}:{}...".format(owner, tool, version))
                build_command = build_docker_cmd(
                    "build", owner, tool, version).replace('\"', '').split(" ")
                term = subprocess.Popen(build_command)
                term_code = term.wait()
                if term_code == 0:
                    print("Successfully built {}/{}:{}...".format(owner, tool, version))
                else:
                    print("ERROR: Unable to build image!\n{}".format(
                        term.communicate()[2]))
                    exit(1)
                # Check if there is a symlink in the latest directory pointing to the newly-built version
                check_latest_path(owner, tool, version)
    if (attempted_build == ""):
        print("No changes to Dockerfiles or latest symlinks detected, nothing to build.\n")


def check_latest_path(owner, tool, version):
    """
    Checks to see if there is a 'latest' directory that points to the currently selected tool and version.
    """
    if os.path.exists(os.path.abspath("{}/latest".format(tool))):
        print("Path to current 'latest' version found, verifying which version it points to...")
        # If the currently selected image is already the latest
        if os.path.realpath("{}/latest".format(tool)) == os.path.abspath("{}/{}".format(tool, version)):
            print("Current version already linked as latest version.")
        # If the new image is replacing the current image
        else:
            print("Latest tag found, but is not pointing to the current version, setting new link and tagging {} as 'latest'".format(
                version))
            os.remove("{}/latest".format(tool))
            os.symlink("../{}/{}".format(tool, version),
                       "{}/latest".format(tool))
            tag_command = (build_docker_cmd("tag", owner, tool,
                                            version, "latest")).replace('\"', '').split(" ")
            subprocess.Popen(tag_command)
    # If no image has been tagged as 'latest'
    else:
        print("No currently set 'latest' image, creating link and tagging as 'latest'.")
        source_dir = "../{}/{}".format(tool, version)
        dest_dir = "{}/latest".format(tool)
        os.symlink(source_dir, os.path.relpath(dest_dir))
        tag_command = (build_docker_cmd("tag", owner, tool,
                                        version, "latest")).replace('\"', '').split(" ")
        subprocess.Popen(tag_command)


def push_images(owner, changed_paths):
    """
    Given
    1. a Docker repo owner (e.g. "medforomics") and
    2. a list of relative path to Dockerfiles (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile",
    issue a docker push command for the images built by build_images
    """
    for changed_path in changed_paths:
        if changed_path.count('/') == 2:
            tool, version, filename = changed_path.split('/')
            if (filename.lower() == "dockerfile"):
                attempted_push = "1"
                print("Pushing {}/{}:{}...".format(owner, tool, version))
                push_command = build_docker_cmd("push", owner, tool, version).replace(
                    '\"', '').split(" ")
                subprocess.Popen(push_command)
                # Check if there's a symlink {}/latest pointing to THIS version
                if version != 'latest':
                    check_latest_path(owner, tool, version)
                push_command = subprocess.Popen(push_command)
                push_code = push_command.wait()
                if push_code == 0:
                    print(
                        "Successfully pushed new branch based on {}/{}:{}".format(owner, tool, version))
                else:
                    print("ERROR: Image for {}/{}:{} was unable to be pushed, please try again after verifying you have access to {}/{}:{} on DockerHub!".format(
                        owner, tool, version, owner, tool, version))
                    exit(1)
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
