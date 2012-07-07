cacheDirs  := cache __pycache__
buildDir   := build
debugFlg   := 
uiSources  := $(wildcard ui/*.ui)
uiInputs   := $(foreach i,$(uiSources),$(i))
qrcSources := $(wildcard res/*.qrc)
qrcInputs  := $(foreach i,$(qrcSources),$(i))
staticPys  := $(wildcard *.py *.ini)

all: createDir debug

run: all
	python3 $(buildDir)/vplanClient.py

release: cpPython makeResources makeUis

debug:  debugFlg := -x
debug:  cpPython makeResources makeUis

createDir:
	@if [ ! -d "$(buildDir)" ]; then mkdir -p $(buildDir); fi

cpPython:
	cp $(staticPys) $(buildDir)/
	chmod +x $(buildDir)/vplanClient.py

makeResources: $(qrcInputs)
	@export data="$(qrcInputs)"; \
	    for f in $$data; do \
	    targetFile=`basename $$f`; \
	    targetFile=`echo "$$targetFile" | sed -e 's/\.qrc/_rc.py/g'`; \
	    targetFile="$(buildDir)/$$targetFile"; \
	    echo "Making $$f to $$targetFile"; \
	    pyrcc4 -py3 -o $$targetFile $$f; \
	    done 

makeUis: $(uiInputs)
	@export data="$(uiInputs)"; \
	    for f in $$data; do \
	    targetFile=`basename $$f`; \
	    targetFile=`echo "Ui$${targetFile^}" | sed -e 's/\.ui/.py/g'`; \
	    targetFile="$(buildDir)/$$targetFile"; \
	    echo "Making $$f to $$targetFile"; \
	    pyuic4 $(debugFlg) -o $$targetFile $$f; \
	    done

clean:
	rm -rvf ${cacheDirs}
	rm -rvf ${buildDir}

