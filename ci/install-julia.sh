#!/bin/sh
# install julia release: ./install-julia.sh juliareleases
# install julia nightly: ./install-julia.sh julianightlies

VERSION="0.6.2"
SHORTVERSION="0.6"

# stop on error
set -e
# default to juliareleases
if [ $# -ge 1 ]; then
  JULIAVERSION=$1
elif [ -z "$JULIAVERSION" ]; then
  JULIAVERSION=juliareleases
fi

case "$JULIAVERSION" in
  julianightlies)
    BASEURL="https://julialangnightlies-s3.julialang.org/bin"
    JULIANAME="julia-latest"
    ;;
  juliareleases)
    BASEURL="https://julialang-s3.julialang.org/bin"
    JULIANAME="julia-$VERSION"
    ;;
  *)
    echo "Unrecognized JULIAVERSION=$JULIAVERSION, exiting"
    exit 1
    ;;
esac

case $(uname) in
  Linux)
    case $(uname -m) in
      x86_64)
        ARCH="x64"
        case "$JULIAVERSION" in
          julianightlies)
            SUFFIX="linux64"
            ;;
          juliareleases)
            SUFFIX="linux-x86_64"
            ;;
        esac
        ;;
      i386 | i486 | i586 | i686)
        ARCH="x86"
        case "$JULIAVERSION" in
          julianightlies)
            SUFFIX="linux32"
            ;;
          juliareleases)
            SUFFIX="linux-i686"
            ;;
        esac
        ;;
      *)
        echo "Do not have Julia binaries for this architecture, exiting"
        exit 1
        ;;
    esac
    echo "$BASEURL/linux/$ARCH/$SHORTVERSION/$JULIANAME-$SUFFIX.tar.gz"
    curl -L "$BASEURL/linux/$ARCH/$SHORTVERSION/$JULIANAME-$SUFFIX.tar.gz" | tar -xz
    sudo ln -s $PWD/julia-*/bin/julia /usr/local/bin/julia
    ;;
  Darwin)
    if [ -e /usr/local/bin/julia ]; then
      echo "/usr/local/bin/julia already exists, exiting"
      exit 1
    elif [ -e julia.dmg ]; then
      echo "julia.dmg already exists, exiting"
      exit 1
    elif [ -e ~/julia ]; then
      echo "~/julia already exists, exiting"
      exit 1
    fi
    curl -Lo julia.dmg "$BASEURL/mac/x64/$SHORTVERSION/$JULIANAME-mac64.dmg"
    hdiutil mount -mountpoint /Volumes/Julia julia.dmg
    cp -Ra /Volumes/Julia/*.app/Contents/Resources/julia ~
    ln -s ~/julia/bin/julia /usr/local/bin/julia
    # TODO: clean up after self?
    ;;
  *)
    echo "Do not have Julia binaries for this platform, exiting"
    exit 1
    ;;
esac