#!/bin/bash
# install julia vX.Y.Z:  ./install-julia.sh X.Y.Z
# install julia nightly: ./install-julia.sh nightly

# stop on error
set -e
VERSION="$1"

case "$VERSION" in
  nightly)
    BASEURL="https://julialangnightlies-s3.julialang.org/bin"
    JULIANAME="julia-latest"
    ;;
  [0-9]*.[0-9]*.[0-9]*)
    BASEURL="https://julialang-s3.julialang.org/bin"
    SHORTVERSION="$(echo "$VERSION" | grep -Eo '^[0-9]+\.[0-9]+')"
    JULIANAME="$SHORTVERSION/julia-$VERSION"
    ;;
  [0-9]*.[0-9])
    BASEURL="https://julialang-s3.julialang.org/bin"
    SHORTVERSION="$(echo "$VERSION" | grep -Eo '^[0-9]+\.[0-9]+')"
    JULIANAME="$SHORTVERSION/julia-$VERSION-latest"
    ;;
  *)
    echo "Unrecognized VERSION=$VERSION, exiting"
    exit 1
    ;;
esac

case $(uname) in
  Linux)
    case $(uname -m) in
      x86_64)
        ARCH="x64"
        case "$JULIANAME" in
          julia-latest)
            SUFFIX="linux64"
            ;;
          *)
            SUFFIX="linux-x86_64"
            ;;
        esac
        ;;
      i386 | i486 | i586 | i686)
        ARCH="x86"
        case "$JULIANAME" in
          julia-latest)
            SUFFIX="linux32"
            ;;
          *)
            SUFFIX="linux-i686"
            ;;
        esac
        ;;
      *)
        echo "Do not have Julia binaries for this architecture, exiting"
        exit 1
        ;;
    esac
    echo "$BASEURL/linux/$ARCH/$JULIANAME-$SUFFIX.tar.gz"
    curl -L "$BASEURL/linux/$ARCH/$JULIANAME-$SUFFIX.tar.gz" | tar -xz
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
    curl -Lo julia.dmg "$BASEURL/mac/x64/$JULIANAME-mac64.dmg"
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