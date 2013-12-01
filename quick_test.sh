#!/bin/sh
python2 -c "import julia;j=julia.Julia();assert(j.run('1+1') == 2)"
echo "Python2 ok..."
python3 -c "import julia;j=julia.Julia();assert(j.run('1+1') == 2)"
echo "Python3 ok..."

