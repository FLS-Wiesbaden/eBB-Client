import QtQuick 2.4
import QtGraphicalEffects 1.0
import QtQuick.Controls 1.3
import QtQuick.Window 2.2

Item {
	id: contentContainer
	width: parent.width
	height: parent.height

	Rectangle {
		id: body
		height: parent.height
		width: parent.width
		color: '#008014'
		anchors.centerIn: parent

		Image {
			id: fireFlameLeft
			anchors.left: parent.left
			anchors.leftMargin: 0
			anchors.verticalCenter: parent.verticalCenter
			rotation: 0
			source: "../../res/img/fire_image_right.png"
		}

		Image {
			id: fireArrowLeft
			anchors.left: parent.left
			anchors.leftMargin: 0
			anchors.verticalCenter: parent.verticalCenter
			rotation: 0
			fillMode: Image.PreserveAspectFit
			source: "../../res/img/fire_arrow.png"
			visible: false

			Behavior on rotation {
				RotationAnimation {
					duration: 300
					direction: RotationAnimation.Shortest
				}
			}
		}

		Image {
			id: fireMan
			anchors.horizontalCenter: parent.horizontalCenter
			anchors.verticalCenter: parent.verticalCenter
			rotation: 0
			source: "../../res/img/fire_symbol_right.png"
		}

		Image {
			id: fireArrowRight
			anchors.verticalCenter: parent.verticalCenter
			anchors.right: parent.right
			anchors.rightMargin: 0
			rotation: 0
			fillMode: Image.PreserveAspectFit
			source: "../../res/img/fire_arrow.png"

			Behavior on rotation {
				RotationAnimation {
					duration: 300
					direction: RotationAnimation.Shortest
				}
			}
		}

		Image {
			id: fireFlameRight
			anchors.verticalCenter: parent.verticalCenter
			anchors.right: parent.right
			anchors.rightMargin: 0
			rotation: 0
			source: "../../res/img/fire_image_left.png"
			visible: false
		}
	}

	function updateArrow(degrees) {
		if (degrees >= 120 && degrees <= 240) {
			// Show the arrow left.
			fireArrowLeft.visible = true
			fireArrowRight.visible = false
			fireArrowLeft.rotation = degrees
			fireArrowRight.rotation = degrees
			fireMan.source = '../../res/img/fire_symbol_left.png'
			fireFlameRight.visible = true
			fireFlameLeft.visible = false
		} else {
			// Show the arrow right.
			fireArrowRight.visible = true
			fireArrowLeft.visible = false
			fireArrowRight.rotation = degrees
			fireArrowLeft.rotation = degrees
			fireMan.source = '../../res/img/fire_symbol_right.png'
			fireFlameLeft.visible = true
			fireFlameRight.visible = false
		}
	}
}
