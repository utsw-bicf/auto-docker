#!/usr/bin/env python3
"""
Receives a Dockerfile, and adds relevant information to the relations.yaml file including:
    1) The parent image
    2) The child image string for the parent image
    3) Any information found about images downstream to this image
"""

import os
import sys
import re
import yaml

RELATION_FILENAME = "relations.yaml"


def write_yaml():
    """
    Overwrites the existing relations.yaml file with the new information provided, should only\
        be called once per run
    """
    yaml_file = open(RELATION_FILENAME, "w")
    yaml.safe_dump(NEWDATA, yaml_file)
    yaml_file.close()


def update_ancestor(parent, docker_image):
    """
    Updates any ancestor entries tied with this image to include them in their child tables
    :param parent: The parent image specified for updating
    :param docker_image: The docker image specified for updating in 'image_name:image_version' format
    """
    parent_name = parent.split(':')[0]
    parent_version = parent.split(':')[1]
    grandparent = []
    new_children = []
    if parent in ORIDATA['images']:
        new_children = ORIDATA['images'][parent_name][parent_version]['children']
        if (new_children == 'none') or (new_children == [None]) or (new_children == []):
            new_children = [docker_image]
        elif not docker_image in ORIDATA['images'][parent_name][parent_version]['children']:
            new_children += [docker_image]
        grandparent = ORIDATA['images'][parent_name][parent_version]['parents']
    else:
        new_children = [docker_image]
    build_entry(parent_name, parent_version, grandparent, new_children)


def build_entry(image_name, image_version, parent_images, child_images):
    """
    Builds a new yaml entry from the parent and child information
    :param image_name: The name of the image to be updated/created
    :param image_version: The version of above to be updated
    :param parents: The parent information for the enty
    :param children: The children information for the entry
    """
    if image_name in ORIDATA['images']:
        if image_version in ORIDATA['images'][image_name]:
            for parent in ORIDATA['images'][image_name][image_version]['parents']:
                if not parent in parent_images:
                    parent_images += [parent]
            for child in ORIDATA['images'][image_name][image_version]['children']:
                if not child in child_images:
                    child_images += [child]
            if (len(child_images) > 1) and (None in child_images):
                child_images.remove(None)
            new_image = {
                'parents': parent_images,
                'children': child_images
            }
            NEWDATA['images'][image_name][image_version].update(new_image)
        else:
            new_image = {
                image_version: {
                    'parents': parent_images,
                    'children': child_images
                }
            }
            new_latest = {
                image_name: image_version
            }
            NEWDATA['images'][image_name].update(new_image)
            NEWDATA['latest'].update(new_latest)
    else:
        new_image = {
            image_name: {
                image_version: {
                    'parents': parent_images,
                    'children': child_images
                }
            }
        }
        NEWDATA['images'].update(new_image)
    new_latest = {
        image_name: image_version
    }
    NEWDATA['latest'].update(new_latest)
    return new_image


def get_children(image_version, image_name):
    """
    Finds any children image in the relations.yaml file
    """
    if image_name in ORIDATA['images']:
        if image_version in ORIDATA['images'][image_name]:
            return ORIDATA['images'][image_name][image_version]['children']
        else:
            return [None]
    else:
        return [None]


def get_parents():
    """
    Gets the parent information from the Dockerfile
    """
    parents = []
    with open(DOCKERFILE_PATH, "r") as dockerfile:
        for line in dockerfile:
            if 'FROM ' in line:
                parents += [line.split()[1].split('/')[-1]]
    return parents


def load_yaml():
    """
    Loads a yaml file and returns a python yaml object
    """
    with open(RELATION_FILENAME) as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)
    yaml_file.close()
    return yaml_data


def main():
    """
    Main method
    """
    global ORIDATA
    global NEWDATA
    global DOCKERFILE_PATH
    if len(sys.argv) < 1:
        print("Usage python3 scripts/relational.py <DOCKERFILE_PATH>")
        sys.exit(1)
    else:
        # Setup the global variables
        DOCKERFILE_PATH = os.path.abspath(sys.argv[1])
        image_name = re.split('/', DOCKERFILE_PATH)[-3]
        image_version = re.split('/', DOCKERFILE_PATH)[-2]
        docker_image = image_name + ':' + image_version
        ORIDATA = load_yaml()
        NEWDATA = load_yaml()
        parents = get_parents()
        children = get_children(image_version, image_name)
    # Start by adding the image to the table
        build_entry(image_name, image_version, parents, children)
    # Update all parent images
    for parent in parents:
        update_ancestor(parent, docker_image)
    # Write out the new relations.yaml
    write_yaml()


if __name__ == "__main__":
    main()
