#!/bin/bash

# Copyright (c) 2020, NVIDIA CORPORATION. All rights reserved.
# Full license terms provided in LICENSE.md file.

CONTAINER_NAME=$1
if [[ -z "${CONTAINER_NAME}" ]]; then
    CONTAINER_NAME=decent-multiarm
fi

# This specifies a mapping between a host directory and a directory in the
# docker container. This mapping should be changed if you wish to have access to
# a different directory
HOST_DIR=$2
if [[ -z "${HOST_DIR}" ]]; then
    HOST_DIR=`realpath ${PWD}/..`
fi

CONTAINER_DIR=$3
if [[ -z "${CONTAINER_DIR}" ]]; then
    CONTAINER_DIR=/root/catkin_ws/src/decentralized-multiarm
fi

IMAGE_NAME=$4
if [[ -z "${IMAGE_NAME}" ]]; then
    IMAGE_NAME=decent-multiarm:test-v16
fi

echo "Container name     : ${CONTAINER_NAME}"
echo "Host directory     : ${HOST_DIR}"
echo "Container directory: ${CONTAINER_DIR}"
DCMA_ID=`docker ps -aqf "name=^/${CONTAINER_NAME}$"`
if [ -z "${DCMA_ID}" ]; then
    echo "Creating new DOPE docker container."
    xhost +local:root
    docker run --gpus all  -it --privileged --network=host -v ${HOST_DIR}:${CONTAINER_DIR}:rw -v /tmp/.X11-unix:/tmp/.X11-unix:rw --env="DISPLAY" --name=${CONTAINER_NAME} ${IMAGE_NAME} bash
else
    echo "Found DOPE docker container: ${DCMA_ID}."
    # Check if the container is already running and start if necessary.
    if [ -z `docker ps -qf "name=^/${CONTAINER_NAME}$"` ]; then
        xhost +local:${DCMA_ID}
        echo "Starting and attaching to ${CONTAINER_NAME} container..."
        docker start ${DCMA_ID}
        docker attach ${DCMA_ID}
    else
        echo "Found running ${CONTAINER_NAME} container, attaching bash..."
        docker exec -it ${DCMA_ID} bash
    fi
fi