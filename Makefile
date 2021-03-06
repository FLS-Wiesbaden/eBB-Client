cacheDirs  := cache __pycache__
buildDir   = build
debugFlg   = 
PACKAGE = VPlanClient
#Directory with ui and resource files
UI_FILES = main.qml pages/PresenterPage.qml pages/ContentPage.qml pages/FirealarmPage.qml pages/VplanPage.qml
RESOURCES = logos.qrc
PYTHONS = $(wildcard $(PACKAGE)/*.py)
RESOURCE_DIR = $(PACKAGE)/res
UI_DIR = $(PACKAGE)/ui
GRAPHICS = $(wildcard $(PACKAGE)/res/img/*.png)

COMPILED_UI = $(UI_FILES:%.qml=$(buildDir)/$(UI_DIR)/%.qml)
COMPILED_RESOURCES = $(RESOURCES:%.qrc=$(buildDir)/$(PACKAGE)/%_rc.py)
COMPILED_PYTHONS = $(PYTHONS:%.py=$(buildDir)/%.py)
COMPILED_GRAPHICS = $(GRAPHICS:%.png=$(buildDir)/%.png)

PYUIC = pyuic5
PYRCC = pyrcc5
PYTHON = python3
PYPARM = 

all: createDir debug

run: all
	$(PYTHON) $(PYPARM) $(buildDir)/$(PACKAGE)/VPlanClient.py

release: PYPARM := -OO
release: pythons resources ui images

debug: debugFlg := -x
debug: PYPARM := -v
debug: pythons resources ui images

createDir:
	@if [ ! -d "$(buildDir)/$(PACKAGE)" ]; then mkdir -p $(buildDir)/$(PACKAGE); fi
	@if [ ! -d "$(buildDir)/$(UI_DIR)" ]; then mkdir -p $(buildDir)/$(UI_DIR); fi
	@if [ ! -d "$(buildDir)/$(UI_DIR)/pages" ]; then mkdir -p $(buildDir)/$(UI_DIR)/pages; fi
	@if [ ! -d "$(buildDir)/$(PACKAGE)/res/img" ]; then mkdir -p $(buildDir)/$(PACKAGE)/res/img; fi

pythons: $(COMPILED_PYTHONS)
$(buildDir)/%.py: %.py
	cp $< $@
	chmod +x $@

ui: $(COMPILED_UI)
$(buildDir)/$(UI_DIR)/%.qml: $(UI_DIR)/%.qml
	cp $< $@
 
resources: $(COMPILED_RESOURCES)  
$(buildDir)/$(PACKAGE)/%_rc.py: $(RESOURCE_DIR)/%.qrc
	$(PYRCC) $< -o $@

images: $(COMPILED_GRAPHICS)
$(buildDir)/%.png: %.png
	cp $< $@

clean:
	$(RM) -rvf $(COMPILED_UI)
	$(RM) -rvf $(COMPILED_RESOURCES)
	$(RM) -rvf $(COMPILED_PYTHONS)
	$(RM) -rvf ${cacheDirs}
