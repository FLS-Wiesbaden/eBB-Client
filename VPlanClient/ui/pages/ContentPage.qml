import QtQuick 2.4
import QtGraphicalEffects 1.0
import QtQuick.Controls 1.3
import QtQuick.Window 2.2

Item {
	id: contentContainer
	width: parent.width
	height: parent.height

	Item {
		id: ebbHeadContainer
		width: parent.width
		height: 87
		z: 2

		RectangularGlow {
			height: parent.height
			z: 5
			glowRadius: 10
			spread: 0.2
			color: "#000000"
			anchors.topMargin: 20
			anchors.fill: ebbHeadLine
		}

		Rectangle {
			id: ebbHeadLine
			width: parent.width
			height: parent.height
			z: 10

			Image {
				id: ebbHeadImgLeft
				height: ebbHeadImgMiddle.height
				width: ebbHeadImgMiddle.x
				source: "../../res/img/header_wdh.png"
				anchors.right: ebbHeadImgMiddle.left

			}

			Image {
				id: ebbHeadImgMiddle
				source: "../../res/img/header_center.png"
				anchors.centerIn: parent

				Text {
					id: lblLeftColumn
					color: "#ffffff"
					z: 5
					anchors.verticalCenter: parent.verticalCenter
					anchors.left: parent.left
					text: qsTr("")
					opacity: 0.85
					textFormat: Text.PlainText
					verticalAlignment: Text.AlignVCenter
					styleColor: "#ffffff"
					font.bold: true
					font.pixelSize: 32
				}

				Text {
					id: lblRightColumn
					color: "#ffffff"
					z: 5
					anchors.verticalCenter: parent.verticalCenter
					anchors.right: parent.right
					text: qsTr("")
					anchors.rightMargin: 0
					anchors.verticalCenterOffset: 0
					opacity: 0.85
					textFormat: Text.PlainText
					verticalAlignment: Text.AlignVCenter
					styleColor: "#ffffff"
					font.bold: true
					font.pixelSize: 32
				}
			}

			Image {
				id: ebbHeadImgRight
				height: ebbHeadImgMiddle.height
				width: parent.width - ebbHeadImgMiddle.width - ebbHeadImgLeft.width
				source: "../../res/img/header_wdh.png"
				anchors.left: ebbHeadImgMiddle.right
			}
		}
	}

	Rectangle {
		id: body
		height: parent.height - ebbHeadContainer.height
		anchors.horizontalCenterOffset: 0
		anchors.rightMargin: 0
		anchors.bottomMargin: 0
		anchors.leftMargin: 0
		anchors.topMargin: 0
		border.width: 0
		anchors.horizontalCenter: parent.horizontalCenter
		anchors.fill: parent

		Item {
			id: contentItem
			anchors.horizontalCenter: parent.horizontalCenter
			anchors.top: parent.top
			anchors.topMargin: 80 + ebbHeadContainer.height
			width: contentContent.width
			height: contentContent.height

			Rectangle {
				anchors.fill: parent
			}

			Rectangle {
				id: contentContent
				height: (contentText.height < (0.32 * body.height) ? 0.32 * body.height : contentText.height + 80)
				width: 0.8 * body.width
				color: "#f3f3f3"
				radius: 50
				border.color: "#bbbbbb"
				border.width: 1
				anchors.centerIn: parent

			}

			InnerShadow {
				anchors.fill: contentContent
				radius: 50
				opacity: 0.5
				spread: 0.2
				samples: 24
				horizontalOffset: -3
				verticalOffset: 3
				color: "#7d7d7d"
				source: contentContent
			}

			InnerShadow {
				anchors.fill: contentContent
				radius: 50
				opacity: 0.5
				z: 0
				rotation: 0
				scale: 1
				spread: 0.2
				samples: 24
				horizontalOffset: 3
				verticalOffset: -3
				color: "#7d7d7d"
				source: contentContent
			}

			Rectangle {
				id: rectangle1
				height: (contentText.height < (0.32 * body.height) ? 0.32 * body.height : contentText.height)
				color: "#00000000"
				anchors.verticalCenterOffset: 0
				anchors.horizontalCenterOffset: 0
				border.width: 0
				width: contentContent.width
				anchors.centerIn: parent

				Text {
					id: contentText
					width: parent.width - 40
					color: "#000000"
					text: ""
					anchors.verticalCenterOffset: 0
					anchors.horizontalCenterOffset: 40
					wrapMode: Text.WordWrap
					font.pixelSize: 20
					anchors.centerIn: parent
				}
			}
		}

		Image {
			id: contentArrow
			anchors.horizontalCenter: parent.horizontalCenter
			anchors.top: contentItem.bottom
			anchors.topMargin: 150
			rotation: 0
			source: "../../res/img/content_arrow.png"

			Behavior on rotation {
				RotationAnimation {
					duration: 500
					direction: RotationAnimation.Shortest
				}
			}
		}

	}

	function updateArrow(degrees) {
		contentArrow.rotation = degrees
	}

	function updateContent(content) {
		contentText.text = content
	}
}
