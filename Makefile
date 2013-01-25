cacheDirs  := cache __pycache__
buildDir   = build
debugFlg   = 
PACKAGE = VPlanClient
#Directory with ui and resource files
UI_FILES = about.ui browser.ui url.ui
RESOURCES = logos.qrc
PYTHONS = $(wildcard $(PACKAGE)/*.py)
RESOURCE_DIR = $(PACKAGE)/res
UI_DIR = $(PACKAGE)/ui

COMPILED_UI = $(UI_FILES:%.ui=$(buildDir)/$(PACKAGE)/ui_%.py)
COMPILED_RESOURCES = $(RESOURCES:%.qrc=$(buildDir)/$(PACKAGE)/%_rc.py)
COMPILED_PYTHONS = $(PYTHONS:%.py=$(buildDir)/%.py)

PYUIC = pyuic4
PYRCC = pyrcc4

all: createDir debug

run: all
	python3 $(buildDir)/$(PACKAGE)/VPlanClient.py

release: pythons resources ui

debug: debugFlg := -x
debug: pythons resources ui

createDir:
	@if [ ! -d "$(buildDir)/$(PACKAGE)" ]; then mkdir -p $(buildDir)/$(PACKAGE); fi

pythons: $(COMPILED_PYTHONS)
$(buildDir)/%.py: %.py
	cp $< $@
	chmod +x $@

resources: $(COMPILED_RESOURCES)  
ui: $(COMPILED_UI)

$(buildDir)/$(PACKAGE)/ui_%.py: $(UI_DIR)/%.ui
	$(PYUIC) $(debugFlg) $< -o $@
 
$(buildDir)/$(PACKAGE)/%_rc.py: $(RESOURCE_DIR)/%.qrc
	$(PYRCC) -py3 $< -o $@

clean:
	$(RM) -rvf $(COMPILED_UI)
	$(RM) -rvf $(COMPILED_RESOURCES)
	$(RM) -rvf $(COMPILED_PYTHONS)
	$(RM) -rvf ${cacheDirs}
