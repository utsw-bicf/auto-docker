# auto-docker

Lightweight version of our automated Docker image builder

## Setup

1. Fork this repository from the master branch, and rename it to suite your needs
2. Setup the following secrets:

* **DEPLOY_BRANCH**: This should be set to something other than ***master*** or ***main***.  We use ***develop***

* **DOCKERHUB_ORG** The default Docker Hub organization name.  If you don't want to use the default Dockerhub, this is where you can change it to either Azure or AWS container registries, otherwise just use your dafult Dockerhub ID.  This is the first part of your *docker push* command, before the first slash:

``` sh
docker push ${DOCKERHUB_ORG}/${image_name}:${image_version}
```

 
We recommend having a user account that is now owned by any individual for pushing, so that you are not compromising personal credentials.

* **DOCKERHUB_PW**: Pretty self-explanitory, password to log in to your Dockerhub organization.

* **DOCKERHUB_UN**: Again, the username associated with the above organization and password.

3. Change the name of the base image to suite your needs.  So, since we are the bicf, we call ours *bicfbase*.  You will need to do this in the main directory, as well as in the *relations.yaml* file.

That should be it, you're all set.
  

## Using this suite

This suite is setup assuming that all of your images have the base image as their ultimate parent.  This image is built off the publically available Ubuntu 18.04 image, with some common tools such as *git*, *parallel*, *pbzip2* and others installed.  It is meant to be fairly light-weight.  Using the *relations.yaml* file, it is very easy to keep track of what images are built on top of other images.

Every new image is setup with the following:

1. A directory structure like that seen in base, where the first directory is the image name, and the second is a three-piece version number, such as *1.0.0*:
* *${image_name}/${image_version}/Files*

2. Inside the version sub-directory should be at least two files:

* **Dockerfile** which is the standard Docker build file
* **unittest.yml** which is a simple command/result unit test file for what you expect to be present in a functional version of your image.  An example file can be found in *base/1.0.0/unittest.yml*, but it should look like this:

``` yaml
commands:
  cmd: 'parallel --version | head -n1'
  expect_text: |
    GNU parallel 20161222
  cmd: 'pandoc --version'
  expect_text: |
    pandoc 1.19.2.4
    Compiled with pandoc-types 1.17.0.5, texmath 0.9.4.4, skylighting 0.3.3.1
    Default user data directory: /root/.pandoc
    Copyright (C) 2006-2016 John MacFarlane
    Web:  http://pandoc.org
    This is free software; see the source for copying conditions.
    There is no warranty, not even for merchantability or fitness
    for a particular purpose.
```

Any additional files required for installation may be placed here as well, such as any scripting files required by the image.  Be aware, these folders are available to anyone that you grant permissions to access this repository, so placing user names and passwords is not advised.

There should be three branches of this repository at any given time, we will call them ***main***, ***develop***, and ***issue***.

### Main

This is the branch that is the most locked down.  Any images listed in this branch should not be modified any further, and should not be rebuilt from the Dockerfile.  For our purposes, this is the branch for images that have been used in publications or publically available pipelines, and so cannot be modified any further.

### Develop

At this branch, images are available for public (or at least organizational) use, but can be modified or rebuilt from the Dockerfile should the need arise.

This is kind of like an extended beta test, and it is your last chance to make any changes or rebuild images before they are pushed to main and locked down.

### Issue

This branch is the most maliable, and it is also the only branch where there should exist more than one; specifically one per image created/in development.  Each issue can have only __***ONE***__ modified Dockerfile, so if you need to modify more than one Dockerfile, you must create two entries in this branch.

The thought process for this branch is that these images are still in testing by the creator, and so are not meant for anyone else's use.

### Creating a new image

1. When a user wants to create a new image, first they should create an issue requesting this new image.  What is in this issue is up to the manager of the fork, however, it is recommended that they list out the following:

* The programs and associated version numbers required for this image
* The URLs for any installation instructions and downloads
* Any time crunch considerations
* What programs would be tested for validation, and how they should be verified (we mostly use a simple version verification)

2. From there, it is up to those who are maintaining the repository to figure out which images should be used as a parent image, and create a new branch, tied to the issue.

3. On this branch, write the new Docker recipe along with any tests that are required to ensure functionality

4. Once the branch is pushed, the image will be built, and the tests specified will be run on it.

5. Assuming that the build is successfull and the test run without issue, the new image will be pushed to the container repository specified by the above secrets.

6. Within the issue branch, a new *relations.yaml* file is created, which takes the current *relations.yaml* from the *develop* branch, and updates it with the new Dockerfile information.  Once it is pushed to ***develop***.

7. Once the image is tested to the satisfaction of both the image creator and the curator of this repository, the ***issue*** can then be merged into ***develop*** and closed.  At a point of the curator's discression, all images in ***develop*** may be merged into ***main***.

### Updating a specific image

This process is funcitonally very similar to the creation of a new image, in that you still want to create an issue with the same information, however, this time, after the new image is pushed, it adds a new step which checks the *relation.yaml* file for any child images, and it automatically creates additional issues for updating these child images, to keep them current with any changes to the parents.

There is a section in the **relations.yaml** called "terminated".  This section is special, and should only be updated on the ***develop*** branch.  This section is reserved for images that are no longer to be updated whenever a parent image is updated (for example, if there are licensing issues, or logins that make an automated build impossible).

### Non-Dockerfile related changes

If the program detects that, after a push, no Dockerfiles have been altered or added, it instead runs the CI on all images that it has tagged as "latest".

### Merging upstream auto-docker changes

This section will describe how to incorporate changes to auto-docker that occurred since initializing your repository.
You will want to do this if there are new enhancements or bugfixes that you want to incorporate.
This process can be difficult, especially if conflicts have arisen, and is recommended only for advanced git users.

It is recommended to do auto-docker upgrades via a pull request to help you view the proposed changes and to ensure the build uses the updates.

1. Checkout a new branch to use as the pull request head branch:

``` sh
# This command names the branch using the current date, i.e. auto-docker-2020-11-06
git checkout -b auto-docker-$(date '+%Y-%m-%d')
```

2. Pull the new commits from auto-docker, but do not automerge:

``` sh
git pull --no-ff --no-commit auto-docker main
```

If all goes well, there won't be any conflicts.
However, if there are conflicts, follow the suggested commands to resolve them.

You can add the changes incrementally using `git add --patch` .
This is helpful to see each upstream change.
You may notice changes that affect how items in `content` are processed.
If so, you should edit and stage `content` files as needed.
When there are no longer any unstaged changes, then do `git commit` .

If updating `main` via a pull request, proceed to push the commit to GitHub and open a pull request.

Once the pull request is ready to merge, use GitHub's "Create a merge commit" option rather than "Squash and merge" or "Rebase and merge" to preserve the auto-docker commit hashes.
