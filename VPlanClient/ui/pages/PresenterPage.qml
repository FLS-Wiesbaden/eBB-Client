import QtQuick 2.0
import QtQml.Models 2.1

Rectangle {
	id: presenterPage
	objectName: "presenterPage"

	property int idx: 0
	property bool repeat: false
	property ListModel presenterPdfModel: null

	signal finished()

	width: parent.width
	height: parent.height

	function setBasicData(model, cycleTime) {
		presenterPdfModel = model
		visualModel.model = presenterPdfModel
		slideT.interval = cycleTime
		slideT.start()
	}

	VisualDataModel {
		id: visualModel
		model: presenterPdfModel

		delegate: Item {
			id: delegateItem

			width: parent.width
			height: parent.height

			Rectangle {
				id: image
				width: parent.width
				height: parent.height
				visible: idx == delegateItem.VisualDataModel.itemsIndex
				anchors.centerIn: parent

				Image {
					anchors.fill: parent
					anchors.leftMargin: 1
					anchors.topMargin: 1
					source: imagePath
					fillMode: Image.PreserveAspectFit
					cache: false
				}

				states: [
					State {
						when: presenterPage.idx === delegateItem.VisualDataModel.itemsIndex
						name: "inDisplay";
						ParentChange { target: image; parent: imageContainer; x: 0; y: 0; }
						PropertyChanges { target: image; z: 2 }
					},
					State {
						when: presenterPage.idx !== delegateItem.VisualDataModel.itemsIndex
						name: "inList";
						ParentChange { target: image; parent: delegateItem; x: 0; y: 0; }
						PropertyChanges { target: image; z: 1 }	
					}
				]

				transitions: [
					Transition {
						from: "inList"
						SequentialAnimation {
							ParentAnimation {
								target: image
								via: presenterPage
								NumberAnimation { 
									target: image
									properties: "opacity"
									from: 0.0
									to: 1.0
									duration: 1000 
								}
							}
						}
					},
					Transition {
						from: "inDisplay"
						SequentialAnimation {
							ParentAnimation {
								target: image
								NumberAnimation { 
									target: image
									properties: "opacity"
									from: 1.0
									to: 0.0
									duration: 1000 
								}
							}
						}
					}
				]
			}
		}
	}

	Item {
		id: imageContainer
		anchors { fill: parent; }
	}

	ListView {
		anchors.fill: parent
		model: visualModel
	}

	Timer {
		id: slideT
		interval: 2000
		running: false
		repeat: true
		onTriggered: {
			presenterPage.idx = presenterPage.idx + 1
			if (presenterPage.idx >= visualModel.count) {
				if (!presenterPage.repeat) {
					slideT.stop()
					presenterPage.finished()
				}
				presenterPage.idx = 0
			}
		}
	}

	function setLoop(loop) {
		presenterPage.repeat = loop
	}
}