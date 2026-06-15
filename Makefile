.PHONY: all clean build check upload

all: upload

clean:
	rm -rf dist

# build both the source distribution (sdist) and the wheel
build: clean
	uv build

# validate package metadata renders correctly on PyPI before uploading
check: build
	uvx twine check dist/*

# upload sdist + wheel to PyPI
upload: check
	uvx twine upload dist/*
