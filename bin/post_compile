#!/usr/bin/env bash
set -eo pipefail

# The post_compile hook is run by heroku-buildpack-python

echo "-----> I'm post-compile hook"

# Work around Heroku bug whereby pylibmc isn't available during
# compile phase. See: https://github.com/heroku/heroku-buildpack-python/issues/57
export MEMCACHE_SERVERS='' MEMCACHIER_SERVERS=''

if [ -f bin/install_nodejs ]; then
    echo "-----> Running install_nodejs"
    chmod +x bin/install_nodejs
    bin/install_nodejs

    if [ -f bin/install_less ]; then
        echo "-----> Running install_lessc"
        chmod +x bin/install_less
        bin/install_less
    fi
fi

if [ -f bin/run_collectstatic ]; then
    echo "-----> Running run_collectstatic"
    chmod +x bin/run_collectstatic
    bin/run_collectstatic
fi

if [ -f bin/run_compress ]; then
    echo "-----> Running run_compress"
    chmod +x bin/run_compress
    bin/run_compress
fi

echo "-----> Post-compile done"
