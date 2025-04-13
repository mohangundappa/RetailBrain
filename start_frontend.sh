#!/bin/bash
cd frontend && DANGEROUSLY_DISABLE_HOST_CHECK=true WDS_SOCKET_PORT=0 PORT=3001 npm start