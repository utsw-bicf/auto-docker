#!/bin/bash

function current_branch_name() {
  echo ${GITHUB_REF##*/}
}

function fetch_develop() {
  # Keep track of which branch we are on.
  # We are on a detached head, and we need to be able to go back to it.
  local build_head=$(git rev-parse HEAD)

  current_branch=$(current_branch_name)
  if [[ "$current_branch" != "$DEPLOY_BRANCH" ]]; then
    # If branch is not deploy branch (e.g. develop)
    # fetch the current develop branch
    # Travis clones with `--depth`, which
    # implies `--single-branch`, so we need to overwrite remote.origin.fetch to
    # do that.
    git config --replace-all remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
    git fetch origin $DEPLOY_BRANCH

    # create the tracking branch
    git checkout -qf $DEPLOY_BRANCH

    # finally, go back to where we were at the beginning
    git checkout ${build_head}
  fi
}

# Given a range, produce the list of file paths changed
function changed_paths_in_range() {
  compare_range=$1
  # dio${GITHUB_REF}f-filter=d excludes deleted files
  git diff --name-only --diff-filter=d $compare_range
}

function fetch_master() {
  #Fetches the master branch
  #Very similar to fetch develop, but specifically points to master
  local build_head=$(git rev-parse HEAD)

  current_branch=$(current_branch_name)
  if [[ "${current_branch}" != "origin/master" ]]; then
    # If the current branch is not master
    # fetch the master branch
    git config --replace-all remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
    git fetch origin master

    # create the tracking branch
    git checkout -qf master

    # finally, go beack to where we were at the beginning
    git checkout ${build_head}
  fi
}

# If the current branch is the deploy branch, return a range representing
# the two parents of the HEAD's merge commit. If not, return a range comparing
# the current HEAD with the deploy_branch
function get_compare_range() {
  current_branch=$(current_branch_name)
  if [[ "$current_branch" == "$DEPLOY_BRANCH" ]]; then
    # On the deploy branch (e.g. develop)
    # Travis should check if this is a merge or not
    range_start="HEAD^1" # alias for first parent
    range_end="HEAD^2"   # alias for second parent
  else
    # Not on the deploy branch (e.g. develop)
    # When not on the deploy branch, always compare with the deploy branch
    # Travis resets develop to the tested commit, so we have to use origin/develop
    range_start="origin/$DEPLOY_BRANCH"
    range_end="HEAD"
  fi
  echo "$range_start $range_end"
}

# Given a docker repo owner, image name, and version, produce a local docker build command
function build_docker_cmd() {
  owner=$1
  tool=$2
  version=$3
  echo "docker build -f $tool/$version/Dockerfile" -t "$owner/$tool:$version" "$tool/$version"
}

# Given a docker repo owner, image name, and version, produce a docker push command
function push_docker_cmd() {
  owner=$1
  tool=$2
  version=$3
  echo "docker push $owner/$tool:$version"
}

# Given a docker repo owner, image name, and version, produce a docker pull command
function pull_docker_cmd() {
  owner=$1
  tool=$2
  version=$3
  echo "docker pull $owner/$tool:$version"
}

# Given a docker repo owner, image name, source and dest tags produce a docker tag command
function tag_docker_cmd() {
  owner=$1
  tool=$2
  src=$3
  tag=$4
  echo "docker tag $owner/$tool:$src $owner/$tool:$tag"
}

# Given a docker repo owner, image name, and version, produce a command that returns the image id if it exists locally
function docker_image_id_cmd() {
  owner=$1
  tool=$2
  tag=$3
  echo "docker images $owner/$tool:$tag -q"
}

# Given a docker repo owner, image name, and version, check if it exists locally and pull if necessary
function ensure_local_image() {
  owner=$1
  tool=$2
  version=$3
  local_image_id=$($(docker_image_id_cmd $owner $tool $version))
  if [[ "$local_image_id" == "" ]]; then
    echo "Image $owner/$tool:$version does not exist locally for tagging, pulling..."
    $(pull_docker_cmd $owner $tool $version)
  fi
}

# Given
# 1. a Docker repo owner (e.g. "medforomics") and
# 2. a list of relative paths to Dockerfiles (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile",
# issue a docker build command and tag any versions with a latest symlink
function build_images() {
  echo "Building changed Dockerfiles..."
  echo
  owner="$1"
  changed_paths="$2"
  # Check for Dockerfile changes first
  for changed_path in $changed_paths; do
    IFS='/' read -r -a f <<<"$changed_path"
    tool="${f[0]}"
    version="${f[1]}"
    filename="${f[2]}"
    if [[ "$filename" == "Dockerfile" && "$version" != "latest" ]]; then
      attempted_build="1"
      echo "Building $owner/$tool:$version..."
      $(build_docker_cmd $owner $tool $version)
      # Check if there's a symlink $tool/latest pointing to THIS version
      if [[ "$tool/latest/Dockerfile" -ef "$tool/$version/Dockerfile" ]]; then
        echo "Tagging $owner/$tool:$version as $owner/$tool:latest"
        $(tag_docker_cmd $owner $tool $version "latest")
      fi
    fi
  done

  # After building all Dockerfiles, check for any changes to latest
  echo "Updating latest tags..."
  echo
  for changed_path in $changed_paths; do
    IFS='/' read -r -a f <<<"$changed_path"
    tool="${f[0]}"
    version="${f[1]}"
    filename="${f[2]}"
    if [[ -L "$changed_path" && "$filename" == "" && "$version" == "latest" ]]; then
      attempted_build="1"
      # The changed file is a symlink called latest, e.g. "fastqc/latest"
      # Determine the version it's pointing to
      dest_version=$(readlink $changed_path)
      # In order to tag to version, it must exist locally. If it wasn't built in previous loop,
      # need to pull it
      ensure_local_image $owner $tool $dest_version
      echo "Tagging $owner/$tool:$dest_version as $owner/$tool:latest"
      $(tag_docker_cmd $owner $tool $dest_version "latest")
    fi
  done

  if [[ "$attempted_build" == "" ]]; then
    echo "No changes to Dockerfiles or latest symlinks detected, nothing to build"
  fi
}

# Given
# 1. a Docker repo owner (e.g. "medforomics") and
# 2. a list of relative paths to Dockerfiles (e.g. "fastqc/0.11.4/Dockerfile bwa/0.7.12/Dockerfile",
# issue a docker push command for the images built by build_images
function push_images() {
  owner="$1"
  changed_paths="$2"
  for changed_path in $changed_paths; do
    IFS='/' read -r -a f <<<"$changed_path"
    tool="${f[0]}"
    version="${f[1]}"
    filename="${f[2]}"
    if [[ "$filename" == "Dockerfile" && "$version" != "latest" ]]; then
      attempted_push="1"
      echo "Pushing $owner/$tool:$version..."
      push_docker_cmd $owner $tool $version
      # Check if there's a symlink $tool/latest pointing to THIS version
      if [[ "$tool/latest/Dockerfile" -ef "$tool/$version/Dockerfile" ]]; then
        echo "Pushing $owner/$tool:latest..."
        $(push_docker_cmd $owner $tool "latest")
      fi
    fi
  done

  # After pushing all Dockerfiles, check for any changes to latest and push those
  echo "Pushing latest tags..."
  echo
  for changed_path in $changed_paths; do
    IFS='/' read -r -a f <<<"$changed_path"
    tool="${f[0]}"
    version="${f[1]}"
    filename="${f[2]}"
    if [[ -L "$changed_path" && "$filename" == "" && "$version" == "latest" ]]; then
      attempted_push="1"
      # The changed file is a symlink called latest, e.g. "fastqc/latest"
      # Determine the version it's pointing to
      echo "Pushing $owner/$tool:latest..."
      $(push_docker_cmd $owner $tool "latest")
    fi
  done

  if [[ "$attempted_push" == "" ]]; then
    echo "No changes to Dockerfiles or latest symlinks detected, nothing to push"
  fi
}

function print_changed() {
  range="$1"
  paths="$2"
  echo "Changed files in ($range)"
  echo
  for changed_path in $paths; do
    echo "  $changed_path"
  done
  echo
}

function check_org() {
  if [[ "$DOCKERHUB_ORG" == "" ]]; then
    echo "Error: DOCKERHUB_ORG is empty"
    echo "Please ensure DOCKERHUB_ORG is set to the name of the Docker Hub organization"
    exit 1
  else
    echo "Using Docker Hub org as $DOCKERHUB_ORG..."
  fi
}
