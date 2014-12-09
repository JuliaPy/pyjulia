# Yes python packaging sucks. 
# I hope that a makefile
# will help everyone to update the pakage.
# don't foret to bump the version number in setup.py

.PHONY: dist

clean:
	rm -rf build 
	rm -rf dist

dist: clean
	#  source distribution
	python3 setup.py sdist
	# 'compiled' distribution 
	# you mignt need to `pip3 install wheel`
	python3 setup.py bdist_wheel

upload: dist
	# upload to Python package index`
	twine upload dist/*

